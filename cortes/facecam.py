"""Localiza a webcam do streamer no quadro, via detecção de rosto em vários frames."""
from collections import namedtuple

import cv2
import numpy as np

FOLGA = 0.3  # quanto o rosto pode sair da posição de sempre, em larguras de rosto

# caixa: (x, y, w, h) da cam, ou None. mudancas: trechos em que o rosto aparece em outro lugar.
# rosto: (cx, cy, largura) do rosto na posição de sempre. firme: o que aparece na caixa é a mesma
# cena do começo ao fim do clipe, como numa webcam parada.
Analise = namedtuple("Analise", "caixa mudancas rosto firme")
SEM_CAM = Analise(None, [], None, False)


def _cascata():
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def _rostos(caminho, amostras):
    """Rostos em `amostras` quadros espalhados pelo vídeo.

    Retorna ([(quadro, cx, cy, w, h)], {quadro: segundo}, miniaturas, largura, altura); a lista
    de tempos só tem os quadros que deu para ler, e as miniaturas são esses quadros em cinza, a 1/4.
    """
    cap = cv2.VideoCapture(caminho)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    L, A = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    if total <= 0 or L == 0:
        return [], {}, [], L, A
    cascata = _cascata()
    achados, tempos, miniaturas = [], {}, []
    for n, pos in enumerate(np.linspace(0, total - 1, amostras).astype(int)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
        ok, frame = cap.read()
        if not ok:
            continue
        tempos[n] = pos / fps
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        miniaturas.append(cv2.resize(cinza, (L // 4, A // 4), interpolation=cv2.INTER_AREA))
        for (x, y, w, h) in cascata.detectMultiScale(cinza, 1.1, 6, minSize=(A // 18, A // 18)):
            achados.append((n, x + w / 2, y + h / 2, w, h))
    cap.release()
    return achados, tempos, miniaturas, L, A


def _firmeza(miniaturas, caixa):
    """(persistência, congelamento) do que aparece na caixa ao longo dos quadros amostrados.

    persistência: fração dos quadros em que a caixa mostra a mesma cena da maioria. Webcam parada
    fica acima de 0,8 (o fundo é sempre o mesmo); recorte do jogo e webcam arrastada, abaixo de 0,5.
    congelamento: fração dos pares de quadros seguidos em que nada se mexe na caixa. Gente ao vivo
    fica perto de 0; foto ou tela parada do jogo, perto de 1.
    """
    x, y, w, h = (v // 4 for v in caixa)
    recortes = [m[y:y + h, x:x + w] for m in miniaturas]
    if not recortes or min(recortes[0].shape) < 2:
        return 0.0, 0.0  # caixa fora do quadro ou pequena demais para medir
    recortes = [cv2.resize(r, (64, 36)).astype(np.float32) for r in recortes]
    molde = np.median(recortes, axis=0)
    molde = molde - molde.mean()

    def parecido(r):
        r = r - r.mean()
        norma = np.sqrt((r * r).sum() * (molde * molde).sum())
        return norma > 1e-6 and (r * molde).sum() / norma >= 0.6

    parados = [np.abs(a - b).mean() < 1 for a, b in zip(recortes, recortes[1:])]
    return float(np.mean([parecido(r) for r in recortes])), float(np.mean(parados)) if parados else 0.0


def _parecido(largura, fw):
    """O rosto achado tem o tamanho do rosto do streamer (largura `fw`)?"""
    return 0.7 * fw <= largura <= 1.4 * fw


def _no_lugar(x, y, cx, cy, fw):
    return abs(x - cx) <= FOLGA * fw and abs(y - cy) <= FOLGA * fw


def _mudancas(achados, tempos, cx, cy, fw, minimo=3):
    """Trechos em que o rosto do streamer aparece parado em outro lugar que não o de sempre.

    Procura, entre duas aparições do rosto na posição de sempre (cx, cy), um rosto do mesmo
    tamanho repetido num outro ponto em pelo menos `minimo` quadros: sinal de que a webcam foi
    arrastada (ou de que o streamer mudou de posição por um tempo).
    """
    parecidos = [a for a in achados if _parecido(a[3], fw)]
    em_casa = {a[0] for a in parecidos if _no_lugar(a[1], a[2], cx, cy, fw)}
    saida, grupos = [], []  # grupos: rostos de fora que caem no mesmo ponto, desde a última vez em casa
    for n in sorted(tempos) + [None]:
        if n is not None and n not in em_casa:
            for a in (a for a in parecidos if a[0] == n):
                for g in grupos:
                    if _no_lugar(a[1], a[2], *np.median(np.array(g)[:, 1:3], axis=0), fw):
                        g.append(a)
                        break
                else:
                    grupos.append([a])
            continue
        for g in grupos:  # o rosto voltou para casa (ou o vídeo acabou): fecha o que juntou
            quadros = sorted({a[0] for a in g})
            if len(quadros) >= minimo:
                gx, gy = np.median(np.array(g)[:, 1:3], axis=0)
                saida.append({"inicio": round(float(tempos[quadros[0]]), 1),
                              "fim": round(float(tempos[quadros[-1]]), 1),
                              "dx": int(round(gx - cx)), "dy": int(round(gy - cy))})
        grupos = []
    return sorted(saida, key=lambda m: m["inicio"])


def _principal(achados, L, A):
    """Os rostos da célula (grade 8x8) em que há rosto em mais quadros distintos."""
    grupos = {}
    for a in achados:
        grupos.setdefault((int(a[1] * 8 / L), int(a[2] * 8 / A)), []).append(a)
    return max(grupos.values(), key=lambda g: len({a[0] for a in g}))


def analisar(caminho, cam=None, amostras=40, presenca_min=0.3):
    """Acha a facecam e diz o quanto dá para confiar nela. Retorna uma `Analise`.

    caixa: (x, y, w, h), ou None se não achar uma posição estável. A webcam costuma ficar parada
    no layout, então o rosto aparece quase sempre na mesma região; rostos de personagens do jogo
    aparecem em posições espalhadas e são descartados, assim como foto ou tela parada do jogo.
    Com `cam` informada (caixa medida à mão), ela é devolvida como está e a análise olha os rostos
    que cabem dentro dela.
    mudancas: [{"inicio", "fim", "dx", "dy", "cam"}] — trechos (em segundos) em que o rosto
    aparece deslocado dx, dy pixels da posição de sempre; "cam" é a caixa que serviria ali. A
    caixa é uma só para o clipe inteiro: nesses trechos o recorte da cam pode cortar o rosto ou
    mostrar jogo.
    """
    achados, tempos, miniaturas, L, A = _rostos(caminho, amostras)
    if cam:  # vale o rosto que cabe inteiro na caixa: é para ele que ela foi medida
        x, y, w, h = cam
        firme = _firmeza(miniaturas, cam)[0] >= 0.7
        candidatos = [a for a in achados if x <= a[1] - a[3] / 2 and a[1] + a[3] / 2 <= x + w
                      and y <= a[2] - a[4] / 2 and a[2] + a[4] / 2 <= y + h]
        if len({a[0] for a in candidatos}) < 3:
            return Analise(tuple(cam), [], None, firme)
        melhor = _principal(candidatos, L, A)
    else:
        candidatos = achados
        if not achados or not tempos:
            return SEM_CAM
        melhor = _principal(achados, L, A)
        if len({a[0] for a in melhor}) / len(tempos) < presenca_min:
            return SEM_CAM

    _, cx, cy, fw, _ = np.median(np.array(melhor), axis=0)
    if not cam and fw * 3.2 > L * 0.5:
        return SEM_CAM  # rosto grande demais para ser webcam (close de cutscene)
    # a célula pode ter partido o rosto em dois (ele bem na divisa, ou a webcam solta um pouco
    # ao lado): refaz a mediana com os rostos desse tamanho em volta, e a maioria decide
    for raio in (1.0, 0.5, 0.5):  # fecha o cerco: com duas posições próximas, fica a mais frequente
        vizinhos = [a for a in candidatos if _parecido(a[3], fw)
                    and abs(a[1] - cx) <= raio * fw and abs(a[2] - cy) <= raio * fw]
        _, cx, cy, fw, _ = np.median(np.array(vizinhos or melhor), axis=0)
    if cam:
        caixa = tuple(cam)
    else:
        # caixa 16:9 em volta do rosto (o rosto ocupa ~1/3 da largura de uma webcam típica)
        w = min(L, fw * 3.2)
        h = min(A, w * 9 / 16)
        caixa = tuple(int(v) // 2 * 2 for v in (np.clip(cx - w / 2, 0, L - w), np.clip(cy - h * 0.42, 0, A - h), w, h))
        persistencia, congelamento = _firmeza(miniaturas, caixa)
        if congelamento >= 0.5:
            return SEM_CAM  # imagem parada: é foto ou tela do jogo com um rosto, não webcam
        firme = persistencia >= 0.7
    mudancas = _mudancas(achados, tempos, cx, cy, fw)
    for m in mudancas:  # a mesma caixa, levada para onde o rosto está nesse trecho
        x = int(np.clip(caixa[0] + m["dx"], 0, L - caixa[2])) // 2 * 2
        y = int(np.clip(caixa[1] + m["dy"], 0, A - caixa[3])) // 2 * 2
        m["cam"] = f"{x}:{y}:{caixa[2]}:{caixa[3]}"
    return Analise(caixa, mudancas, (float(cx), float(cy), float(fw)), firme)


def detectar(caminho, amostras=40, presenca_min=0.3):
    """Só a caixa (x, y, w, h) da facecam, ou None. Ver `analisar`."""
    return analisar(caminho, None, amostras, presenca_min).caixa


def ausencias(caminho, rosto, trechos, passo=0.25, ponte=1.0):
    """Pedaços de `trechos` [(inicio, fim)] em que o rosto do streamer não foi confirmado no lugar.

    Olha um quadro a cada `passo` segundos, só na região do rosto (`rosto` vem de `analisar`).
    Entre duas confirmações seguidas a até `ponte` segundos uma da outra a webcam é dada como
    parada; o resto do trecho é devolvido como ausência. É nesses pedaços que o recorte da cam
    pode estar mostrando jogo: webcam arrastada, escondida, ou streamer fora do quadro.
    Sem `rosto` não há o que confirmar: devolve os trechos inteiros.
    """
    trechos = [tuple(t) for t in trechos]
    if not rosto or not trechos:
        return trechos
    cx, cy, fw = rosto
    x0, y0, lado = int(max(0, cx - 2 * fw)), int(max(0, cy - 2 * fw)), int(0.6 * fw)
    cascata = _cascata()
    cap = cv2.VideoCapture(caminho)
    vistos, proximo = [], 0.0  # instantes em que o rosto estava no lugar
    while cap.grab():  # em sequência, sem pular: o tempo de cada quadro sai exato em qualquer formato
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if t > max(b for _, b in trechos) + ponte:
            break
        if t < proximo or not any(a - ponte <= t <= b + ponte for a, b in trechos):
            continue
        proximo = t + passo
        ok, frame = cap.retrieve()
        if not ok:
            break
        cinza = cv2.cvtColor(frame[y0:int(cy + 2 * fw), x0:int(cx + 2 * fw)], cv2.COLOR_BGR2GRAY)
        if any(_parecido(w, fw) and _no_lugar(x0 + x + w / 2, y0 + y + h / 2, cx, cy, fw)
               for (x, y, w, h) in cascata.detectMultiScale(cinza, 1.1, 6, minSize=(lado, lado))):
            vistos.append(t)
    cap.release()
    return _faltas(vistos, trechos, ponte)


def _faltas(vistos, trechos, ponte):
    """O que sobra de cada trecho tirando os pedaços entre duas confirmações seguidas do rosto."""
    saida = []
    for a, b in trechos:
        visiveis = []  # pedaços do trecho com o rosto confirmado do começo ao fim
        for u, v in zip(vistos, vistos[1:]):
            if v - u > ponte:
                continue
            u, v = max(u, a), min(v, b)
            if v <= u:
                continue
            if visiveis and u <= visiveis[-1][1]:
                visiveis[-1][1] = v
            else:
                visiveis.append([u, v])
        t = a
        for u, v in visiveis:
            if v - u < 1:  # aparição curta demais: a cam só piscaria na tela
                continue
            if u - t > 0.05:
                saida.append((round(t, 2), round(u, 2)))
            t = v
        if b - t > 0.05:
            saida.append((round(t, 2), round(b, 2)))
    return saida


def descrever(mudancas):
    """Frase com os trechos em que o rosto sai do lugar, para avisar quem está montando o corte."""
    def lado(m):
        partes = []
        if abs(m["dx"]) >= 10:
            partes.append(f"{abs(m['dx'])} px à {'direita' if m['dx'] > 0 else 'esquerda'}")
        if abs(m["dy"]) >= 10:
            partes.append(f"{abs(m['dy'])} px {'abaixo' if m['dy'] > 0 else 'acima'}")
        return " e ".join(partes) or "fora do lugar"

    return "; ".join(f"de {m['inicio']:.0f} s a {m['fim']:.0f} s, {lado(m)} (--cam {m['cam']})" for m in mudancas)


def interpretar(texto):
    """'x:y:w:h' -> tupla, para informar a posição da cam manualmente."""
    partes = [int(p) for p in texto.replace(",", ":").split(":")]
    if len(partes) != 4:
        raise ValueError("use o formato x:y:w:h")
    return tuple(partes)
