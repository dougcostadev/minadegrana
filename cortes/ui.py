"""Identidade visual dos cortes: gancho, plaquinha do streamer, linha da divisória e selo,
desenhados numa imagem transparente do tamanho do vídeo, que o render sobrepõe de uma vez."""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import postagem

L, A, A_CAM = 1080, 1920, 608
RAIZ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "marca")
FORTE = os.path.join(RAIZ, "fontes", "Poppins-ExtraBold.ttf")
MEDIA = os.path.join(RAIZ, "fontes", "Poppins-SemiBold.ttf")
SELO = os.path.join(RAIZ, "selo.png")

# cores tiradas da logo (flamingo no pôr do sol)
ROSA, LARANJA, AMARELO = (255, 46, 126), (255, 122, 26), (255, 194, 31)
NOITE, CREME, BRANCO = (27, 10, 42), (255, 224, 190), (255, 255, 255)


def _degrade(largura, altura, cores=(ROSA, LARANJA, AMARELO)):
    """Faixa horizontal que passa pelas cores dadas, da esquerda para a direita."""
    faixa = Image.new("RGBA", (largura, 1))
    px = faixa.load()
    trechos = len(cores) - 1
    for x in range(largura):
        p = x / max(1, largura - 1) * trechos
        i = min(trechos - 1, int(p))
        f = p - i
        px[x, 0] = tuple(int(cores[i][k] + (cores[i + 1][k] - cores[i][k]) * f) for k in range(3)) + (255,)
    return faixa.resize((largura, altura))


def _placa(img, caixa, raio, borda=6, fundo=NOITE + (245,), sombra=True, cores=(ROSA, LARANJA, AMARELO)):
    """Retângulo arredondado escuro com contorno em degradê e sombra suave."""
    x0, y0, x1, y1 = caixa
    w, h = x1 - x0, y1 - y0
    if sombra:
        s = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).rounded_rectangle((x0, y0 + 10, x1, y1 + 10), raio, fill=(0, 0, 0, 120))
        img.alpha_composite(s.filter(ImageFilter.GaussianBlur(12)))
    mascara = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, w - 1, h - 1), raio, fill=255)
    img.paste(_degrade(w, h, cores), (x0, y0), mascara)
    ImageDraw.Draw(img).rounded_rectangle((x0 + borda, y0 + borda, x1 - borda, y1 - borda), max(2, raio - borda), fill=fundo)


def _quebrar(texto, fonte, largura, linhas=2):
    """Divide o texto em até `linhas` linhas de largura parecida que caibam em `largura`."""
    palavras = texto.split()
    melhor = None
    for corte in range(len(palavras) + 1):
        partes = [" ".join(palavras[:corte]), " ".join(palavras[corte:])] if linhas == 2 else [texto]
        partes = [p for p in partes if p]
        maior = max(fonte.getlength(p) for p in partes)
        if maior <= largura and (melhor is None or maior < melhor[0]):
            melhor = (maior, partes)
    return melhor[1] if melhor else None


def _etiqueta(img, streamer, cx, y_base, para_cima=True):
    """Etiqueta "DA LIVE DE FULANO", presa à placa do gancho: fica na divisória, longe do rosto.

    Não cita a plataforma de origem (Twitch, Kick): outras redes não gostam de ver o nome delas.
    """
    nome = postagem.nome(streamer).upper()
    fr, fn = ImageFont.truetype(MEDIA, 26), ImageFont.truetype(FORTE, 30)
    antes = "DA LIVE DE "
    larg = int(fr.getlength(antes) + fn.getlength(nome)) + 2 * 26
    alt = 54
    y0 = y_base - alt + 10 if para_cima else y_base - 10
    caixa = (cx - larg // 2, y0, cx + larg // 2, y0 + alt)
    mascara = Image.new("L", (larg, alt), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, larg - 1, alt - 1), 18, fill=255)
    img.paste(_degrade(larg, alt, (ROSA, LARANJA)), caixa[:2], mascara)
    d = ImageDraw.Draw(img)
    meio = y0 + (alt - 10) // 2 + (0 if para_cima else 10)
    x = caixa[0] + 26
    d.text((x, meio), antes, font=fr, fill=NOITE, anchor="lm")
    d.text((x + fr.getlength(antes), meio), nome, font=fn, fill=BRANCO, anchor="lm")


def moldura(destino, gancho=None, streamer=None, com_cam=True):
    """Gera o PNG transparente (1080x1920) com os elementos fixos do corte."""
    img = Image.new("RGBA", (L, A), (0, 0, 0, 0))

    if com_cam:  # linha fina em degradê na divisória entre a câmera e o jogo
        img.alpha_composite(_degrade(L, 8), (0, A_CAM - 4))

    centro = A_CAM if com_cam else 190
    caixa = (L // 2, centro, L // 2, centro)
    partes, f, alt_linha = [], None, 0
    if gancho:
        texto = gancho.upper().strip()
        for corpo in (56, 52, 48, 44, 40):
            f = ImageFont.truetype(FORTE, corpo)
            partes = _quebrar(texto, f, L - 2 * 96)
            if partes:
                break
        partes = partes or [texto]
        alt_linha = int(corpo * 1.18)
        larg = int(max(f.getlength(p) for p in partes)) + 2 * 40
        alt = alt_linha * len(partes) + 2 * 22
        caixa = ((L - larg) // 2, centro - alt // 2, (L + larg) // 2, centro + alt // 2)
    if streamer:  # desenhada antes da placa, que cobre a ponta dela
        _etiqueta(img, streamer, L // 2, caixa[1] if com_cam else caixa[3], para_cima=com_cam)
    if gancho:
        _placa(img, caixa, raio=34)
        d = ImageDraw.Draw(img)
        y = caixa[1] + 22 + alt_linha // 2
        for p in partes:
            d.text((L // 2, y), p, font=f, fill=BRANCO, anchor="mm")
            y += alt_linha

    if os.path.exists(SELO):  # selo do canal sozinho no canto de cima
        sx, sy, lado = (28, 168, 150) if com_cam else (28, 330, 140)
        img.alpha_composite(Image.open(SELO).convert("RGBA").resize((lado, lado), Image.LANCZOS), (sx, sy))
    img.save(destino)
    return destino
