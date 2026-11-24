"""Selo do canal: a marca d'água no centro e o nome escrito em círculo em volta dela."""
import math

from PIL import Image, ImageDraw, ImageFont

FONTE = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"


def selo(destino, logo=None, texto="CLIPES LEONIDA", lado=600, repeticoes=2,
         fundo=(24, 8, 34, 240), borda=(255, 46, 126, 255)):
    """Gera um PNG transparente de `lado` x `lado`. Sem `logo`, o miolo fica só com as iniciais."""
    s = 2  # desenha no dobro e reduz, para as letras saírem lisas
    L = lado * s
    img = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, L - 1, L - 1), fill=borda)
    e = int(L * 0.012)
    d.ellipse((e, e, L - 1 - e, L - 1 - e), fill=fundo)
    miolo = int(L * 0.62)
    m0 = (L - miolo) // 2
    if logo:
        arte = Image.open(logo).convert("RGBA")
        lado_arte = min(arte.size)
        arte = arte.crop(((arte.width - lado_arte) // 2, (arte.height - lado_arte) // 2,
                          (arte.width + lado_arte) // 2, (arte.height + lado_arte) // 2)).resize((miolo, miolo), Image.LANCZOS)
        mascara = Image.new("L", (miolo, miolo), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, miolo - 1, miolo - 1), fill=255)
        img.paste(arte, (m0, m0), Image.composite(arte.getchannel("A"), Image.new("L", (miolo, miolo), 0), mascara))
        d.ellipse((m0 - e, m0 - e, m0 + miolo + e, m0 + miolo + e), outline=borda, width=e * 2)
    else:
        d.ellipse((m0, m0, m0 + miolo, m0 + miolo), fill=(200, 30, 99, 255))
        f = ImageFont.truetype(FONTE, int(miolo * 0.5))
        d.text((L / 2, L / 2), "CL", font=f, fill="white", anchor="mm")
    # nome em círculo: cada letra é desenhada em pé e girada para a sua posição
    frase = (texto + " • ") * repeticoes
    f = ImageFont.truetype(FONTE, int(L * 0.105))
    raio = L * 0.405
    larguras = [f.getlength(c) for c in frase]
    passo = 360 / sum(larguras)
    ang = -90 - larguras[0] * passo / 2
    for c, w in zip(frase, larguras):
        ang += w * passo / 2
        t = Image.new("RGBA", (int(w) + 8, int(L * 0.14)), (0, 0, 0, 0))
        ImageDraw.Draw(t).text((t.width / 2, t.height / 2), c, font=f, fill="white", anchor="mm")
        t = t.rotate(-(ang + 90), expand=True, resample=Image.BICUBIC)
        x = L / 2 + raio * math.cos(math.radians(ang)) - t.width / 2
        y = L / 2 + raio * math.sin(math.radians(ang)) - t.height / 2
        img.alpha_composite(t, (int(x), int(y)))
        ang += w * passo / 2
    img.resize((lado, lado), Image.LANCZOS).save(destino)
    return destino
