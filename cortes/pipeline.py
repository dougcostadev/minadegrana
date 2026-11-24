"""Orquestra: baixar -> achar momentos -> detectar cam -> renderizar -> metadados."""
import json
import os
import re
import subprocess

from . import facecam, ganchos, legendas, meme, momentos, postagem, render, ui, yt

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


def _pegar(u, faixa=None):
    """GET simples; `faixa` = (inicio, tamanho) em bytes para pedir só um pedaço do arquivo."""
    import urllib.request
    cab = {"User-Agent": "Mozilla/5.0"}
    if faixa:
        cab["Range"] = f"bytes={faixa[0]}-{faixa[0] + faixa[1] - 1}"
    with urllib.request.urlopen(urllib.request.Request(u, headers=cab), timeout=60) as r:
        dados = r.read()
    # servidor que ignora Range devolve o arquivo inteiro: recorta aqui
    return dados[faixa[0]:faixa[0] + faixa[1]] if faixa and len(dados) > faixa[1] else dados


def _faixa(texto, fim_anterior):
    """'tamanho[@inicio]' de EXT-X-BYTERANGE -> (inicio, tamanho)."""
    tam, _, ini = texto.strip().strip('"').partition("@")
    return (int(ini) if ini else fim_anterior, int(tam))


def baixar_hls(url, destino_sem_ext, inicio=0.0, fim=float("inf")):
    """Baixa os segmentos de uma playlist HLS que cobrem [inicio, fim].

    Retorna (arquivo, deslocamento) — o trecho pedido começa `deslocamento` segundos dentro
    do arquivo — ou None se a playlist não tiver segmentos nesse intervalo.
    Respeita EXT-X-BYTERANGE (a Kick guarda o clipe inteiro num só .ts e aponta pedaços dele).
    """
    from urllib.parse import urljoin
    lista = _pegar(url).decode()
    if "#EXT-X-STREAM-INF" in lista:  # playlist mestre: segue para a variante de maior qualidade
        linhas = lista.splitlines()
        variantes = [(int((re.search(r"BANDWIDTH=(\d+)", l) or [0, 0])[1]), linhas[i + 1].strip())
                     for i, l in enumerate(linhas[:-1]) if l.startswith("#EXT-X-STREAM-INF")]
        return baixar_hls(urljoin(url, max(variantes)[1]), destino_sem_ext, inicio, fim)
    t, dur, init, partes, desloc = 0.0, 0.0, None, [], None
    faixa, fim_faixa = None, {}
    for linha in lista.splitlines():
        linha = linha.strip()
        if linha.startswith("#EXT-X-MAP"):
            u = urljoin(url, re.search(r'URI="([^"]+)"', linha).group(1))
            br = re.search(r'BYTERANGE="([^"]+)"', linha)
            init = (u, _faixa(br.group(1), 0) if br else None)
        elif linha.startswith("#EXTINF:"):
            dur = float(linha[8:].split(",")[0])
        elif linha.startswith("#EXT-X-BYTERANGE:"):
            faixa = linha.split(":", 1)[1]
        elif linha and not linha.startswith("#"):
            u = urljoin(url, linha)
            f = _faixa(faixa, fim_faixa.get(u, 0)) if faixa else None
            if f:
                fim_faixa[u] = f[0] + f[1]
            if t + dur > inicio and t < fim:
                if desloc is None:
                    desloc = inicio - t
                partes.append((u, f))
            t += dur
            faixa = None
    if not partes:
        return None
    destino = f"{destino_sem_ext}.{'mp4' if init else 'ts'}"
    with open(destino, "wb") as arq:
        for u, f in ([init] if init else []) + partes:
            arq.write(_pegar(u, f))
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


def _quadro(video, segundo):
    """Um quadro do vídeo como imagem PIL."""
    import cv2
    from PIL import Image
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, segundo) * 1000)
    ok, frame = cap.read()
    cap.release()
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) if ok else None


def base(clipe, trabalho="trabalho", cam=None, censura=None, tarjas=None, bruto=None):
    """Baixa o clipe e gera o corte vertical limpo (sem moldura), base do edit.

    Retorna (arquivo limpo, arquivo bruto, caixa da câmera, duração) ou None.
    """
    os.makedirs(trabalho, exist_ok=True)
    bruto = bruto or baixar_clipe(clipe, trabalho)
    if not bruto:
        return None
    caixa = cam or facecam.detectar(bruto)
    nome = f"{_slug(clipe['canal'])}-{_slug(clipe['id'])[-12:]}"
    limpo = os.path.join(trabalho, nome + ".limpo.mp4")
    ass = None
    if censura:  # o selo CENSURADO acompanha a pixelização
        ass = os.path.join(trabalho, nome + ".ass")
        legendas.escrever_ass(ass, _duracao(bruto), None, censura=censura,
                              y_censura=render.A_CAM + 580 if caixa else 900, marca=None, chamada=None)
    render.renderizar(bruto, limpo, cam=caixa, legenda_ass=ass, censura=censura, tarjas=tarjas, moldura=False)
    return limpo, bruto, caixa, _duracao(limpo)


def processar_clipe(clipe, saida="saida", trabalho="trabalho", legendar=False, cam=None,
                    gancho=None, titulo=None, legenda=None, censura=None, tarjas=None, aviso=None,
                    receita=None, capa_titulo=None, capa_tempo=None, capa_destaque=None, capa_foco=0.5):
    """Clipe de espectador -> vídeo vertical com gancho na tela. Retorna os metadados ou None.

    Com `gancho` e `titulo` informados (escritos por quem viu o clipe), não consulta a IA.
    """
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
    usar_ia = bool(os.environ.get("ANTHROPIC_API_KEY")) and not gancho
    palavras = legendas.transcrever(bruto, "pt") if (legendar or usar_ia) else None
    if gancho:
        g = {"aprovado": True, "gancho": gancho.upper(), "titulo": titulo or gancho.capitalize(), "ia": False}
    else:
        g = ganchos.gerar(canal, clipe["titulo"], legendas.texto(palavras), clipe["views"], bruto)
    if not legendar:
        palavras = None
    if not g["aprovado"]:
        print(f"reprovado ({g.get('motivo', '')[:120]}): {clipe['titulo']}")
        return None

    limpo, _, caixa, duracao = base(clipe, trabalho, cam, censura, tarjas, bruto=bruto)
    nome = f"{_slug(canal)}-{_slug(clipe['id'])[-12:]}"
    destino = os.path.join(saida, nome + ".mp4")
    # por cima do corte limpo: moldura do canal (gancho, etiqueta do streamer, selo), capa no
    # primeiro quadro e, se houver receita, o edit de meme
    moldura = ui.moldura(os.path.join(trabalho, nome + ".ui.png"), g["gancho"], canal, com_cam=bool(caixa))
    instante = duracao * 0.4 if capa_tempo is None else float(capa_tempo)
    quadro = _quadro(bruto, instante)
    rosto = None
    if caixa and quadro is not None:
        x, y, w, h = caixa
        rosto = quadro.crop((int(x + w * 0.18), y, int(x + w * 0.82), y + h))
    capa = None
    if quadro is not None:
        capa = ui.capa(os.path.join(saida, nome + ".capa.jpg"), quadro, capa_titulo or g["gancho"].rstrip("."), canal,
                       rosto=rosto, destaque=capa_destaque, foco=capa_foco, evitar=caixa)
    blocos = (receita or {}).get("blocos") or [{"tipo": "clipe", "de": 0, "ate": duracao}]
    qual = sum(ord(c) for c in str(clipe["id"]))  # a frase da chamada varia de um clipe para outro
    final = ui.chamada(os.path.join(trabalho, nome + ".cta.png"), com_cam=bool(caixa), indice=qual)
    estalo = ui.chamada(os.path.join(trabalho, nome + ".cta2.png"), com_cam=bool(caixa), indice=qual, estalo=True)
    meme.editar(limpo, destino, blocos, moldura=moldura, capa=capa, com_cam=bool(caixa), trabalho=trabalho,
                chamada=final, estalo=estalo)
    render.compactar(destino)

    slug = clipe.get("slug") or canal.lower()
    meta = {
        "arquivo": destino, "id": clipe["id"], "plataforma": clipe["plataforma"],
        "canal_original": canal, "titulo_base": g["titulo"], "legenda": legenda or g["titulo"],
        "gancho": g["gancho"], "gancho_por_ia": g["ia"],
        "link_original": f"https://{'kick.com' if clipe['plataforma'] == 'kick' else 'www.twitch.tv'}/{slug}",
        "clipe_original": clipe["url"] if clipe["plataforma"] == "twitch" else None,
        "views_do_clipe": clipe["views"], "titulo_do_clipe": clipe["titulo"],
        "duracao_s": round(_duracao(destino)), "facecam": caixa,
        "capa_arquivo": capa, "capa_titulo": capa_titulo, "edit_de_meme": bool(receita),
    }
    if censura or tarjas:
        trechos = sorted([(a, b) for a, b in censura or []] + [(t[0], t[1]) for t in tarjas or []])
        meta["censura"] = trechos
        meta["aviso"] = ("Tem trecho censurado (" + ", ".join(f"{a:.0f}s a {b:.0f}s" for a, b in trechos)
                         + "). Assista ao vídeo inteiro antes de postar.")
    if aviso:  # ressalva do editor (palavrão, cam torta...), aparece na página da biblioteca
        meta["aviso"] = " ".join(x for x in (meta.get("aviso"), aviso.strip()) if x)
    meta["redes"] = postagem.textos(meta)
    meta["titulo"] = meta["redes"]["youtube"]["titulo"]        # usados pelo upload automático
    meta["descricao"] = meta["redes"]["youtube"]["descricao"]
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
