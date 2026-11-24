"""Piloto v2: narração frase a frase, cortes rápidos, legenda palavra a palavra e trilha."""
import json, os, re, subprocess, sys
sys.path.insert(0, "/home/user/minadegrana")
from cortes import legendas

B = "/home/user/voz"; V = B + "/v2"; W, H, FPS = 1080, 1920, 30
frases = json.load(open(V + "/frases.json", encoding="utf-8"))
PAUSA = [0.35, 0.45, 0.50, 0.45, 0.55, 0.50]; INICIO, CAUDA = 0.15, 1.5
MUSICA, MUSICA_DE = B + "/musica/At_Rest.mp3", 8.0

def run(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
def dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                        capture_output=True, text=True).stdout)
def t(s): return f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"

# 1. apara o silêncio de cada frase e monta a faixa de voz com pausas controladas
corte = "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,areverse,silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.05,areverse"
ini, pos, palavras = [], INICIO, []
for i, f in enumerate(frases):
    a = f"{V}/fala/{i+1}.wav"; b = f"{V}/fala/{i+1}-a.wav"
    run("-i", a, "-af", corte, "-ar", "48000", "-ac", "1", b)
    d = dur(b); ini.append((pos, pos + d))
    ws = [(float(x), float(y), str(z).strip()) for x, y, z in legendas.transcrever(b)]
    alvo = f.split()
    if len(ws) == len(alvo):
        ws = [(x, y, z) for (x, y, _), z in zip(ws, alvo)]
    else:  # tempos proporcionais ao tamanho das palavras do roteiro
        print("aviso: transcrição difere na frase", i + 1, [w[2] for w in ws]); tot = sum(len(z) for z in alvo); c = 0.0; novo = []
        for z in alvo:
            novo.append((d * c / tot, d * (c + len(z)) / tot, z)); c += len(z)
        ws = novo
    palavras.append([(pos + x, pos + y, z) for x, y, z in ws])
    pos += d + (PAUSA[i] if i < len(PAUSA) else 0)
FIM = pos + CAUDA
partes = "".join(f"[{i}:a]adelay={int(a*1000)}:all=1[s{i}];" for i, (a, _) in enumerate(ini))
run(*sum((["-i", f"{V}/fala/{i+1}-a.wav"] for i in range(len(frases))), []), "-filter_complex",
    partes + "".join(f"[s{i}]" for i in range(len(frases))) + f"amix=inputs={len(frases)}:normalize=0,apad=whole_dur={FIM},loudnorm=I=-15:TP=-1.5:LRA=9[a]",
    "-map", "[a]", "-t", f"{FIM}", "-ar", "48000", f"{V}/voz.wav")

# 2. legenda: blocos de até 3 palavras, com a palavra falada em destaque
AMARELO, OURO = "&H4DE1FF&", "&H7FD4FF&"
ev = []
def blocos(ws):
    out, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) == 3 or re.search(r"[.,:;!?]$", w[2]):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out
def limpa(z): return re.sub(r"[.,:;]+$", "", z).upper()
for i, ws in enumerate(palavras):
    if i == 4:  # referência do versículo
        ev.append(f"Dialogue: 0,{t(ws[0][0])},{t(ws[-1][1] + 0.35)},V,,0,0,0,,{{\\pos(540,1150)\\fad(120,120)}}ISAÍAS 41:10"); continue
    bs = blocos(ws)
    for bi, b in enumerate(bs):
        fim_bloco = bs[bi + 1][0][0] if bi + 1 < len(bs) else b[-1][1] + 0.25
        for k, (a, _, _) in enumerate(b):
            fim = b[k + 1][0] if k + 1 < len(b) else fim_bloco
            cor = OURO if (i == 6 and bi == len(bs) - 1) else AMARELO
            txt = " ".join(("{\\c" + cor + "}" + limpa(z) + "{\\c&HFFFFFF&}") if j == k else limpa(z) for j, (_, _, z) in enumerate(b))
            pop = "\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)" if k == 0 else ""
            ev.append(f"Dialogue: 0,{t(a)},{t(fim)},L,,0,0,0,,{{\\pos(540,1150){pop}}}{txt}")
ev.append(f"Dialogue: 1,{t(0)},{t(ini[0][1] + 0.3)},G,,0,0,0,,{{\\pos(540,360)\\fad(0,150)}}PRA VOCÊ QUE ESTÁ CANSADO")
cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: L,Inter Display Black,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,1,0,0,0,100,100,0,0,1,7,4,5,70,70,0,1
Style: V,DejaVu Serif,104,&H007FD4FF,&H007FD4FF,&H00000000,&HA0000000,1,0,0,0,100,100,2,0,1,6,4,5,70,70,0,1
Style: G,Inter Display Black,58,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,1,0,0,0,100,100,0,0,3,18,0,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(V + "/legenda.ass", "w", encoding="utf-8").write(cab + "\n".join(ev) + "\n")

# 3. planos: cada um vira um arquivo com a duração exata
S = [a for a, _ in ini] + [FIM]
def meio(i, palavra=None):
    if palavra:
        for a, _, z in palavras[i]:
            if z.lower().startswith(palavra): return a - 0.05
    return (ini[i][0] + ini[i][1]) / 2
planos = [
    ("vid", B + "/broll/1116.mp4", (1215, 2160, 1658, 0), None, 0.0, S[1]),
    ("img", B + "/piloto/img/1.jpg", (1383, 2459, 268, 0), "in", S[1], meio(1, "que")),
    ("img", B + "/piloto/img/1.jpg", (830, 1476, 545, 362), "in", meio(1, "que"), S[2]),
    ("img", B + "/piloto/img/2.jpg", (1294, 2301, 447, 0), "in", S[2], meio(2, "cada")),
    ("img", B + "/piloto/img/2.jpg", (780, 1387, 660, 366), "out", meio(2, "cada"), S[3]),
    ("img", B + "/piloto/img/3.jpg", (1342, 2386, 366, 0), "in", S[3], meio(3, "não")),
    ("img", B + "/piloto/img/3.jpg", (800, 1422, 637, 769), "in", meio(3, "não"), S[5]),
    ("img", B + "/piloto/img/4.jpg", (727, 1292, 322, 0), "out", S[5], S[6]),
    ("vid", B + "/broll/4397.mp4", (608, 1080, 502, 0), None, S[6], FIM),
]
lista = []
for n, (tipo, arq, (w, h, x, y), zoom, a, b) in enumerate(planos):
    d = b - a; q = int(round(d * FPS)); sai = f"{V}/plano{n}.mp4"
    if tipo == "img":
        z = f"1+0.09*on/{q}" if zoom == "in" else f"1.09-0.09*on/{q}"
        vf = (f"crop={w}:{h}:{x}:{y},scale=2160:3840:flags=lanczos,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={q}:s={W}x{H}:fps={FPS},setsar=1")
        run("-loop", "1", "-i", arq, "-vf", vf, "-frames:v", str(q), "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", sai)
    else:
        vf = f"crop={w}:{h}:{x}:{y},scale={W}:{H}:flags=lanczos,fps={FPS},setsar=1"
        run("-ss", "0.5", "-i", arq, "-vf", vf, "-frames:v", str(q), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", sai)
    lista.append(f"file '{sai}'")
open(V + "/planos.txt", "w").write("\n".join(lista) + "\n")

# 4. passe final: cor, legenda, voz e trilha com a música baixando quando há fala
fc = (f"[0:v]eq=brightness=-0.03:contrast=1.06:saturation=1.0,vignette=PI/6,ass={V}/legenda.ass,"
      f"fade=t=in:st=0:d=0.25,fade=t=out:st={FIM-0.7:.2f}:d=0.7[v];"
      f"[1:a]asplit=2[voz][chave];"
      f"[2:a]aresample=48000,volume=3.2,afade=t=in:st=0:d=1.0,afade=t=out:st={FIM-2.0:.2f}:d=2.0[m];"
      f"[m][chave]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=450[md];"
      f"[voz][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]")
run("-f", "concat", "-safe", "0", "-i", V + "/planos.txt", "-i", V + "/voz.wav", "-ss", str(MUSICA_DE), "-i", MUSICA,
    "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{FIM:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", V + "/piloto-v2.mp4")
print("duração", round(FIM, 2), "| frases", [(round(a, 2), round(b, 2)) for a, b in ini])
