"""Localiza a webcam do streamer no quadro, via detecção de rosto em vários frames."""
import cv2
import numpy as np


def detectar(caminho, amostras=40, presenca_min=0.3):
    """Retorna (x, y, w, h) da facecam ou None se não achar uma posição estável.

    A webcam fica parada no layout, então o rosto aparece sempre na mesma região;
    rostos de personagens do jogo aparecem em posições espalhadas e são descartados.
    """
    cap = cv2.VideoCapture(caminho)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    L, A = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if total <= 0 or L == 0:
        return None
    cascata = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    achados = []  # (frame, cx, cy, w, h)
    pequenos = []  # os mesmos quadros, reduzidos, para achar a moldura da webcam depois
    escala = 960 / L
    lidos = 0
    for n, pos in enumerate(np.linspace(0, total - 1, amostras).astype(int)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
        ok, frame = cap.read()
        if not ok:
            continue
        lidos += 1
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        pequenos.append(cv2.resize(cinza, (960, int(A * escala))).astype(np.float32))
        for (x, y, w, h) in cascata.detectMultiScale(cinza, 1.1, 6, minSize=(A // 18, A // 18)):
            achados.append((n, x + w / 2, y + h / 2, w, h))
    cap.release()
    if not achados or not lidos:
        return None

    # agrupa por célula de uma grade 8x8 e pega a célula com rosto em mais frames distintos
    grupos = {}
    for a in achados:
        chave = (int(a[1] * 8 / L), int(a[2] * 8 / A))
        grupos.setdefault(chave, []).append(a)
    melhor = max(grupos.values(), key=lambda g: len({a[0] for a in g}))
    if len({a[0] for a in melhor}) / lidos < presenca_min:
        return None

    _, cx, cy, fw, fh = np.median(np.array(melhor), axis=0)
    if fw * 3.2 > L * 0.5:
        return None  # rosto grande demais para ser webcam (close de cutscene)
    exata = _moldura(pequenos, escala, cx, cy, fw, fh)
    if exata:
        return _enquadrar(exata, cx, cy, fh)
    # caixa 16:9 em volta do rosto (rosto ocupa ~1/3 da largura de uma webcam típica)
    w = min(L, fw * 3.2)
    h = min(A, w * 9 / 16)
    x = float(np.clip(cx - w / 2, 0, L - w))
    y = float(np.clip(cy - h * 0.42, 0, A - h))
    return tuple(int(v) // 2 * 2 for v in (x, y, w, h))


def _enquadrar(caixa, cx, cy, fh=0):
    """Recorta, dentro da webcam, a janela 16:9 que o painel de cima usa, guiada pelo rosto.

    Webcam mais alta que 16:9 perde o que sobra em cima ou embaixo (é onde ficam as barras do
    layout), mantendo o rosto a 42% da altura; mais larga, perde as laterais.
    """
    x, y, w, h = caixa
    if h > w * 9 / 16:
        alt = w * 9 / 16
        # o rosto fica a 42% da altura, mas nunca tão alto que corte o topo da cabeça
        y += float(np.clip(cy - y - max(0.42 * alt, 1.05 * fh), 0, h - alt))
        h = alt
    else:
        larg = h * 16 / 9
        x += float(np.clip(cx - x - larg / 2, 0, w - larg))
        w = larg
    return tuple(int(v) // 2 * 2 for v in (x, y, w, h))


def _primeiro_acima(perfil, inicio, passo, limite, teto, seguidos=4):
    """Anda de `inicio` na direção `passo` e devolve o primeiro índice em que o perfil fica acima
    do `teto` por `seguidos` posições; None se chegar em `limite` sem achar."""
    conta, i = 0, inicio
    while 0 <= i < len(perfil) and i != limite:
        conta = conta + 1 if perfil[i] > teto else 0
        if conta >= seguidos:
            return i - passo * (seguidos - 1)
        i += passo
    return None


def _moldura(quadros, e, cx, cy, fw, fh):
    """Acha o retângulo exato da webcam em volta do rosto, ou None.

    O fundo da webcam (o quarto do streamer) fica parado, enquanto o jogo em volta muda o tempo
    todo. Então a borda da webcam é onde a variação dos pixels ao longo do clipe salta de baixa
    para alta. Embaixo da webcam costuma haver uma barra fixa do layout (último sub, combo), que
    também é parada: ali a borda é a linha horizontal que persiste em todos os quadros.
    """
    if len(quadros) < 8:
        return None
    pilha = np.stack(quadros)
    varia = cv2.blur(pilha.std(axis=0), (5, 5))                        # quanto cada pixel muda no tempo
    linha_h = np.mean([np.abs(cv2.Sobel(q, cv2.CV_32F, 0, 1, ksize=3)) for q in quadros], axis=0)  # bordas horizontais fixas
    a_, l_ = varia.shape
    cx, cy, fw, fh = cx * e, cy * e, fw * e, fh * e

    # esquerda e direita: perfil da variação nas linhas do rosto, andando para fora
    y0, y1 = int(max(0, cy - 0.5 * fh)), int(min(a_, cy + 0.5 * fh))
    perfil = np.median(varia[y0:y1], axis=0)
    perto = np.r_[perfil[int(max(0, cx - 1.2 * fw)):int(max(1, cx - 0.7 * fw))], perfil[int(min(l_ - 1, cx + 0.7 * fw)):int(min(l_, cx + 1.2 * fw))]]
    if not len(perto):
        return None
    teto = max(7.0, 2.5 * float(np.median(perto)) + 3.0)
    esq = _primeiro_acima(perfil, int(cx - 0.7 * fw), -1, int(max(0, cx - 4.5 * fw)), teto)
    dire = _primeiro_acima(perfil, int(cx + 0.7 * fw), +1, int(min(l_ - 1, cx + 4.5 * fw)), teto)
    esq = esq + 1 if esq is not None else (0 if cx - 4.5 * fw <= 0 else None)       # webcam colada na borda da tela
    dire = dire - 1 if dire is not None else (l_ - 1 if cx + 4.5 * fw >= l_ - 1 else None)
    if esq is None or dire is None:
        return None
    w = dire - esq
    if not 1.6 * fw <= w <= 6 * fw:
        return None
    if cx - esq < 0.7 * fw + 4 or dire - cx < 0.7 * fw + 4:
        return None  # a variação já começa alta ao lado do rosto (luz piscando no fundo): não dá para confiar

    # em cima: mesma ideia, olhando só o miolo da largura (30% mais parados de cada linha)
    x0, x1 = int(esq + 0.08 * w), int(dire - 0.08 * w)
    perfil_v = np.percentile(varia[:, x0:x1], 30, axis=1)
    topo = _primeiro_acima(perfil_v, int(cy - 0.6 * fh), -1, int(max(0, cy - 3 * fh)), teto)
    topo = topo + 1 if topo is not None else (0 if cy - 3 * fh <= 0 else None)
    if topo is None:
        return None
    # embaixo: a linha horizontal mais forte e mais longa entre as proporções 16:9 e 4:3
    faixa0, faixa1 = int(topo + 0.45 * w), int(min(a_ - 1, topo + 0.85 * w))
    if faixa1 - faixa0 < 4:
        return None
    forca = linha_h[faixa0:faixa1, x0:x1]
    nota = forca.mean(axis=1) * (forca > 12).mean(axis=1)
    # a primeira linha forte de cima para baixo: a de baixo costuma ser o fim da barra do layout
    base = faixa0 + int(np.argmax(nota >= 0.6 * nota.max()))
    if (forca[base - faixa0] > 12).mean() < 0.45:
        desce = _primeiro_acima(perfil_v, int(cy + 0.9 * fh), +1, faixa1, teto)
        base = desce - 1 if desce is not None and desce > faixa0 else int(topo + w * 9 / 16)
    h = base - topo
    if not 0.4 * w <= h <= 0.9 * w or not (esq < cx < dire and topo < cy < base):
        return None
    m = 3  # folga para dentro, para não pegar a linha da moldura
    caixa = ((esq + m) / e, (topo + m) / e, (w - 2 * m) / e, (h - 2 * m) / e)
    return tuple(int(v) // 2 * 2 for v in caixa)


def interpretar(texto):
    """'x:y:w:h' -> tupla, para informar a posição da cam manualmente."""
    partes = [int(p) for p in texto.replace(",", ":").split(":")]
    if len(partes) != 4:
        raise ValueError("use o formato x:y:w:h")
    return tuple(partes)
