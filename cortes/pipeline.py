"""Orquestra: baixar -> achar momentos -> detectar cam -> renderizar -> metadados."""
import json
import os
import re
import subprocess

from . import facecam, legendas, momentos, render, yt

GANCHOS = [
    "ELE NÃO ACREDITOU NO QUE ACONTECEU NO GTA 6",
    "O MOMENTO MAIS INSANO DO GTA 6 ATÉ AGORA",
    "ISSO SÓ ACONTECE NO GTA 6",
    "A REAÇÃO DELE NO GTA 6 FOI IMPAGÁVEL",
    "GTA 6 PASSOU DOS LIMITES AQUI",
]
TAGS = "#gta6 #gtavi #gta #gameplay #cortes #shorts"


def _slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", (texto or "video").lower()).strip("-")[:40]


def _hms(s):
    return f"{int(s) // 3600}:{int(s) % 3600 // 60:02d}:{int(s) % 60:02d}"


def _proibidos(caminho="nao_cortar.txt"):
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding="utf-8") as f:
        return [l.strip().lower() for l in f if l.strip() and not l.startswith("#")]


def baixar_audio(url, pasta):
    """Baixa só o áudio (leve) e devolve (caminho, info) — info traz o heatmap 'mais repetidos'."""
    import yt_dlp
    opts = yt.opcoes(format="ba/b", outtmpl=os.path.join(pasta, "%(id)s.audio.%(ext)s"))
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), info


def baixar_trecho(url, pasta, inicio, fim, altura=1080):
    """Baixa só o trecho do corte, em vez do VOD inteiro."""
    import yt_dlp
    from yt_dlp.utils import download_range_func
    opts = {
        **yt.opcoes(),
        "format": f"bv*[height<={altura}]+ba/b[height<={altura}]/b",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(pasta, f"%(id)s.{int(inicio)}.%(ext)s"),
        "download_ranges": download_range_func(None, [(inicio, fim)]),
        "force_keyframes_at_cuts": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base = os.path.splitext(ydl.prepare_filename(info))[0]
        return base + ".mp4"


def processar(fonte, saida="saida", trabalho="trabalho", quantos=5, duracao=35,
              cam=None, sem_cam=False, legendar=False, ignorar_inicio=0):
    """`fonte` é uma URL do YouTube ou um arquivo local. Retorna a lista de cortes gerados."""
    os.makedirs(saida, exist_ok=True)
    os.makedirs(trabalho, exist_ok=True)
    local = os.path.exists(fonte)
    if local:
        audio, info = fonte, {"id": _slug(os.path.splitext(os.path.basename(fonte))[0])}
    else:
        audio, info = baixar_audio(fonte, trabalho)
        canal = (info.get("channel") or info.get("uploader") or "").lower()
        if any(b in canal for b in _proibidos()):
            raise SystemExit(f"'{info.get('channel')}' está em nao_cortar.txt (proíbe cortes) — pulando.")

    nota = momentos.pontuar(momentos.volume_por_segundo(audio), info.get("heatmap"))
    cortes = momentos.escolher(nota, quantos, duracao, ignorar_inicio=ignorar_inicio)
    gerados = []
    for n, (ini, fim, pontos) in enumerate(cortes, 1):
        if local:
            trecho, ss, to = fonte, ini, fim
        else:
            trecho, ss, to = baixar_trecho(fonte, trabalho, ini, fim), None, None

        caixa = None if sem_cam else (cam or facecam.detectar(trecho))
        nome = f"{_slug(info.get('channel'))}-{info['id']}-{n:02d}"
        destino = os.path.join(saida, nome + ".mp4")

        ass = None
        if legendar:
            # legenda é sincronizada com o trecho já recortado, então renderiza em duas etapas
            bruto = os.path.join(trabalho, nome + ".bruto.mp4")
            render.renderizar(trecho, bruto, ss, to, caixa)
            ass = os.path.join(trabalho, nome + ".ass")
            y = render.A_CAM + 40 if caixa else 1500
            if legendas.gerar_ass(bruto, ass, y):
                _queimar(bruto, destino, ass)
            else:
                os.replace(bruto, destino)
        else:
            render.renderizar(trecho, destino, ss, to, caixa)

        meta = {
            "arquivo": destino,
            "titulo": f"{GANCHOS[(n - 1) % len(GANCHOS)]} 😱 #gta6 #shorts",
            "descricao": (
                f"Corte de {info.get('channel') or 'canal original'}\n"
                f"Vídeo original: {info.get('webpage_url', fonte)}"
                + (f"&t={int(ini)}s" if not local else "") + f" ({_hms(ini)})\n\n{TAGS}"
            ),
            "canal_original": info.get("channel"),
            "inicio_s": ini, "fim_s": fim, "nota": round(pontos, 2),
            "facecam": caixa,
        }
        with open(os.path.join(saida, nome + ".json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        gerados.append(meta)
    return gerados


def _queimar(origem, destino, ass):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", origem, "-vf", f"ass='{render._esc(ass)}'",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy",
                    "-movflags", "+faststart", destino], check=True)
