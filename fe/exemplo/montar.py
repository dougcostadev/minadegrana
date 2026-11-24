"""Monta um vídeo vertical do canal de fé a partir de um roteiro JSON.

Uso: python montar.py roteiro.json pasta_de_trabalho
A pasta precisa ter fala/1.wav, fala/2.wav... (uma narração por frase, geradas com ../piloto/gerar.py).

Cada frase do roteiro tem: texto, img (pintura), foco [x, y] de 0 a 1 (onde o recorte 9:16 centra),
zoom "in" ou "out", e opcionalmente estilo "versiculo" (texto dourado em serifa) ou "cta" (destaque final).
"""
import json, os, re, subprocess, sys
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
from cortes import legendas

rot = json.load(open(sys.argv[1], encoding="utf-8")); V = os.path.abspath(sys.argv[2])
IMG = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), rot.get("pasta_img", "img"))
W, H, FPS = 1080, 1920, 30
frases = rot["frases"]; INICIO, CAUDA = 0.15, 2.2
FONTES = os.path.join(RAIZ, "marca", "fontes")

def run(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
def dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                        capture_output=True, text=True).stdout)
def t(s): return f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"
def tam(p): return [int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                    "stream=width,height", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.split(",")[:2]]

# 1. apara o silêncio de cada frase e monta a faixa de voz com pausas
corte = ("silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,areverse,"
         "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.05,areverse")
ini, pos, palavras = [], INICIO, []
for i, f in enumerate(frases):
    a = f"{V}/fala/{i+1}.wav"; b = f"{V}/fala/{i+1}-a.wav"
    run("-i", a, "-af", corte, "-ar", "48000", "-ac", "1", b)
    d = dur(b); ini.append((pos, pos + d))
    ws = [(float(x), float(y), str(z).strip()) for x, y, z in (legendas.transcrever(b, idioma="pt") or [])]
    alvo = f["texto"].split()
    if len(ws) == len(alvo):  # tempo do whisper, grafia do roteiro
        ws = [(x, y, z) for (x, y, _), z in zip(ws, alvo)]
    else:  # tempos proporcionais ao tamanho das palavras
        print("aviso: transcrição difere na frase", i + 1, [w[2] for w in ws])
        tot = sum(len(z) for z in alvo); c = 0.0; novo = []
        for z in alvo:
            novo.append((d * c / tot, d * (c + len(z)) / tot, z)); c += len(z)
        ws = novo
    palavras.append([(pos + x, pos + y, z) for x, y, z in ws])
    pos += d + f.get("pausa", 0.45)
FIM = pos - frases[-1].get("pausa", 0.45) + CAUDA
partes = "".join(f"[{i}:a]adelay={int(a*1000)}:all=1[s{i}];" for i, (a, _) in enumerate(ini))
run(*sum((["-i", f"{V}/fala/{i+1}-a.wav"] for i in range(len(frases))), []), "-filter_complex",
    partes + "".join(f"[s{i}]" for i in range(len(frases))) +
    f"amix=inputs={len(frases)}:normalize=0,apad=whole_dur={FIM},loudnorm=I=-15:TP=-1.5:LRA=9[a]",
    "-map", "[a]", "-t", f"{FIM}", "-ar", "48000", f"{V}/voz.wav")

# 2. legenda: blocos de até 3 palavras, palavra falada em amarelo; versículo em serifa dourada
AMARELO, OURO = "&H4DE1FF&", "&H7FD4FF&"
def blocos(ws):
    out, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) == 3 or re.search(r"[.,:;!?]$", w[2]):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out
def limpa(z): return re.sub(r"[.,:;]+$", "", z).upper()
ev = []
for i, (f, ws) in enumerate(zip(frases, palavras)):
    if f.get("estilo") == "versiculo":
        txt = f.get("tela", f["texto"]).replace("\n", "\\N")
        ev.append(f"Dialogue: 0,{t(ws[0][0])},{t(ws[-1][1] + 0.5)},V,,0,0,0,,{{\\pos(540,1180)\\fad(200,200)}}{txt}")
        continue
    bs = blocos(ws)
    for bi, b in enumerate(bs):
        fim_bloco = bs[bi + 1][0][0] if bi + 1 < len(bs) else b[-1][1] + 0.25
        for k, (a, _, _) in enumerate(b):
            fim = b[k + 1][0] if k + 1 < len(b) else fim_bloco
            cor = OURO if f.get("estilo") == "cta" else AMARELO
            txt = " ".join(("{\\c" + cor + "}" + limpa(z) + "{\\c&HFFFFFF&}") if j == k else limpa(z)
                           for j, (_, _, z) in enumerate(b))
            pop = "\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)" if k == 0 else ""
            ev.append(f"Dialogue: 0,{t(a)},{t(fim)},L,,0,0,0,,{{\\pos(540,1180){pop}}}{txt}")
ev.append(f"Dialogue: 1,{t(0)},{t(ini[0][1] + 0.4)},G,,0,0,0,,{{\\pos(540,380)\\fad(0,200)}}{rot['gancho']}")
if rot.get("chamada"):
    ev.append(f"Dialogue: 1,{t(FIM - CAUDA + 0.2)},{t(FIM)},C,,0,0,0,,{{\\pos(540,1500)\\fad(250,0)}}{rot['chamada']}")
cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: L,Poppins ExtraBold,104,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,0,0,0,0,100,100,0,0,1,7,4,5,70,70,0,1
Style: V,DejaVu Serif,84,&H007FD4FF,&H007FD4FF,&H00000000,&HA0000000,1,0,0,0,100,100,2,0,1,6,4,5,90,90,0,1
Style: G,Poppins ExtraBold,64,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,3,18,0,5,70,70,0,1
Style: C,Poppins SemiBold,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,1,0,1,4,2,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(V + "/legenda.ass", "w", encoding="utf-8").write(cab + "\n".join(ev) + "\n")

# 3. planos: um por frase (ou dois, se a frase tiver "corte"), recorte 9:16 em volta do foco + zoom lento
S = [a for a, _ in ini]; S[0] = 0.0; S.append(FIM)
planos = []
for i, f in enumerate(frases):
    a, b = S[i], S[i + 1]
    if f.get("corte"):  # segundo enquadramento na palavra indicada
        m = next((x - 0.05 for x, _, z in palavras[i] if z.lower().startswith(f["corte"]["palavra"])), (a + b) / 2)
        planos += [(f["img"], f["foco"], f.get("aperto", 1.0), f.get("zoom", "in"), a, m),
                   (f.get("corte", {}).get("img", f["img"]), f["corte"]["foco"], f["corte"].get("aperto", 1.6),
                    f["corte"].get("zoom", "in"), m, b)]
    else:
        planos.append((f["img"], f["foco"], f.get("aperto", 1.0), f.get("zoom", "in"), a, b))
lista = []
for n, (img, (fx, fy), aperto, zoom, a, b) in enumerate(planos):
    arq = os.path.join(IMG, img); iw, ih = tam(arq)
    h = min(ih, iw * 16 / 9) / aperto; w = h * 9 / 16
    x = min(max(fx * iw - w / 2, 0), iw - w); y = min(max(fy * ih - h / 2, 0), ih - h)
    q = int(round((b - a) * FPS)); sai = f"{V}/plano{n}.mp4"
    z = f"1+0.10*on/{q}" if zoom == "in" else f"1.10-0.10*on/{q}"
    vf = (f"crop={int(w)}:{int(h)}:{int(x)}:{int(y)},scale=2160:3840:flags=lanczos,"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={q}:s={W}x{H}:fps={FPS},setsar=1")
    run("-loop", "1", "-i", arq, "-vf", vf, "-frames:v", str(q), "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p", sai)
    lista.append(f"file '{sai}'")
open(V + "/planos.txt", "w").write("\n".join(lista) + "\n")

# 4. passe final: cor quente, vinheta e legenda. Sem trilha por padrão: o som em alta do TikTok entra na postagem.
vf = (f"[0:v]eq=brightness=-0.04:contrast=1.07:saturation=0.95,colorbalance=rm=0.04:bm=-0.04,vignette=PI/5,"
      f"ass={V}/legenda.ass:fontsdir={FONTES},fade=t=in:st=0:d=0.3,fade=t=out:st={FIM-0.8:.2f}:d=0.8[v]")
ent = ["-f", "concat", "-safe", "0", "-i", V + "/planos.txt", "-i", V + "/voz.wav"]
if rot.get("musica"):  # opcional, com a música baixando quando há fala
    musica = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), rot["musica"]["arquivo"])
    ent += ["-ss", str(rot["musica"].get("de", 0)), "-i", musica]
    fa = (f"[1:a]asplit=2[voz][chave];[2:a]aresample=48000,volume={rot['musica'].get('volume', 3.0)},"
          f"afade=t=in:st=0:d=1.0,afade=t=out:st={FIM-2.0:.2f}:d=2.0[m];"
          f"[m][chave]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=450[md];"
          f"[voz][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]")
else:
    fa = "[1:a]anull[a]"
run(*ent, "-filter_complex", vf + ";" + fa, "-map", "[v]", "-map", "[a]", "-t", f"{FIM:.2f}", "-c:v", "libx264",
    "-preset", "medium", "-crf", "20", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-c:a", "aac",
    "-b:a", "192k", "-movflags", "+faststart", V + "/" + rot.get("saida", "exemplo.mp4"))
print("duração", round(FIM, 2), "| planos", len(planos))
