"""Edit de meme sobre um corte vertical limpo.

A receita é a lista de blocos na ordem em que aparecem no vídeo final. Cada bloco é um trecho do
clipe, uma pausa com zoom ou o rosto do streamer em tela cheia, e pode levar legenda de meme,
figurinha (GIF), efeito sonoro e tremida. Por cima de tudo vão a moldura do canal e, no primeiro
décimo de segundo, a capa.
"""
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

from . import render

L, A, A_CAM, FPS = 1080, 1920, 608, 30
RAIZ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "marca")
ACERVO = os.path.join(RAIZ, "memes.json")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
CORES = {"branco": "&HFFFFFF&", "amarelo": "&H1FC2FF&", "rosa": "&H7E2EFF&"}
ALTURA_TEXTO = {"cima": 820, "meio": 1180, "baixo": 1480}  # acima da área que o texto dos aplicativos cobre
CANTO = {"dir-cima": (1, 700), "esq-cima": (0, 700), "esq-baixo": (0, 1380), "dir-baixo": (1, 1380)}
ENC = ["-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def _ff(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def _pagina(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read()


def buscar_sons(termo, quantos=8):
    """Procura efeitos sonoros de meme. Devolve [(título, endereço)]."""
    h = _pagina("https://www.myinstants.com/pt/search/?name=" + urllib.parse.quote_plus(termo)).decode("utf-8", "ignore")
    caminhos = re.findall(r"play\('(/media/sounds/[^']+)'", h)
    titulos = re.findall(r'class="instant-link[^"]*"[^>]*>([^<]+)<', h)
    return [(t.strip(), "https://www.myinstants.com" + urllib.parse.quote(c)) for c, t in list(zip(caminhos, titulos))[:quantos]]


def buscar_gifs(termo, quantos=8):
    """Procura GIFs de meme (em vídeo). Devolve a lista de endereços."""
    h = _pagina("https://tenor.com/pt-BR/search/" + urllib.parse.quote(termo.strip().replace(" ", "-")) + "-gifs").decode("utf-8", "ignore")
    vistos = []
    for u in re.findall(r"https://media\d*\.tenor\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_%.-]+\.mp4", h):
        if u not in vistos:
            vistos.append(u)
    return vistos[:quantos]


def acervo():
    with open(ACERVO, encoding="utf-8") as f:
        return json.load(f)


def recurso(tipo, nome, pasta="trabalho/memes"):
    """Caminho local de um som ("sons") ou GIF ("gifs"); `nome` é um apelido do acervo ou um endereço."""
    if nome.startswith("http"):
        url, apelido = nome, re.sub(r"[^a-z0-9]+", "-", urllib.parse.unquote(nome.split("/")[-1].rsplit(".", 1)[0]).lower()).strip("-")
        apelido += "-" + re.sub(r"[^A-Za-z0-9]", "", nome.split("/")[-2])[:8]
    else:
        itens = acervo()[tipo]
        if nome not in itens:
            raise KeyError(f"{tipo[:-1]} '{nome}' não está no acervo; use um destes ou um endereço: {', '.join(sorted(itens))}")
        url, apelido = itens[nome], nome
    destino = os.path.join(pasta, tipo, apelido + (".mp3" if tipo == "sons" else ".mp4"))
    if not os.path.exists(destino):
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as f:
            f.write(_pagina(url))
    return destino


def _lista(v, chave):
    """Aceita um apelido, um objeto ou uma lista deles; devolve sempre uma lista de objetos."""
    if v is None or v is False:
        return []
    itens = v if isinstance(v, list) else [v]
    return [{chave: i} if not isinstance(i, dict) else i for i in itens]


def _trecho(origem, destino, de, ate, vf=None):
    args = ["-ss", f"{de:.3f}", "-t", f"{ate - de:.3f}", "-i", origem]
    if vf:
        args += ["-vf", vf]
    _ff(*args, "-af", "aresample=48000", "-t", f"{ate - de:.3f}", *ENC, destino)


def _pausa(origem, destino, em, dur, alvo, zoom, lento, pb, quadro):
    _ff("-ss", f"{em:.3f}", "-i", origem, "-frames:v", "1", quadro)
    q = int(round(dur * FPS))
    tx, ty = alvo[0] * L * 2, alvo[1] * A * 2
    z = f"1+{zoom - 1}*on/{q}" if lento else f"min(1+{zoom - 1}*on/10,{zoom})"
    cor = "hue=s=0,eq=contrast=1.15:brightness=-0.04,vignette=PI/4," if pb else ""
    vf = (f"[0:v]{cor}scale={2 * L}:{2 * A}:flags=lanczos,zoompan=z='{z}':x='{tx}*(1-1/zoom)':y='{ty}*(1-1/zoom)'"
          f":d={q}:s={L}x{A}:fps={FPS},setsar=1[v]")
    _ff("-loop", "1", "-i", quadro, "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-t", f"{dur:.3f}", *ENC, destino)


def _t(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def editar(limpo, destino, blocos, moldura=None, capa=None, com_cam=True, trabalho="trabalho",
           chamada=None, chamada_seg=3.2, estalo=None):
    """Monta o vídeo final. Devolve {"duracao": s, "inicios": [início de cada bloco]}."""
    pasta = os.path.join(trabalho, os.path.splitext(os.path.basename(destino))[0] + ".edit")
    os.makedirs(pasta, exist_ok=True)
    segs = []
    for i, b in enumerate(blocos):
        tipo, arq = b.get("tipo", "clipe"), os.path.join(pasta, f"{i:02d}.mp4")
        if tipo == "pausa":
            dur = float(b.get("dur", 1.6))
            _pausa(limpo, arq, float(b["em"]), dur, b.get("alvo", (0.5, 0.65)), float(b.get("zoom", 1.4)),
                   bool(b.get("lento")), bool(b.get("pb")), os.path.join(pasta, f"{i:02d}.png"))
        elif tipo in ("clipe", "rosto"):
            de, ate = float(b["de"]), float(b["ate"])
            vf = None
            if tipo == "rosto" and com_cam:  # janela vertical dentro do painel da câmera, em tela cheia
                fx, fy = b.get("foco", (0.5, 0.6))
                x = int(min(max(0, fx * L - 146), L - 292))
                y = int(min(max(0, fy * A_CAM - 260), A_CAM - 520))
                vf = f"crop=292:520:{x}:{y},scale={L}:{A}:flags=bicubic,eq=saturation=1.5:contrast=1.2,unsharp=7:7:1.5"
            _trecho(limpo, arq, de, ate, vf)
            dur = ate - de
        else:
            raise ValueError(f"tipo de bloco desconhecido: {tipo}")
        segs.append((arq, dur, b))

    def quando(b, item, ini, dur, padrao=0.0):
        """Instante do item no vídeo final: `em` (tempo do clipe) ou `atraso` (a partir do início do bloco)."""
        if "em" in item and b.get("tipo", "clipe") != "pausa":
            return ini + float(item["em"]) - float(b["de"])
        return ini + float(item.get("atraso", padrao))

    eventos, tremidas, ocultar, figurinhas, sons, inicios = [], [], [], [], [], []
    t = 0.0
    for arq, dur, b in segs:
        ini, fim = t, t + dur
        inicios.append(round(ini, 3))
        for x in _lista(b.get("texto"), "texto"):
            a = quando(b, x, ini, dur, 0.1)
            z = min(fim, a + float(x["dur"])) if "dur" in x else fim
            pop = "\\fscx130\\fscy130\\t(0,120,\\fscx100\\fscy100)"
            cor = CORES.get(x.get("cor", "branco"), CORES["branco"])
            frase = str(x["texto"]).upper().replace("\n", "\\N")
            eventos.append(f"Dialogue: 1,{_t(a)},{_t(z)},X,,0,0,0,,{{\\pos({int(x.get('x', 540))},"
                           f"{ALTURA_TEXTO.get(x.get('pos', 'baixo'), 1560)}){pop}\\c{cor}\\fs{int(x.get('tam', 112))}}}{frase}")
        tr = b.get("tremer")
        if tr:
            for x in ([{"dur": 0.5}] if tr is True else [{"dur": tr}] if isinstance(tr, (int, float)) else _lista(tr, "dur")):
                a = quando(b, x, ini, dur)
                tremidas.append((a, min(fim, a + float(x.get("dur", 0.5)))))
        for x in _lista(b.get("meme"), "nome"):
            a = quando(b, x, ini, dur)
            figurinhas.append((recurso("gifs", x["nome"]), a, min(fim, a + float(x["dur"])) if "dur" in x else fim,
                               x.get("pos", "dir-cima"), int(x.get("larg", 380))))
        for x in _lista(b.get("som"), "nome"):
            sons.append((recurso("sons", x["nome"]), quando(b, x, ini, dur), float(x.get("volume", 1.0)),
                         float(x.get("de", 0)), x.get("ate")))
        if b.get("tipo") == "rosto" or b.get("sem_moldura"):
            ocultar.append((ini, fim))
        t = fim
    total = t

    ass = os.path.join(pasta, "meme.ass")
    with open(ass, "w", encoding="utf-8") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {L}
PlayResY: {A}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: X,Anton,112,&H00FFFFFF,&H00FFFFFF,&H002A0A1B,&H007E2EFF,0,0,0,0,100,100,1,0,1,9,6,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(eventos) + "\n")
    lista = os.path.join(pasta, "lista.txt")
    with open(lista, "w") as f:
        f.write("".join(f"file '{os.path.abspath(a)}'\n" for a, _, _ in segs))

    entradas, n = ["-f", "concat", "-safe", "0", "-i", lista], 1
    fc, v = [], "0:v"
    if tremidas:
        cond = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in tremidas)
        fc.append(f"[{v}]scale=1146:2038:flags=bicubic,crop={L}:{A}:x='33+if({cond},28*sin(2*PI*t*14),0)'"
                  f":y='59+if({cond},38*cos(2*PI*t*11),0)'[tr]")
        v = "tr"
    for arq, a, z, pos, larg in figurinhas:
        entradas += ["-stream_loop", "-1", "-i", arq]
        lado, y = CANTO.get(pos, CANTO["dir-cima"])
        x = L - 50 - larg - 16 if lado else 50
        fc.append(f"[{n}:v]scale={larg}:-2:flags=bicubic,pad=iw+16:ih+16:8:8:white,setpts=PTS-STARTPTS+{a:.2f}/TB[g{n}]")
        fc.append(f"[{v}][g{n}]overlay={x}:{y}:enable='between(t,{a:.2f},{z:.2f})'[f{n}]")
        v, n = f"f{n}", n + 1
    fc.append(f"[{v}]ass='{render._esc(ass)}':fontsdir='{render._esc(os.path.join(RAIZ, 'fontes'))}'[leg]")
    v = "leg"
    troca = max(0.0, total - chamada_seg) if chamada and total > chamada_seg + 5 else None
    if moldura:
        entradas += ["-i", moldura]
        fora = [f"between(t,{a:.2f},{b:.2f})" for a, b in ocultar] + ([f"gte(t,{troca:.2f})"] if troca is not None else [])
        visivel = ":enable='not(" + "+".join(fora) + ")'" if fora else ""
        fc.append(f"[{v}][{n}:v]overlay=0:0{visivel}[mol]")
        v, n = "mol", n + 1
    if troca is not None:  # nos segundos finais o gancho dá lugar ao pedido para seguir
        entradas += ["-i", chamada]
        fc.append(f"[{v}][{n}:v]overlay=0:0:enable='gte(t,{troca:.2f})'[cha]")
        v, n = "cha", n + 1
        if estalo:  # a entrada da chamada pisca em rosa por um instante
            entradas += ["-i", estalo]
            fc.append(f"[{v}][{n}:v]overlay=0:0:enable='between(t,{troca:.2f},{troca + 0.3:.2f})'[est]")
            v, n = "est", n + 1
    if capa:
        entradas += ["-i", capa]
        fc.append(f"[{n}:v]scale={L}:{A}[capa];[{v}][capa]overlay=0:0:enable='lt(t,0.1)'[cap]")
        v, n = "cap", n + 1
    audios = ["[0:a]"]
    for arq, a, vol, de, ate in sons:
        entradas += ["-i", arq]
        corte = f"atrim=start={de}" + (f":end={ate}" if ate is not None else "") + ",asetpts=PTS-STARTPTS,"
        fc.append(f"[{n}:a]{corte}aresample=48000,volume={vol},adelay={int(a * 1000)}:all=1[s{n}]")
        audios.append(f"[s{n}]")
        n += 1
    fc.append(f"{''.join(audios)}amix=inputs={len(audios)}:normalize=0:duration=first,alimiter=limit=0.95[a]")
    _ff(*entradas, "-filter_complex", ";".join(fc), "-map", f"[{v}]", "-map", "[a]", "-t", f"{total:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", *render._taxa(total), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", destino)
    return {"duracao": round(total, 2), "inicios": inicios}
