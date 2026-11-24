"""Exemplo do formato narrado para o Leonida Clipes: abertura com narrador, pausa no ponto de virada,
replay em câmera lenta e pergunta final."""
import subprocess
SRC = "/home/user/minadegrana/saida/hayashii-3096445093.mp4"
def run(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
def dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)
ENC = ["-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
NARR = "aresample=48000,loudnorm=I=-14:TP=-1.5:LRA=9"
n = {i: dur(f"n{i}.wav") for i in (1, 2, 3, 4)}
segs = []
def trecho(nome, a, b, narr=None, atraso=0.15, vol=1.0):
    d = b - a
    if narr:
        fc = (f"[0:a]volume={vol},aresample=48000[c];[1:a]{NARR},adelay={int(atraso*1000)}:all=1,apad=whole_dur={d}[n];"
              f"[c][n]amix=inputs=2:normalize=0:duration=first[a]")
        run("-ss", str(a), "-t", str(d), "-i", SRC, "-i", f"n{narr}.wav", "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-t", str(d), *ENC, nome)
    else:
        run("-ss", str(a), "-t", str(d), "-i", SRC, "-af", "aresample=48000", "-t", str(d), *ENC, nome)
    segs.append((nome, d))
def pausa(nome, t, d, narr, atraso=0.1):
    run("-ss", str(t), "-i", SRC, "-frames:v", "1", "q.png")
    q = int(round(d * 30))
    vf = (f"[0:v]scale=2160:3840:flags=lanczos,zoompan=z='1+0.05*on/{q}':x='iw/2-(iw/zoom/2)':y='ih*0.62-(ih/zoom*0.62)':d={q}:s=1080x1920:fps=30,setsar=1[v];"
          f"[1:a]{NARR},adelay={int(atraso*1000)}:all=1,apad=whole_dur={d}[a]")
    run("-loop", "1", "-i", "q.png", "-i", f"n{narr}.wav", "-filter_complex", vf, "-map", "[v]", "-map", "[a]", "-t", str(d), *ENC, nome)
    segs.append((nome, d))
def replay(nome, a, b, narr, atraso=0.3):
    d = (b - a) * 2
    fc = f"[0:v]setpts=2*PTS,fps=30[v];[1:a]{NARR},adelay={int(atraso*1000)}:all=1,apad=whole_dur={d}[a]"
    run("-ss", str(a), "-t", str(b - a), "-i", SRC, "-i", f"n{narr}.wav", "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", str(d), *ENC, nome)
    segs.append((nome, d))

trecho("s1.mp4", 0.5, 0.5 + n[1] + 0.4, narr=1, vol=0.15)
trecho("s2.mp4", 8.0, 15.8)
pausa("s3.mp4", 15.8, n[2] + 0.4, narr=2)
trecho("s4.mp4", 15.8, 27.0)
replay("s5.mp4", 20.5, 22.5, narr=3)
pausa("s6.mp4", 21.6, n[4] + 1.5, narr=4, atraso=0.2)

ini, t = {}, 0.0
for nome, d in segs: ini[nome] = t; t += d
TOTAL = t
def T(s): return f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"
ev = [f"Dialogue: 3,{T(0)},{T(TOTAL)},M,,0,0,0,,LEONIDA CLIPES",
      f"Dialogue: 2,{T(ini['s1.mp4']+0.1)},{T(ini['s1.mp4']+n[1]+0.35)},N,,0,0,0,,ELE SÓ PAROU PRA AJUDAR\\NA DESATOLAR A VAN",
      f"Dialogue: 2,{T(ini['s3.mp4']+0.05)},{T(ini['s3.mp4']+n[2]+0.35)},N,,0,0,0,,SÓ QUE ELE APERTOU\\NO BOTÃO ERRADO",
      f"Dialogue: 2,{T(ini['s5.mp4'])},{T(ini['s5.mp4']+4.0)},R,,0,0,0,,REPLAY",
      f"Dialogue: 2,{T(ini['s5.mp4']+0.25)},{T(ini['s5.mp4']+n[3]+0.5)},N,,0,0,0,,TINHA UM TIGRE\\NDENTRO DA VAN",
      f"Dialogue: 2,{T(ini['s6.mp4']+0.15)},{T(ini['s6.mp4']+n[4]+0.3)},N,,0,0,0,,VOCÊ TERIA PARADO\\NPRA AJUDAR?",
      f"Dialogue: 4,{T(TOTAL-1.45)},{T(TOTAL)},S,,0,0,0,,{{\\fad(200,0)}}SEGUE PRA MAIS\\NGTA 6 TODO DIA"]
cab = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: M,DejaVu Sans,36,&H30FFFFFF,&H50000000,&H80000000,&H00000000,1,0,0,0,100,100,0,0,1,3,1,7,40,40,214,1
Style: N,Inter Display Black,64,&H00000000,&H00000000,&H004DE1FF,&H004DE1FF,1,0,0,0,100,100,0,0,3,16,0,8,80,80,1430,1
Style: R,Inter Display Black,54,&H00FFFFFF,&H00FFFFFF,&H002020E0,&H002020E0,1,0,0,0,100,100,2,0,3,12,0,9,60,60,700,1
Style: S,DejaVu Sans,66,&H00FFFFFF,&H00631EC8,&H00631EC8,&H00000000,1,0,0,0,100,100,0,0,3,20,0,8,90,90,1150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open("narrado.ass", "w", encoding="utf-8").write(cab + "\n".join(ev) + "\n")
open("lista.txt", "w").write("".join(f"file '{nome}'\n" for nome, _ in segs))
run("-f", "concat", "-safe", "0", "-i", "lista.txt", "-vf", "ass=narrado.ass", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
    "-maxrate", "4200k", "-bufsize", "8400k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "narrado.mp4")
print("total", round(TOTAL, 2), {k: round(v, 2) for k, v in ini.items()})
