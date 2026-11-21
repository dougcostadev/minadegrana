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

    # agrupa por célula de uma grade 8x8 e pega a célula com rosto em mais frames distintos
    grupos = {}
    for a in achados:
        chave = (int(a[1] * 8 / L), int(a[2] * 8 / A))
        grupos.setdefault(chave, []).append(a)
    melhor = max(grupos.values(), key=lambda g: len({a[0] for a in g}))
    if len({a[0] for a in melhor}) / lidos < presenca_min:
        return None

    _, cx, cy, fw, _ = np.median(np.array(melhor), axis=0)
    # caixa 16:9 em volta do rosto (rosto ocupa ~1/3 da largura de uma webcam típica)
    w = min(L, fw * 3.2)
    h = min(A, w * 9 / 16)
    x = float(np.clip(cx - w / 2, 0, L - w))
    y = float(np.clip(cy - h * 0.42, 0, A - h))
    return tuple(int(v) // 2 * 2 for v in (x, y, w, h))


def interpretar(texto):
    """'x:y:w:h' -> tupla, para informar a posição da cam manualmente."""
    partes = [int(p) for p in texto.replace(",", ":").split(":")]
    if len(partes) != 4:
        raise ValueError("use o formato x:y:w:h")
    return tuple(partes)
