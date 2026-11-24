"""Monta um vídeo vertical do canal de fé a partir de um roteiro JSON.

Uso: python montar.py roteiro.json pasta_de_trabalho
A pasta precisa ter fala/1.wav, fala/2.wav... (uma narração por frase, geradas com ../piloto/gerar.py).

Roteiro:
  gancho   texto grande que aparece no quadro 0 (\\N quebra linha, *palavra* sai em amarelo)
  frases   lista; cada frase tem texto, img, foco [x, y] de 0 a 1, aperto (zoom do recorte, 1 = altura toda),
           zoom "in"/"out", pausa (segundos depois da fala), entrada "soco" (zoom de impacto + tremida +
           flash + estrondo), estilo "impacto" (cada palavra sozinha, gigante), "versiculo" (serifa dourada,
           usa o campo "tela") ou "cta", e corte {palavra, img, foco, aperto, zoom, entrada} para trocar de
           plano no meio da frase.
  musica   opcional {arquivo, de, volume}. Por padrão sai sem trilha: o som em alta do TikTok entra na postagem.
"""
import json, os, re, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)
from cortes import legendas

rot = json.load(open(sys.argv[1], encoding="utf-8")); V = os.path.abspath(sys.argv[2])
IMG = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), rot.get("pasta_img", "img"))
SFX = os.path.join(AQUI, "sfx")
W, H, FPS = 1080, 1920, 30
frases = rot["frases"]; CAUDA, PAUSA = 1.6, 0.3
FONTES = os.path.join(RAIZ, "marca", "fontes")

def run(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
def dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                        capture_output=True, text=True).stdout)
def t(s): s = max(s, 0); return f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"
def tam(p): return [int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                    "stream=width,height", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.split(",")[:2]]

# 1. voz: apara o silêncio de cada frase e cola com pausas curtas; a primeira palavra sai no quadro 0
corte = ("silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.02,areverse,"
         "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.05,areverse")
ini, pos, palavras = [], 0.0, []
for i, f in enumerate(frases):
    a = f"{V}/fala/{i+1}.wav"; b = f"{V}/fala/{i+1}-a.wav"
    run("-i", a, "-af", corte, "-ar", "48000", "-ac", "1", b)
    d = dur(b); ini.append((pos, pos + d))
    ws = [(float(x), float(y), str(z).strip()) for x, y, z in (legendas.transcrever(b, idioma="pt") or [])]
    alvo = f["texto"].split()
    if len(ws) == len(alvo):  # tempo do whisper, grafia do roteiro
        ws = [(x, y, z) for (x, y, _), z in zip(ws, alvo)]
    else:  # tempos proporcionais ao tamanho das palavras
        if f.get("estilo") != "versiculo":
            print("aviso: transcrição difere na frase", i + 1, [w[2] for w in ws])
        tot = sum(len(z) for z in alvo); c = 0.0; novo = []
        for z in alvo:
            novo.append((d * c / tot, d * (c + len(z)) / tot, z)); c += len(z)
        ws = novo
    palavras.append([(pos + x, pos + y, z) for x, y, z in ws])
    pos += d + f.get("pausa", PAUSA)
FIM = pos - frases[-1].get("pausa", PAUSA) + CAUDA

# 2. planos: recorte 9:16 em volta do foco, zoom lento; "soco" = entra com zoom forte, tremida e flash
S = [a for a, _ in ini]; S[0] = 0.0; S.append(FIM)
planos = []  # (img, foco, aperto, zoom, entrada, inicio, fim)
for i, f in enumerate(frases):
    a, b = S[i], S[i + 1]
    p = (f["img"], f["foco"], f.get("aperto", 1.0), f.get("zoom", "in"), f.get("entrada") or ("soco" if i == 0 else None))
    if f.get("corte"):
        c = f["corte"]
        m = next((x - 0.05 for x, _, z in palavras[i] if z.lower().strip(".,:;!?…").startswith(c["palavra"])), (a + b) / 2)
        planos += [(*p, a, m), (c.get("img", f["img"]), c["foco"], c.get("aperto", 1.6), c.get("zoom", "in"),
                                c.get("entrada"), m, b)]
    else:
        planos.append((*p, a, b))
lista, efeitos, flashes = [], [], []
for n, (img, (fx, fy), aperto, zoom, entrada, a, b) in enumerate(planos):
    arq = os.path.join(IMG, img); iw, ih = tam(arq)
    h = min(ih, iw * 16 / 9) / aperto; w = h * 9 / 16
    x = min(max(fx * iw - w / 2, 0), iw - w); y = min(max(fy * ih - h / 2, 0), ih - h)
    q = int(round((b - a) * FPS)); sai = f"{V}/plano{n}.mp4"
    z = f"1+0.10*on/{q}" if zoom == "in" else f"1.10-0.10*on/{q}"
    dx = dy = "0"
    if entrada == "soco":
        z += "+0.32*max(0,1-on/7)"
        dx = "if(lt(on,10),44*sin(on*2.9)*(1-on/10),0)"; dy = "if(lt(on,10),30*cos(on*3.7)*(1-on/10),0)"
        efeitos.append((a, "boom.wav", 1.0 if n == 0 else 0.75))
        if n > 0: flashes.append(a)  # sem flash no quadro 0: ele é a capa no feed
    elif n > 0:
        efeitos.append((a - 0.32, "whoosh.wav", 0.9))
    vf = (f"crop={int(w)}:{int(h)}:{int(x)}:{int(y)},scale=2160:3840:flags=lanczos,"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)+{dx}':y='ih/2-(ih/zoom/2)+{dy}':d={q}:s={W}x{H}:fps={FPS},setsar=1")
    run("-loop", "1", "-i", arq, "-vf", vf, "-frames:v", str(q), "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p", sai)
    lista.append(f"file '{sai}'")
open(V + "/planos.txt", "w").write("\n".join(lista) + "\n")
for f, ws in zip(frases, palavras):
    if f.get("estilo") == "versiculo":
        efeitos.append((ws[0][0] - 0.1, "brilho.wav", 1.0))

# 3. legenda
AMARELO, OURO = "&H00E5FF&", "&H7FD4FF&"
def limpa(z): return re.sub(r"[.,:;!?…]+$", "", z).upper()
def blocos(ws):
    out, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) == 3 or re.search(r"[.,:;!?…]$", w[2]):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out
ev = []
for i, (f, ws) in enumerate(zip(frases, palavras)):
    est = f.get("estilo")
    if est == "versiculo":
        txt = f.get("tela", f["texto"]).replace("\n", "\\N")
        ev.append(f"Dialogue: 0,{t(ws[0][0])},{t(S[i + 1])},V,,0,0,0,,"
                  f"{{\\pos(540,1060)\\fad(250,150)\\fscx92\\fscy92\\t(0,600,\\fscx100\\fscy100)}}{txt}")
        continue
    if est == "impacto":  # uma palavra por vez, gigante; a última em amarelo
        for k, (a, _, z) in enumerate(ws):
            fim = ws[k + 1][0] if k + 1 < len(ws) else min(ws[-1][1] + 0.5, S[i + 1])
            cor = "{\\c" + AMARELO + "}" if k == len(ws) - 1 else ""
            ev.append(f"Dialogue: 0,{t(a)},{t(fim)},I,,0,0,0,,"
                      f"{{\\pos(540,1000)\\fscx150\\fscy150\\t(0,110,\\fscx100\\fscy100)}}{cor}{limpa(z)}")
        continue
    bs = blocos(ws)
    for bi, b in enumerate(bs):
        fim_bloco = bs[bi + 1][0][0] if bi + 1 < len(bs) else min(b[-1][1] + 0.3, S[i + 1])
        for k, (a, _, _) in enumerate(b):
            fim = b[k + 1][0] if k + 1 < len(b) else fim_bloco
            cor = OURO if est == "cta" else AMARELO
            txt = " ".join(("{\\c" + cor + "\\fscx110\\fscy110\\t(0,100,\\fscx100\\fscy100)}" + limpa(z) +
                            "{\\c&HFFFFFF&\\fscx100\\fscy100}") if j == k else limpa(z) for j, (_, _, z) in enumerate(b))
            ev.append(f"Dialogue: 0,{t(a)},{t(fim)},L,,0,0,0,,{{\\pos(540,1200)}}{txt}")
gancho = re.sub(r"\*([^*]+)\*", lambda m: "{\\c" + AMARELO + "}" + m.group(1) + "{\\c&HFFFFFF&}", rot["gancho"])
fim_gancho = max(ini[0][1] + 0.4, 2.6)
ev.append(f"Dialogue: 1,{t(0)},{t(fim_gancho)},G,,0,0,0,,"
          f"{{\\pos(540,560)\\fscx130\\fscy130\\t(0,140,\\fscx100\\fscy100)\\fad(0,180)}}{gancho}")
cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: L,Poppins ExtraBold,100,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,0,0,0,0,100,100,0,0,1,8,4,5,60,60,0,1
Style: I,Anton,210,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,2,0,1,10,6,5,40,40,0,1
Style: V,DejaVu Serif,80,&H007FD4FF,&H007FD4FF,&H00000000,&HA0000000,1,0,0,0,100,100,2,0,1,6,4,5,80,80,0,1
Style: G,Anton,150,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,1,0,1,9,5,5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(V + "/legenda.ass", "w", encoding="utf-8").write(cab + "\n".join(ev) + "\n")

# 4. passe final: cor dramática, grão, flash nos socos, legenda; áudio = voz + efeitos (+ trilha opcional)
escuro = "".join(f",eq=brightness=-0.16:enable='between(t,{ws[0][0]-0.1:.3f},{S[i+1]:.3f})'"
                 for i, (f, ws) in enumerate(zip(frases, palavras)) if f.get("estilo") == "versiculo")
flash = escuro + "".join(f",eq=brightness=0.45:enable='between(t,{a:.3f},{a + 0.07:.3f})'" for a in flashes)
vf = (f"[0:v]eq=brightness=-0.03:contrast=1.13:saturation=0.92,colorbalance=rm=0.04:bm=-0.03,vignette=PI/4.5"
      f"{flash},noise=alls=7:allf=t+u,ass={V}/legenda.ass:fontsdir={FONTES},fade=t=out:st={FIM-0.6:.2f}:d=0.6[v]")
ent = ["-f", "concat", "-safe", "0", "-i", V + "/planos.txt", "-i", V + "/voz.wav"]
run(*sum((["-i", f"{V}/fala/{i+1}-a.wav"] for i in range(len(frases))), []), "-filter_complex",
    "".join(f"[{i}:a]adelay={int(a*1000)}:all=1[s{i}];" for i, (a, _) in enumerate(ini)) +
    "".join(f"[s{i}]" for i in range(len(frases))) +
    f"amix=inputs={len(frases)}:normalize=0,apad=whole_dur={FIM},loudnorm=I=-14:TP=-1.5:LRA=9[a]",
    "-map", "[a]", "-t", f"{FIM}", "-ar", "48000", f"{V}/voz.wav")
fa, k = "", 2
for n, (a, arq, vol) in enumerate(efeitos):
    ent += ["-i", os.path.join(SFX, arq)]
    fa += f"[{k}:a]aresample=48000,volume={vol},adelay={int(max(a, 0)*1000)}:all=1[e{n}];"; k += 1
mix = "[1:a]" + "".join(f"[e{n}]" for n in range(len(efeitos)))
if rot.get("musica"):
    musica = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), rot["musica"]["arquivo"])
    ent += ["-ss", str(rot["musica"].get("de", 0)), "-i", musica]
    fa += (f"[{k}:a]aresample=48000,volume={rot['musica'].get('volume', 3.0)},afade=t=out:st={FIM-2.0:.2f}:d=2.0[m];")
    mix += "[m]"; n_ent = len(efeitos) + 2
else:
    n_ent = len(efeitos) + 1
fa += f"{mix}amix=inputs={n_ent}:normalize=0:duration=first,alimiter=limit=0.95[a]"
run(*ent, "-filter_complex", vf + ";" + fa, "-map", "[v]", "-map", "[a]", "-t", f"{FIM:.2f}", "-c:v", "libx264",
    "-preset", "medium", "-crf", "20", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-c:a", "aac",
    "-b:a", "192k", "-movflags", "+faststart", V + "/" + rot.get("saida", "exemplo.mp4"))
print("duração", round(FIM, 2), "| planos", len(planos), "| socos", len(flashes) + 1)
