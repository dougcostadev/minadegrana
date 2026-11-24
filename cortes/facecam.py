"""Localiza a webcam do streamer no quadro, via detecção de rosto em vários frames."""
import cv2
import numpy as np


def detectar(caminho, amostras=40, presenca_min=0.3):
    """Retorna (x, y, w, h) da facecam ou None se não achar uma posição estável.

    A webcam fica parada no layout, então o rosto aparece sempre na mesma região;
    rostos de personagens do jogo aparecem em posições espalhadas e são descartados.
    "Rosto" cravado no mesmo ponto em todos os frames (boneco ou quadro no cenário atrás
    do streamer) perde para o rosto que se mexe: gente balança de um frame para o outro.
    """
    cap = cv2.VideoCapture(caminho)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    L, A = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if total <= 0 or L == 0:
        return None
    cascata = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    achados = []  # (frame, cx, cy, w, h)
    lidos = 0
    for n, pos in enumerate(np.linspace(0, total - 1, amostras).astype(int)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
        ok, frame = cap.read()
        if not ok:
            continue
        lidos += 1
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        for (x, y, w, h) in cascata.detectMultiScale(cinza, 1.1, 6, minSize=(A // 18, A // 18)):
            achados.append((n, x + w / 2, y + h / 2, w, h))
    cap.release()
    if not achados or not lidos:
        return None
    return escolher(np.array(achados, dtype=float), L, A, lidos, presenca_min)


def escolher(achados, L, A, lidos, presenca_min=0.3):
    """Das detecções (frame, cx, cy, w, h) feitas em `lidos` frames, tira a caixa da facecam ou None."""
    # agrupa por célula de uma grade 8x8 e pega a célula com rosto em mais frames distintos
    grupos = {}
    for i, a in enumerate(achados):
        grupos.setdefault((int(a[1] * 8 / L), int(a[2] * 8 / A)), []).append(i)
    indices = max(grupos.values(), key=lambda g: _frames(achados[g]))
    melhor = achados[indices]
    if _frames(melhor) / lidos < presenca_min:
        return None

    # célula vencedora com "rosto" parado (objeto no cenário da webcam, foto fixa na tela):
    # quem define a caixa é o rosto que se mexe, se houver um com presença suficiente
    parado = _parados(achados)
    if parado[indices].any():
        vivo = _janela(achados[~parado], L, A)
        if len(vivo) and _frames(vivo) / lidos >= presenca_min:
            melhor = vivo

    _, cx, cy, fw, _ = np.median(melhor, axis=0)
    if fw * 3.2 > L * 0.5:
        return None  # rosto grande demais para ser webcam (close de cutscene)
    # caixa 16:9 em volta do rosto (rosto ocupa ~1/3 da largura de uma webcam típica)
    w = min(L, fw * 3.2)
    h = min(A, w * 9 / 16)
    x = float(np.clip(cx - w / 2, 0, L - w))
    y = float(np.clip(cy - h * 0.42, 0, A - h))
    return tuple(int(v) // 2 * 2 for v in (x, y, w, h))


def _frames(achados):
    return len(np.unique(achados[:, 0]))


def _parados(achados, minimo=4, folga=0.02, quase_todos=0.85):
    """Marca as detecções cravadas num ponto: objeto que o detector toma por rosto.

    Parado é o ponto em que quase todas as detecções em volta (até meio rosto de distância)
    caem no mesmo lugar, com folga de 1,5 px ou `folga` x o tamanho do rosto, em pelo menos
    `minimo` frames. Em 69 clipes medidos, objeto parado teve de 92% a 100% das detecções
    nessa folga; rosto de streamer, mesmo quieto, no máximo 62%.
    """
    parado = np.zeros(len(achados), dtype=bool)
    for _, cx, cy, w, _ in achados:
        dx, dy = np.abs(achados[:, 1] - cx), np.abs(achados[:, 2] - cy)
        tol = max(1.5, w * folga)
        cravado = (dx <= tol) & (dy <= tol)
        em_volta = (dx <= w / 2) & (dy <= w / 2)
        n = _frames(achados[cravado])
        if n >= minimo and n >= quase_todos * _frames(achados[em_volta]):
            parado |= cravado
    return parado


def _janela(achados, L, A):
    """Detecções da janela, do tamanho de uma célula da grade, com rosto em mais frames distintos.

    A janela é centrada numa detecção em vez de presa à grade, para o rosto que fica em cima
    da divisa entre células não sair repartido entre elas.
    """
    melhor, nota = achados[:0], (0, 0.0)
    for _, cx, cy, _, _ in achados:
        grupo = achados[(np.abs(achados[:, 1] - cx) <= L / 16) & (np.abs(achados[:, 2] - cy) <= A / 16)]
        # no empate, fica a janela mais bem centrada no próprio grupo
        desvio = np.hypot(cx - np.median(grupo[:, 1]), cy - np.median(grupo[:, 2]))
        if (_frames(grupo), -desvio) > nota:
            melhor, nota = grupo, (_frames(grupo), -desvio)
    return melhor


def interpretar(texto):
    """'x:y:w:h' -> tupla, para informar a posição da cam manualmente."""
    partes = [int(p) for p in texto.replace(",", ":").split(":")]
    if len(partes) != 4:
        raise ValueError("use o formato x:y:w:h")
    return tuple(partes)
