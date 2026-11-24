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


# Pedido fixo: convida para um grupo com nome (Leonida é o estado do jogo) e lembra de quem fica de fora.
FIXO = ("ENTRA PRA LEONIDA", "SEGUE E NÃO FICA DE FORA")


def _seguir(img, com_cam):
    """Pedido para seguir, fixo no canto de cima à direita o vídeo inteiro (espelha o selo, longe do rosto)."""
    f1, f2 = ImageFont.truetype(FORTE, 31), ImageFont.truetype(MEDIA, 20)
    larg, alt = int(max(f1.getlength(FIXO[0]), f2.getlength(FIXO[1]))) + 2 * 24, 88
    x0, y0 = L - 28 - larg, (199 if com_cam else 356)
    s = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle((x0, y0 + 8, x0 + larg, y0 + alt + 8), 28, fill=(0, 0, 0, 130))
    img.alpha_composite(s.filter(ImageFilter.GaussianBlur(10)))
    m = Image.new("L", (larg, alt), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, larg - 1, alt - 1), 28, fill=255)
    img.paste(_degrade(larg, alt, (AMARELO, LARANJA)), (x0, y0), m)
    d = ImageDraw.Draw(img)
    d.text((x0 + larg // 2, y0 + 31), FIXO[0], font=f1, fill=NOITE, anchor="mm")
    d.text((x0 + larg // 2, y0 + 64), FIXO[1], font=f2, fill=NOITE, anchor="mm")


# Frases da chamada para seguir, que troca de lugar com o gancho nos segundos finais.
# Todas puxam pelo pertencimento: existe um grupo, ele tem lugar para você, e só você ainda está fora.
# Nada de número inventado de seguidores: quando a conta tiver um número que impressiona, ele entra aqui.
CHAMADAS = [
    ("TODO FÃ DE GTA VI TEM LUGAR AQUI", "SÓ FALTA VOCÊ. SEGUE."),
    ("QUEM É DE LEONIDA JÁ SEGUE", "VAI FICAR DE FORA?"),
    ("A GENTE VÊ GTA VI JUNTO TODO DIA", "SÓ FALTA VOCÊ. SEGUE."),
    ("VOCÊ SE DIZ FÃ DE GTA VI", "E AINDA NÃO SEGUE ESSE PERFIL?"),
]


def chamada(destino, frase=None, indice=0, com_cam=True, estalo=False):
    """Moldura dos segundos finais: no lugar do gancho entra o pedido para seguir, com a 2ª linha em amarelo.

    `estalo=True` gera a versão de entrada, com a placa rosa, mostrada por um instante para puxar o olho.
    """
    l1, l2 = frase or CHAMADAS[indice % len(CHAMADAS)]
    img = Image.new("RGBA", (L, A), (0, 0, 0, 0))
    if com_cam:
        img.alpha_composite(_degrade(L, 8), (0, A_CAM - 4))
    for corpo in (52, 48, 44, 40, 36):
        f = ImageFont.truetype(FORTE, corpo)
        if max(f.getlength(l1), f.getlength(l2)) <= L - 2 * 80:
            break
    alt_linha = int(corpo * 1.2)
    larg = int(max(f.getlength(l1), f.getlength(l2))) + 2 * 40
    alt = alt_linha * 2 + 2 * 24
    centro = A_CAM if com_cam else 190
    caixa = ((L - larg) // 2, centro - alt // 2, (L + larg) // 2, centro + alt // 2)
    # etiqueta "SEGUE O PERFIL" no lugar da do streamer
    fr = ImageFont.truetype(FORTE, 28)
    lt, at = int(fr.getlength("SEGUE O PERFIL")) + 2 * 28, 54
    y0 = caixa[1] - at + 10 if com_cam else caixa[3] - 10
    m = Image.new("L", (lt, at), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, lt - 1, at - 1), 18, fill=255)
    img.paste(_degrade(lt, at, (AMARELO, LARANJA)), (L // 2 - lt // 2, y0), m)
    ImageDraw.Draw(img).text((L // 2, y0 + (at - 10) // 2 + (0 if com_cam else 10)), "SEGUE O PERFIL", font=fr, fill=NOITE, anchor="mm")
    if estalo:
        caixa = (caixa[0] - 14, caixa[1] - 8, caixa[2] + 14, caixa[3] + 8)
    _placa(img, caixa, raio=34, fundo=(ROSA if estalo else NOITE) + (250,), cores=(AMARELO, LARANJA, ROSA))
    d = ImageDraw.Draw(img)
    meio = (caixa[1] + caixa[3]) // 2
    d.text((L // 2, meio - alt_linha // 2), l1, font=f, fill=BRANCO, anchor="mm")
    d.text((L // 2, meio + alt_linha // 2), l2, font=f, fill=BRANCO if estalo else AMARELO, anchor="mm")
    _seguir(img, com_cam)
    if os.path.exists(SELO):
        sx, sy, lado = (28, 168, 150) if com_cam else (28, 330, 140)
        img.alpha_composite(Image.open(SELO).convert("RGBA").resize((lado, lado), Image.LANCZOS), (sx, sy))
    img.save(destino)
    return destino


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

    _seguir(img, com_cam)
    if os.path.exists(SELO):  # selo do canal sozinho no canto de cima
        sx, sy, lado = (28, 168, 150) if com_cam else (28, 330, 140)
        img.alpha_composite(Image.open(SELO).convert("RGBA").resize((lado, lado), Image.LANCZOS), (sx, sy))
    img.save(destino)
    return destino


TITULO = os.path.join(RAIZ, "fontes", "Anton-Regular.ttf")


def _titulo(texto, largura, destaque=None, corpo_max=210, linhas_max=3):
    """Desenha o título da capa em linhas curtas, com contorno escuro e sombra rosa; devolve a imagem."""
    palavras = texto.upper().split()
    for corpo in range(corpo_max, 90, -10):
        f = ImageFont.truetype(TITULO, corpo)
        linhas, atual = [], ""
        for p in palavras:
            tenta = (atual + " " + p).strip()
            if f.getlength(tenta) <= largura or not atual:
                atual = tenta
            else:
                linhas.append(atual)
                atual = p
        linhas.append(atual)
        if len(linhas) <= linhas_max and all(f.getlength(l) <= largura for l in linhas):
            break
    alt_linha = int(corpo * 1.08)
    img = Image.new("RGBA", (largura + 80, alt_linha * len(linhas) + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dest = (destaque or linhas[-1]).upper()
    for i, l in enumerate(linhas):
        y = 40 + i * alt_linha + alt_linha // 2
        cor = AMARELO if l in dest or dest in l else BRANCO
        d.text((img.width // 2 + 8, y + 10), l, font=f, fill=ROSA + (255,), anchor="mm", stroke_width=14, stroke_fill=ROSA + (255,))
        d.text((img.width // 2, y), l, font=f, fill=cor + (255,), anchor="mm", stroke_width=14, stroke_fill=NOITE + (255,))
    return img


def capa(destino, quadro, titulo, streamer=None, rosto=None, destaque=None, foco=0.5, evitar=None):
    """Capa 1080x1920 do corte: o momento-chave do jogo ao fundo, título grande, rosto do streamer e selo.

    `quadro` e `rosto` são imagens (PIL). Tudo o que importa fica na faixa central, porque as
    grades de perfil do TikTok e do Instagram cortam o topo e o pé da capa.
    """
    q = quadro.convert("RGB")
    larg = int(q.height * 9 / 16)
    x0 = int(min(max(0, q.width * foco - larg / 2), q.width - larg))
    if evitar:  # a webcam do streamer no quadro original não deve aparecer no fundo da capa
        ex, _, ew, _ = evitar
        if x0 < ex + ew and x0 + larg > ex:
            x0 = ex - larg if ex - larg >= 0 else (ex + ew if ex + ew + larg <= q.width else x0)
    fundo = q.crop((x0, 0, x0 + larg, q.height)).resize((L, A), Image.LANCZOS).filter(ImageFilter.UnsharpMask(3, 60, 2))
    img = fundo.convert("RGBA")
    # escurece em cima e embaixo para o texto e o rosto destacarem
    sombra = Image.new("L", (1, A), 0)
    px = sombra.load()
    for y in range(A):
        cima = max(0.0, 1 - y / 760)
        baixo = max(0.0, (y - 1050) / 870)
        px[0, y] = int(215 * max(cima, baixo) ** 1.3)
    img.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (L, A), NOITE).split(), sombra.resize((L, A)))))

    t = _titulo(titulo, L - 150, destaque).rotate(4, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(t, ((L - t.width) // 2, 560 - t.height // 2))

    base_y = 1290
    if rosto is not None:  # bolha com o rosto do streamer e o nome ao lado
        lado = 330
        r = rosto.convert("RGB")
        m = min(r.size)
        r = r.crop(((r.width - m) // 2, (r.height - m) // 2, (r.width + m) // 2, (r.height + m) // 2)).resize((lado, lado), Image.LANCZOS)
        anel = _degrade(lado + 28, lado + 28)
        ma = Image.new("L", anel.size, 0)
        ImageDraw.Draw(ma).ellipse((0, 0, anel.width - 1, anel.height - 1), fill=255)
        img.paste(anel, (70, base_y - lado // 2 - 14), ma)
        mr = Image.new("L", (lado, lado), 0)
        ImageDraw.Draw(mr).ellipse((0, 0, lado - 1, lado - 1), fill=255)
        img.paste(r, (84, base_y - lado // 2), mr)
    if streamer:
        nome = postagem.nome(streamer).upper()
        fn = ImageFont.truetype(FORTE, 58)
        fr = ImageFont.truetype(MEDIA, 30)
        x = 450 if rosto is not None else 90
        d = ImageDraw.Draw(img)
        d.text((x, base_y - 44), "DA LIVE DE", font=fr, fill=CREME, anchor="lm", stroke_width=4, stroke_fill=NOITE)
        d.text((x, base_y + 14), nome, font=fn, fill=BRANCO, anchor="lm", stroke_width=6, stroke_fill=NOITE)
    if os.path.exists(SELO):
        img.alpha_composite(Image.open(SELO).convert("RGBA").resize((230, 230), Image.LANCZOS), (L - 290, 1420))
    img.convert("RGB").save(destino, quality=92)
    return destino
