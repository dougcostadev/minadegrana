"""Monta o vídeo vertical 1080x1920: facecam em cima, gameplay embaixo."""
import subprocess

L, A = 1080, 1920
A_CAM = 608  # 1080x608 = 16:9


def _esc(caminho):
    return caminho.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def renderizar(origem, destino, inicio=None, fim=None, cam=None, legenda_ass=None):
    """Renderiza um corte. `cam` = (x, y, w, h) da webcam no vídeo original, ou None."""
    if cam:
        x, y, w, h = cam
        a_jogo = A - A_CAM
        filtro = (
            f"[0:v]split=2[a][b];"
            f"[a]crop={w}:{h}:{x}:{y},scale={L}:{A_CAM}:force_original_aspect_ratio=increase,"
            f"crop={L}:{A_CAM}[cam];"
            f"[b]crop=trunc(ih*{L}/{a_jogo}/2)*2:ih,scale={L}:{a_jogo}[jogo];"
            f"[cam][jogo]vstack=inputs=2[v0]"
        )
    else:
        # sem cam: gameplay 4:5 no centro sobre o próprio vídeo desfocado
        filtro = (
            f"[0:v]split=2[a][b];"
            f"[a]scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},boxblur=24:2[fundo];"
            f"[b]crop=trunc(ih*4/5/2)*2:ih,scale={L}:1350[jogo];"
            f"[fundo][jogo]overlay=0:(H-h)/2[v0]"
        )
    if legenda_ass:
        filtro += f";[v0]ass='{_esc(legenda_ass)}'[v]"
    else:
        filtro += ";[v0]null[v]"

    cmd = ["ffmpeg", "-y", "-v", "error"]
    if inicio is not None:
        cmd += ["-ss", str(inicio)]
    if fim is not None:
        cmd += ["-to", str(fim)]
    cmd += ["-i", origem, "-filter_complex", filtro, "-map", "[v]", "-map", "0:a?",
            "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-movflags", "+faststart", destino]
    subprocess.run(cmd, check=True)
    return destino
