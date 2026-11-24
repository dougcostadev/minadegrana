"""Orquestra: baixar -> achar momentos -> detectar cam -> renderizar -> metadados."""
import json
import os
import re
import subprocess
import sys

from . import facecam, ganchos, legendas, momentos, postagem, render, yt

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


def _cam_exposta(mudanca, censura, censura_cam):
    """True se, em algum instante da mudança de lugar do rosto, o jogo está tampado e a cam aparece."""
    def dentro(t, trechos):
        return any(a <= t <= b for a, b in trechos)

    instantes = (mudanca["inicio"] + k / 4 for k in range(int((mudanca["fim"] - mudanca["inicio"]) * 4) + 1))
    return any(dentro(t, censura) and not dentro(t, censura_cam) for t in instantes)


def _avisar_cam(caixa, cam_muda, firme, censura, censura_cam, faltas):
    """Diz a quem está montando o corte o que precisa conferir na cam (na saída de erro).

    `faltas`: pedaços dos trechos em que o rosto não foi confirmado, quando foi o programa que
    decidiu onde a cam some; None quando veio de --censurar-cam.
    """
    def avisar(texto):
        print(texto, file=sys.stderr)

    nome = ":".join(str(v) for v in caixa or ())
    if cam_muda:  # a caixa é uma só para o clipe todo: ali o recorte pode cortar o rosto ou mostrar jogo
        avisar("AVISO: o rosto do streamer muda de lugar durante o clipe (" + facecam.descrever(cam_muda)
               + "). A webcam pode ter sido movida: confira a cam nesses trechos e, se o rosto sair"
               " cortado, monte de novo com --cam x:y:w:h.")
    if caixa and not firme:
        avisar(f"AVISO: o que aparece na caixa da cam ({nome}) muda ao longo do clipe: ou a webcam foi"
               " movida, ou a caixa não é a webcam (a detecção pode ter pego um rosto do jogo). Confira o"
               " painel de cima e corrija com --cam x:y:w:h ou --sem-cam.")
    if censura_cam and faltas is not None:
        pedacos = ",".join(f"{a:g}-{b:g}" for a, b in faltas)
        if not firme:
            avisar("AVISO: por isso a cam não aparece nos trechos de --censurar. Se ela for mesmo a webcam,"
                   " monte de novo com --censurar-cam "
                   + (f'"{pedacos}" (os pedaços em que o rosto não foi confirmado no lugar).' if faltas else "nao."))
        else:
            avisar(f'AVISO: nos trechos de --censurar a cam não aparece em "{pedacos}": ali o rosto do'
                   " streamer não foi confirmado na caixa da cam (webcam fora do lugar ou escondida, ou ele"
                   " de lado ou fora do quadro). Se no clipe original a webcam está no lugar nesses pedaços,"
                   ' monte de novo com --censurar-cam nao, ou com --censurar-cam "inicio-fim" só onde ela'
                   " sai do lugar.")
    if caixa and sum(b - a for a, b in censura) - sum(b - a for a, b in censura_cam) > 0.1:
        avisar(f"CONFIRA: nos trechos de --censurar a cam (caixa {nome}) aparece por cima do jogo. Ela tem"
               " de mostrar só a webcam do streamer: se for imagem do jogo, monte de novo com --sem-cam ou"
               " com --cam x:y:w:h.")
    expostas = [m for m in cam_muda if _cam_exposta(m, censura, censura_cam)] if faltas is None else []
    if expostas:
        avisar("ATENÇÃO: em trecho de --censurar com a cam à mostra o rosto sai do lugar ("
               + facecam.descrever(expostas) + "). Pode aparecer jogo nítido na cam: tire a cam desses"
               " pedaços com --censurar-cam.")


def processar_clipe(clipe, saida="saida", trabalho="trabalho", legendar=False, cam=None,
                    gancho=None, titulo=None, legenda=None, censura=None, tarjas=None, aviso=None,
                    censura_cam=None, sem_cam=False):
    """Clipe de espectador -> vídeo vertical com gancho na tela. Retorna os metadados ou None.

    Com `gancho` e `titulo` informados (escritos por quem viu o clipe), não consulta a IA.
    Nos trechos de `censura` o jogo sai de foco e a cam desce para cima dele (`render.renderizar`).
    `censura_cam` diz em que pedaços a cam não aparece. Sem ela, a cam só aparece se a caixa
    mostra a mesma cena o clipe inteiro e enquanto o rosto do streamer é confirmado no lugar
    (`facecam.analisar` e `facecam.ausencias`). `sem_cam` monta o layout sem câmera.
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

    # a análise roda mesmo com a caixa informada à mão: é ela que percebe a webcam mudando de lugar
    caixa, cam_muda, rosto, firme = facecam.SEM_CAM if sem_cam else facecam.analisar(bruto, cam)
    censura = list(censura or [])
    confirmar = censura_cam is None  # ninguém disse onde a cam some: vale o rosto, quadro a quadro
    faltas = facecam.ausencias(bruto, rosto, censura) if caixa and censura and confirmar else []
    if not caixa or not censura:
        censura_cam = []
    elif confirmar:  # caixa que não se mantém ao longo do clipe não tampa nada sem alguém conferir
        censura_cam = faltas if firme else list(censura)
    nome = f"{_slug(canal)}-{_slug(clipe['id'])[-12:]}"
    destino = os.path.join(saida, nome + ".mp4")
    ass = os.path.join(trabalho, nome + ".ass")
    # gancho na divisória entre a cam e o gameplay; legenda logo abaixo, sem cobrir o jogo
    y_gancho, y_legenda = (render.A_CAM - 70, render.A_CAM + 130) if caixa else (150, 330)
    tem_texto = legendas.escrever_ass(ass, _duracao(bruto), palavras, y_legenda, g["gancho"], y_gancho,
                                      y_marca=legendas.Y_MARCA if caixa else legendas.Y_MARCA_SEM_CAM)
    render.renderizar(bruto, destino, cam=caixa, legenda_ass=ass if tem_texto else None,
                      censura=censura, tarjas=tarjas, censura_cam=censura_cam)

    slug = clipe.get("slug") or canal.lower()
    meta = {
        "arquivo": destino, "id": clipe["id"], "plataforma": clipe["plataforma"],
        "canal_original": canal, "titulo_base": g["titulo"], "legenda": legenda or g["titulo"],
        "gancho": g["gancho"], "gancho_por_ia": g["ia"],
        "link_original": f"https://{'kick.com' if clipe['plataforma'] == 'kick' else 'www.twitch.tv'}/{slug}",
        "clipe_original": clipe["url"] if clipe["plataforma"] == "twitch" else None,
        "views_do_clipe": clipe["views"], "titulo_do_clipe": clipe["titulo"],
        "duracao_s": round(_duracao(destino)), "facecam": caixa,
    }
    if cam_muda:
        meta["cam_muda"] = cam_muda
    _avisar_cam(caixa, cam_muda, firme, censura, censura_cam, None if not confirmar else faltas)
    if censura or tarjas:
        trechos = sorted({(a, b) for a, b in censura} | {(t[0], t[1]) for t in tarjas or []})
        meta["censura"] = trechos
        if caixa and censura:
            meta["censura_cam"] = sorted(tuple(t) for t in censura_cam)
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
