"""Monta o vídeo vertical 1080x1920: facecam em cima, gameplay embaixo."""
import os
import subprocess

L, A = 1080, 1920
A_CAM = 608  # 1080x608 = 16:9


def _esc(caminho):
    return caminho.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


TETO_MB = 19  # a pauta online aceita vídeos de até 20 MiB

# Marca d'água do canal: o selo redondo com a logo e o nome em volta (gerado por cortes/marca.py).
SELO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "marca", "selo.png")
SELO_COM_CAM = (34, 176, 176)   # x, y, lado: canto de cima da câmera, abaixo da barra dos aplicativos
SELO_SEM_CAM = (34, 318, 160)   # sem câmera o gancho ocupa o topo, então o selo desce para o jogo


def _selo(entrada, saida, com_cam=True):
    """Trecho de filtro que sobrepõe o selo em `entrada`; sem o arquivo do selo, só repassa o vídeo."""
    if not os.path.exists(SELO):
        return f"[{entrada}]null[{saida}]"
    x, y, lado = SELO_COM_CAM if com_cam else SELO_SEM_CAM
    return (f"movie='{_esc(SELO)}',scale={lado}:{lado}:flags=lanczos,format=rgba,colorchannelmixer=aa=0.92[selo];"
            f"[{entrada}][selo]overlay={x}:{y}[{saida}]")


def _duracao(arquivo):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "csv=p=0", arquivo], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _taxa(segundos):
    """Args de bitrate que mantêm o arquivo abaixo de TETO_MB (qualidade constante até esse teto)."""
    kbps = max(900, min(7000, int(TETO_MB * 8192 / max(segundos, 5)) - 180))
    return ["-crf", "20", "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k"]


def compactar(arquivo):
    """Reencoda o vídeo só se ele passar do teto. Retorna True se mexeu."""
    if os.path.getsize(arquivo) <= TETO_MB * 1024 * 1024:
        return False
    tmp = arquivo + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", arquivo, "-c:v", "libx264", "-preset", "veryfast",
                    *_taxa(_duracao(arquivo)), "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, arquivo)
    return True


def _quando(trechos):
    """Expressão `enable` do ffmpeg para uma lista de (inicio, fim) em segundos."""
    return "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in trechos)


def _censura(censura, tarjas):
    """Filtros aplicados só ao painel do jogo: pixelização total e/ou tarjas pretas por trecho.

    censura: [(inicio, fim)] — pixeliza o painel inteiro nesses trechos.
    tarjas:  [(inicio, fim, x, y, w, h)] — retângulo preto; x, y, w, h são frações do painel (0 a 1).
    """
    filtros = ""
    if censura:
        filtros += f",pixelize=w=54:h=54:enable='{_quando(censura)}'"
    for a, b, x, y, w, h in tarjas or []:
        filtros += (f",drawbox=x=iw*{x:.3f}:y=ih*{y:.3f}:w=iw*{w:.3f}:h=ih*{h:.3f}:color=black:t=fill"
                    f":enable='{_quando([(a, b)])}'")
    return filtros


def carimbar(origem, destino, ass=None, com_cam=True):
    """Põe o selo (e queima um .ass, se houver) num vídeo vertical já pronto, respeitando o teto de tamanho."""
    filtro = (f"[0:v]ass='{_esc(ass)}'[v0];" if ass else "[0:v]null[v0];") + _selo("v0", "v", com_cam)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", origem, "-filter_complex", filtro, "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-preset", "veryfast", *_taxa(_duracao(origem)), "-pix_fmt", "yuv420p",
                    "-c:a", "copy", "-movflags", "+faststart", destino], check=True)
    return destino


def renderizar(origem, destino, inicio=None, fim=None, cam=None, legenda_ass=None, censura=None,
               tarjas=None, moldura=None):
    """Renderiza um corte. `cam` = (x, y, w, h) da webcam no vídeo original, ou None."""
    if cam:
        x, y, w, h = cam
        a_jogo = A - A_CAM
        filtro = (
            f"[0:v]split=2[a][b];"
            f"[a]crop={w}:{h}:{x}:{y},scale={L}:{A_CAM}:force_original_aspect_ratio=increase,"
            f"crop={L}:{A_CAM}[cam];"
            f"[b]crop=trunc(ih*{L}/{a_jogo}/2)*2:ih,scale={L}:{a_jogo}{_censura(censura, tarjas)}[jogo];"
            f"[cam][jogo]vstack=inputs=2[v0]"
        )
    else:
        # sem cam: gameplay 4:5 no centro sobre o próprio vídeo desfocado
        filtro = (
            f"[0:v]split=2[a][b];"
            f"[a]scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},boxblur=24:2[fundo];"
            f"[b]crop=trunc(ih*4/5/2)*2:ih,scale={L}:1350{_censura(censura, tarjas)}[jogo];"
            f"[fundo][jogo]overlay=0:(H-h)/2[v0]"
        )
    if legenda_ass:
        filtro += f";[v0]ass='{_esc(legenda_ass)}'[v1]"
    else:
        filtro += ";[v0]null[v1]"
    if moldura:  # PNG do tamanho do vídeo com gancho, etiqueta do streamer e selo (cortes/ui.py)
        filtro += f";movie='{_esc(moldura)}',format=rgba[ui];[v1][ui]overlay=0:0[v]"
    elif moldura is None:
        filtro += ";" + _selo("v1", "v", com_cam=bool(cam))
    else:  # moldura=False: vídeo limpo, para quem vai editar por cima e pôr a moldura no fim
        filtro += ";[v1]null[v]"

    segundos = (fim - inicio) if (inicio is not None and fim is not None) else _duracao(origem)
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if inicio is not None:
        cmd += ["-ss", str(inicio)]
    if fim is not None:
        cmd += ["-to", str(fim)]
    cmd += ["-i", origem, "-filter_complex", filtro, "-map", "[v]", "-map", "0:a?",
            "-r", "30", "-c:v", "libx264", "-preset", "veryfast", *_taxa(segundos),
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-movflags", "+faststart", destino]
    subprocess.run(cmd, check=True)
    return destino
