"""Orquestra: baixar -> achar momentos -> detectar cam -> renderizar -> metadados."""
import json
import os
import re
import subprocess

from . import facecam, ganchos, legendas, momentos, render, yt

GANCHOS = [
    "ELE NÃO ACREDITOU NO QUE ACONTECEU NO GTA 6",
    "O MOMENTO MAIS INSANO DO GTA 6 ATÉ AGORA",
    "ISSO SÓ ACONTECE NO GTA 6",
    "A REAÇÃO DELE NO GTA 6 FOI IMPAGÁVEL",
    "GTA 6 PASSOU DOS LIMITES AQUI",
]
GANCHOS_EN = [
    "{c} CAN'T BELIEVE WHAT JUST HAPPENED IN GTA 6",
    "{c}'S WILDEST GTA 6 MOMENT SO FAR",
    "THIS ONLY HAPPENS IN GTA 6 ({c})",
    "{c}'S REACTION TO THIS GTA 6 SCENE",
    "GTA 6 WENT TOO FAR HERE ({c})",
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


def _pegar(u):
    import urllib.request
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def baixar_hls(url, destino_sem_ext, inicio=0.0, fim=float("inf")):
    """Baixa os segmentos de uma playlist HLS que cobrem [inicio, fim].

    Retorna (arquivo, deslocamento) — o trecho pedido começa `deslocamento` segundos dentro
    do arquivo — ou None se a playlist não tiver segmentos nesse intervalo.
    """
    from urllib.parse import urljoin
    lista = _pegar(url).decode()
    if "#EXT-X-STREAM-INF" in lista:  # playlist mestre: segue para a variante de maior qualidade
        linhas = lista.splitlines()
        variantes = [(int((re.search(r"BANDWIDTH=(\d+)", l) or [0, 0])[1]), linhas[i + 1].strip())
                     for i, l in enumerate(linhas[:-1]) if l.startswith("#EXT-X-STREAM-INF")]
        return baixar_hls(urljoin(url, max(variantes)[1]), destino_sem_ext, inicio, fim)
    t, dur, init, partes, desloc = 0.0, 0.0, None, [], None
    for linha in lista.splitlines():
        linha = linha.strip()
        if linha.startswith("#EXT-X-MAP"):
            init = urljoin(url, re.search(r'URI="([^"]+)"', linha).group(1))
        elif linha.startswith("#EXTINF:"):
            dur = float(linha[8:].split(",")[0])
        elif linha and not linha.startswith("#"):
            if t + dur > inicio and t < fim:
                if desloc is None:
                    desloc = inicio - t
                partes.append(urljoin(url, linha))
            t += dur
    if not partes:
        return None
    destino = f"{destino_sem_ext}.{'mp4' if init else 'ts'}"
    with open(destino, "wb") as f:
        for u in ([init] if init else []) + partes:
            f.write(_pegar(u))
    return destino, max(0.0, desloc)


def baixar_trecho_hls(info, pasta, inicio, fim, altura=1080):
    """Para lives em HLS (Twitch, Kick): baixa só o trecho do corte. None se a fonte não for HLS."""
    fmts = [f for f in info.get("formats") or []
            if "m3u8" in (f.get("protocol") or "") and f.get("vcodec") not in (None, "none")
            and (f.get("height") or 0) <= altura]
    if not fmts:
        return None
    url = max(fmts, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0))["url"]
    return baixar_hls(url, os.path.join(pasta, f"{info['id']}.{int(inicio)}"), inicio, fim)


def _duracao(arquivo):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "csv=p=0", arquivo], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def baixar_clipe(clipe, pasta):
    """Baixa um clipe de espectador. Retorna o arquivo, ou None se não for de GTA 6."""
    import yt_dlp
    if clipe["plataforma"] == "kick":
        r = baixar_hls(clipe["url"], os.path.join(pasta, clipe["id"]))
        return r[0] if r else None
    opts = yt.opcoes(format="b[format_id!^=portrait][height<=1080]/b[height<=1080]/b",
                     outtmpl=os.path.join(pasta, "%(id)s.%(ext)s"))
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(clipe["url"], download=False)
        jogo = " ".join(info.get("categories") or []).lower()
        if "grand theft auto vi" not in jogo:
            return None
        info = ydl.process_ie_result(info, download=True)
        return ydl.prepare_filename(info)


def processar_clipe(clipe, saida="saida", trabalho="trabalho", legendar=False, cam=None):
    """Clipe de espectador -> vídeo vertical com gancho na tela. Retorna o dict de metadados ou None."""
    os.makedirs(saida, exist_ok=True)
    os.makedirs(trabalho, exist_ok=True)
    canal = clipe["canal"]
    if any(b in canal.lower() for b in _proibidos()):
        return None
    bruto = baixar_clipe(clipe, trabalho)
    if not bruto:
        return None
    # a transcrição alimenta a IA do gancho; só vira legenda na tela se pedido (ela erra
    # bastante quando a fala do streamer se mistura com o áudio em inglês do jogo)
    usar_ia = bool(os.environ.get("ANTHROPIC_API_KEY"))
    palavras = legendas.transcrever(bruto, "pt") if (legendar or usar_ia) else None
    g = ganchos.gerar(canal, clipe["titulo"], legendas.texto(palavras), clipe["views"], bruto)
    if not legendar:
        palavras = None
    if not g["aprovado"]:
        print(f"reprovado ({g.get('motivo', '')[:120]}): {clipe['titulo']}")
        return None

    caixa = cam or facecam.detectar(bruto)
    nome = f"{_slug(canal)}-{_slug(clipe['id'])[-12:]}"
    destino = os.path.join(saida, nome + ".mp4")
    vertical = os.path.join(trabalho, nome + ".vertical.mp4")
    render.renderizar(bruto, vertical, cam=caixa)
    ass = os.path.join(trabalho, nome + ".ass")
    # gancho na divisória entre a cam e o gameplay; legenda logo abaixo, sem cobrir o jogo
    y_gancho, y_legenda = (render.A_CAM - 70, render.A_CAM + 130) if caixa else (150, 330)
    if legendas.escrever_ass(ass, _duracao(vertical), palavras, y_legenda, g["gancho"], y_gancho):
        _queimar(vertical, destino, ass)
    else:
        os.replace(vertical, destino)

    meta = {
        "arquivo": destino,
        "titulo": f"{g['titulo']} 😱 #gta6 #shorts",
        "descricao": f"Corte de {canal}\nClipe original: {clipe['url'] if clipe['plataforma'] == 'twitch' else 'kick.com/' + canal.lower()}\n\n{TAGS}",
        "gancho": g["gancho"], "gancho_por_ia": g["ia"],
        "canal_original": canal, "views_do_clipe": clipe["views"],
        "titulo_do_clipe": clipe["titulo"], "facecam": caixa,
    }
    with open(os.path.join(saida, nome + ".json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def processar(fonte, saida="saida", trabalho="trabalho", quantos=5, duracao=35,
              cam=None, sem_cam=False, legendar=False, ignorar_inicio=0, titulos="pt"):
    """`fonte` é uma URL do YouTube ou um arquivo local. Retorna a lista de cortes gerados."""
    os.makedirs(saida, exist_ok=True)
    os.makedirs(trabalho, exist_ok=True)
    local = os.path.exists(fonte)
    if local:
        audio, info = fonte, {"id": _slug(os.path.splitext(os.path.basename(fonte))[0])}
    else:
        audio, info = baixar_audio(fonte, trabalho)
        info["channel"] = info.get("channel") or info.get("uploader")
        canal = (info["channel"] or "").lower()
        if any(b in canal for b in _proibidos()):
            raise SystemExit(f"'{info.get('channel')}' está em nao_cortar.txt (proíbe cortes) — pulando.")

    nota = momentos.pontuar(momentos.volume_por_segundo(audio), info.get("heatmap"))
    cortes = momentos.escolher(nota, quantos, duracao, ignorar_inicio=ignorar_inicio)
    gerados, ultima_cam = [], None
    for n, (ini, fim, pontos) in enumerate(cortes, 1):
        if local:
            trecho, ss, to = fonte, ini, fim
        else:
            hls = baixar_trecho_hls(info, trabalho, ini, fim)
            if hls:
                trecho, ss, to = hls[0], hls[1], hls[1] + (fim - ini)
            else:
                trecho, ss, to = baixar_trecho(fonte, trabalho, ini, fim), None, None

        caixa = None if sem_cam else (cam or facecam.detectar(trecho) or ultima_cam)
        ultima_cam = caixa or ultima_cam  # a webcam não muda de lugar dentro da mesma live
        nome = f"{_slug(info.get('channel'))}-{info['id']}-{n:02d}"
        destino = os.path.join(saida, nome + ".mp4")

        if legendar:
            # legenda é sincronizada com o trecho já recortado, então renderiza em duas etapas
            bruto = os.path.join(trabalho, nome + ".bruto.mp4")
            render.renderizar(trecho, bruto, ss, to, caixa)
            ass = os.path.join(trabalho, nome + ".ass")
            y = render.A_CAM - 45 if caixa else 330  # em cima da divisória cam/gameplay
            if legendas.escrever_ass(ass, _duracao(bruto), legendas.transcrever(bruto), y):
                _queimar(bruto, destino, ass)
            else:
                os.replace(bruto, destino)
        else:
            render.renderizar(trecho, destino, ss, to, caixa)

        meta = {
            "arquivo": destino,
            "titulo": (GANCHOS_EN if titulos == "en" else GANCHOS)[(n - 1) % len(GANCHOS)].format(
                c=(info.get("channel") or "").upper()).strip() + " 😱 #gta6 #shorts",
            "descricao": (
                f"{'Clip from' if titulos == 'en' else 'Corte de'} {info.get('channel') or 'canal original'}\n"
                f"{'Full stream' if titulos == 'en' else 'Vídeo original'}: {info.get('webpage_url', fonte)}"
                + ("" if local else f"{'&' if '?' in info.get('webpage_url', fonte) else '?'}t={int(ini)}s")
                + f" ({_hms(ini)})\n\n{TAGS}"
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
