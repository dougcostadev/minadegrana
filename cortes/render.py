"""Monta o vídeo vertical 1080x1920: facecam em cima, gameplay embaixo."""
import os
import subprocess

L, A = 1080, 1920
A_CAM = 608  # 1080x608 = 16:9
Y_TAMPA = 720  # onde a cam fica quando desce para tampar o jogo: logo abaixo do gancho


def _esc(caminho):
    return caminho.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


TETO_MB = 19  # a pauta online aceita vídeos de até 20 MiB


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


# A conversão para 30 fps vem antes de tudo: feita só na saída, com fonte a 60 fps, o tempo dos
# filtros não bate com o do vídeo pronto e o que é ligado por trecho entra uns 2 quadros atrasado.
_FPS = "fps=30"


def _quando(trechos):
    """Expressão `enable` do ffmpeg para uma lista de (inicio, fim) em segundos."""
    return "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in trechos)


def _sem_foco(w, h):
    """Filtros que tiram um painel w x h de foco a ponto de não dar para reconhecer nada nele."""
    return f"scale={w // 16}:{h // 16},gblur=sigma=6,scale={w}:{h}"


def _tarjas(tarjas):
    """Tarjas pretas no painel do jogo: [(inicio, fim, x, y, w, h)], com x, y, w, h em frações do painel."""
    return "".join(f",drawbox=x=iw*{x:.3f}:y=ih*{y:.3f}:w=iw*{w:.3f}:h=ih*{h:.3f}:color=black:t=fill"
                   f":enable='{_quando([(a, b)])}'" for a, b, x, y, w, h in tarjas or [])


def carimbar(origem, destino, ass):
    """Queima um .ass (marca e chamada) num vídeo vertical já pronto, respeitando o teto de tamanho."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", origem, "-vf", f"ass='{_esc(ass)}'",
                    "-c:v", "libx264", "-preset", "veryfast", *_taxa(_duracao(origem)), "-pix_fmt", "yuv420p",
                    "-c:a", "copy", "-movflags", "+faststart", destino], check=True)
    return destino


def renderizar(origem, destino, inicio=None, fim=None, cam=None, legenda_ass=None, censura=None,
               tarjas=None, censura_cam=None):
    """Renderiza um corte. `cam` = (x, y, w, h) da webcam no vídeo original, ou None.

    censura: [(inicio, fim)] — nesses trechos o quadro inteiro vira o jogo fora de foco e a cam,
    se houver, desce para cima dele, na largura toda: é o streamer que tampa a cena, sem pixel
    nem selo de censura.
    censura_cam: pedaços desses trechos em que a cam não aparece (fica só o jogo fora de foco).
    O recorte da cam é fixo: se a webcam sair do lugar, ou a caixa pegar mais que a webcam,
    aparece jogo nítido ali. None = a cam não aparece em nenhum trecho de `censura`; [] = aparece
    em todos.
    tarjas: retângulos pretos no painel do jogo (ver `_tarjas`).
    """
    if censura_cam is None:
        censura_cam = censura
    grafo = [f"[0:v]{_FPS},split={3 if censura else 2}[a][b]" + ("[c]" if censura else "")]
    if cam:
        x, y, w, h = cam
        a_jogo = A - A_CAM
        grafo += [f"[a]crop={w}:{h}:{x}:{y},scale={L}:{A_CAM}:force_original_aspect_ratio=increase,"
                  f"crop={L}:{A_CAM}" + (",split=2[cam][tampa]" if censura else "[cam]"),
                  f"[b]crop=trunc(ih*{L}/{a_jogo}/2)*2:ih,scale={L}:{a_jogo}{_tarjas(tarjas)}[jogo]",
                  "[cam][jogo]vstack=inputs=2[v0]"]
    else:
        # sem cam: gameplay 4:5 no centro sobre o próprio vídeo desfocado
        grafo += [f"[a]scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},boxblur=24:2[fundo]",
                  f"[b]crop=trunc(ih*4/5/2)*2:ih,scale={L}:1350{_tarjas(tarjas)}[jogo]",
                  "[fundo][jogo]overlay=0:(H-h)/2[v0]"]
    if censura:
        grafo.append(f"[c]scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},{_sem_foco(L, A)}[foco]")
        if cam:
            aparece = f":enable='not({_quando(censura_cam)})'" if censura_cam else ""
            grafo.append(f"[foco][tampa]overlay=0:{Y_TAMPA}{aparece}[foco2]")
        grafo.append(f"[v0][{'foco2' if cam else 'foco'}]overlay=enable='{_quando(censura)}'[v1]")
    grafo.append(f"[{'v1' if censura else 'v0'}]" + (f"ass='{_esc(legenda_ass)}'" if legenda_ass else "null") + "[v]")
    filtro = ";".join(grafo)

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
