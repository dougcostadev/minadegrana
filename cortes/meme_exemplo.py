"""Exemplo completo do formato novo do Clipes Leonida: edit de meme sobre o corte limpo, memes em
vídeo no lugar de emoji, identidade visual por cima de tudo e a capa como primeiro quadro.

Rascunho de 24/11/2026, montado em /home/user/voz. Os sons e os GIFs vêm de acervos de memes e não
têm licença, por isso não ficam no repositório."""
import subprocess
E = "/home/user/voz/exemplo"; M = "/home/user/voz/meme"; R = "/home/user/minadegrana/marca"
SRC = E + "/limpo.mp4"
def run(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
ENC = ["-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
segs = []
def trecho(nome, a, b, vf=None):
    args = ["-ss", str(a), "-t", str(b - a), "-i", SRC]
    if vf: args += ["-vf", vf]
    run(*args, "-af", "aresample=48000", "-t", str(b - a), *ENC, nome); segs.append((nome, b - a))
def pausa(nome, t, d, alvo, zoom, rapido=True, pb=False):
    run("-ss", str(t), "-i", SRC, "-frames:v", "1", E + "/q.png")
    q = int(round(d * 30)); tx, ty = alvo[0] * 2, alvo[1] * 2
    z = f"min(1+{zoom-1}*on/10,{zoom})" if rapido else f"1+{zoom-1}*on/{q}"
    cor = "hue=s=0,eq=contrast=1.15:brightness=-0.04,vignette=PI/4," if pb else ""
    vf = f"[0:v]{cor}scale=2160:3840:flags=lanczos,zoompan=z='{z}':x='{tx}*(1-1/zoom)':y='{ty}*(1-1/zoom)':d={q}:s=1080x1920:fps=30,setsar=1[v]"
    run("-loop", "1", "-i", E + "/q.png", "-f", "lavfi", "-t", str(d), "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex", vf,
        "-map", "[v]", "-map", "1:a", "-t", str(d), *ENC, nome); segs.append((nome, d))

trecho(E + "/a.mp4", 0.5, 5.0)
trecho(E + "/b.mp4", 9.0, 15.8)
pausa(E + "/c.mp4", 15.8, 1.7, alvo=(450, 1260), zoom=1.45)
trecho(E + "/d.mp4", 15.8, 18.4)
trecho(E + "/e.mp4", 18.4, 19.6, vf="crop=292:520:394:88,scale=1080:1920:flags=bicubic,eq=saturation=1.5:contrast=1.2,unsharp=7:7:1.5")
trecho(E + "/f.mp4", 19.6, 24.6)
pausa(E + "/g.mp4", 24.6, 3.2, alvo=(780, 1270), zoom=1.3, rapido=False, pb=True)

ini, t = {}, 0.0
for nome, dd in segs: ini[nome[-5]] = t; t += dd
TOTAL = t
def T(s): return f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"
pop = "\\fscx130\\fscy130\\t(0,120,\\fscx100\\fscy100)"
ev = [f"Dialogue: 1,{T(ini['b']+0.2)},{T(ini['b']+2.9)},X,,0,0,0,,{{\\pos(540,1560){pop}}}CIDADÃO DE BEM",
      f"Dialogue: 1,{T(ini['c']+0.1)},{T(ini['c']+1.7)},X,,0,0,0,,{{\\pos(540,1180){pop}\\c&H1FC2FF&\\fs150}}O BOTÃO ERRADO",
      f"Dialogue: 1,{T(ini['f']+1.4)},{T(ini['f']+3.3)},X,,0,0,0,,{{\\pos(620,1560){pop}\\c&H1FC2FF&}}\"EU APERTEI O\\NBOTÃO ERRADO\"",
      f"Dialogue: 1,{T(ini['g']+0.4)},{T(TOTAL)},X,,0,0,0,,{{\\pos(660,1500)\\fad(300,0)}}ELE SÓ QUERIA\\NAJUDAR"]
cab = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: X,Anton,112,&H00FFFFFF,&H00FFFFFF,&H002A0A1B,&H007E2EFF,0,0,0,0,100,100,1,0,1,9,6,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(E + "/meme.ass", "w", encoding="utf-8").write(cab + "\n".join(ev) + "\n")
open(E + "/lista.txt", "w").write("".join(f"file '{nome}'\n" for nome, _ in segs))

tremer = f"between(t,{ini['e']:.2f},{ini['e']+0.45:.2f})+between(t,{ini['f']+1.35:.2f},{ini['f']+1.95:.2f})"
def liga(a, b): return f"enable='between(t,{a:.2f},{b:.2f})'"
def figurinha(n, larg, a):  # GIF de meme com borda branca, começando no instante `a`
    return f"[{n}:v]scale={larg}:-2:flags=bicubic,pad=iw+16:ih+16:8:8:white,setpts=PTS-STARTPTS+{a:.2f}/TB[g{n}]"
tf, tg, th = ini['c'] + 0.45, ini['f'] + 1.3, ini['g'] + 0.4
fc = (f"[0:v]scale=1146:2038:flags=bicubic,crop=1080:1920:x='33+if({tremer},28*sin(2*PI*t*14),0)':y='59+if({tremer},38*cos(2*PI*t*11),0)'[v0];"
      + figurinha(1, 420, tf) + ";" + figurinha(2, 300, tg) + ";" + figurinha(3, 300, th) + ";"
      f"[v0][g1]overlay=600:700:{liga(tf, ini['c']+1.7)}[v1];"
      f"[v1][g2]overlay=50:1380:{liga(tg, tg+2.0)}[v2];"
      f"[v2][g3]overlay=50:1340:{liga(th, TOTAL)}[v3];"
      f"[v3]ass={E}/meme.ass:fontsdir={R}/fontes[v4];"
      f"[v4][4:v]overlay=0:0:enable='not(between(t,{ini['e']:.2f},{ini['e']+1.2:.2f}))'[v5];"
      f"[5:v]scale=1080:1920[capa];[v5][capa]overlay=0:0:enable='lt(t,0.1)'[v];"
      f"[6:a]volume=1.5,adelay={int(ini['c']*1000)}:all=1[s1];"
      f"[7:a]volume=4.0,adelay={int((ini['c']+0.55)*1000)}:all=1[s2];"
      f"[8:a]atrim=start=7.5,asetpts=PTS-STARTPTS,volume=0.55,afade=t=in:st=0:d=0.4,adelay={int(ini['d']*1000)}:all=1[s3];"
      f"[9:a]volume=1.0,adelay={int(ini['e']*1000)}:all=1[s4];"
      f"[10:a]volume=1.0,adelay={int((ini['f']+1.35)*1000)}:all=1[s5];"
      f"[11:a]atrim=end=3.2,volume=0.85,afade=t=out:st=2.4:d=0.8,adelay={int((ini['g']+0.1)*1000)}:all=1[s6];"
      f"[0:a][s1][s2][s3][s4][s5][s6]amix=inputs=7:normalize=0:duration=first,alimiter=limit=0.95[a]")
run("-f", "concat", "-safe", "0", "-i", E + "/lista.txt",
    "-stream_loop", "-1", "-i", M + "/gif/errou0.mp4", "-stream_loop", "-1", "-i", M + "/gif/susto0.mp4", "-stream_loop", "-1", "-i", M + "/gif/hamster0.mp4",
    "-i", E + "/moldura.png", "-i", E + "/capa.jpg",
    "-i", M + "/sfx/scratch.mp3", "-i", M + "/sfx/errou.mp3", "-i", M + "/sfx/suspense.mp3", "-i", M + "/sfx/boom.mp3", "-i", M + "/sfx/boom.mp3", "-i", M + "/sfx/violino.mp3",
    "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{TOTAL:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
    "-maxrate", "5M", "-bufsize", "10M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", E + "/exemplo.mp4")
print("total", round(TOTAL, 2), {k: round(v, 2) for k, v in ini.items()})
