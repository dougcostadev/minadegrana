"""Modo automático: vídeos novos dos canais de canais.txt -> cortes -> (opcional) upload."""
import json
import os
from datetime import date, timedelta
from itertools import zip_longest

import yt_dlp

from . import clipes, meme, pipeline, publicar, yt


# a Rockstar derruba vídeo com final da história; pula lives de zeramento
SPOILER = ("finale", "ending", "final mission", "final boss", "zerando", "zeramos", "zerei",
           "final do jogo", "grande final")


def _linhas(caminho):
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def usados(processados="processados.txt"):
    """{id do clipe: data em que foi usado}. Linhas antigas sem data contam como de hoje."""
    hoje = date.today().isoformat()
    saida = {}
    for linha in _linhas(processados):
        partes = linha.split()
        saida[partes[0]] = partes[1] if len(partes) > 1 else hoje
    return saida


def estado_exportar(destino="saida/estado.json", processados="processados.txt", dias=8):
    """Grava os usados recentes num JSON para guardar no banco da pauta.

    Só os últimos `dias` importam: a fila nunca olha clipes mais velhos que uma semana.
    """
    corte = (date.today() - timedelta(days=dias)).isoformat()
    ids = {i: d for i, d in usados(processados).items() if d >= corte}
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump({"ids": ids, "atualizado": date.today().isoformat(), "memes": meme.usados()[-meme.MEMORIA:]}, f)
    return len(ids)


def estado_carregar(origem, processados="processados.txt"):
    """Junta ao processados.txt os ids lidos do banco da pauta (documento estado/usados)."""
    with open(origem, encoding="utf-8") as f:
        doc = json.load(f)
    for chave in ("data", "fields", "document"):  # o arquivo pode vir com um envelope
        if isinstance(doc.get(chave), dict) and "ids" in doc[chave]:
            doc = doc[chave]
    # memes e fechos dos últimos clipes, para não repetir; sem memória no banco, começa da semente
    meme.gravar_usados(doc["memes"] if isinstance(doc.get("memes"), list) else meme.SEMENTE)
    ja = usados(processados)
    novos = {i: d for i, d in (doc.get("ids") or {}).items() if i not in ja}
    with open(processados, "a", encoding="utf-8") as f:
        for i, d in novos.items():
            f.write(f"{i} {d}\n")
    return len(novos)


GTA = ("gta 6", "gta vi", "gta6", "vice city", "leonida")


def videos_recentes(canal, quantos=6):
    """URLs dos últimos vídeos e lives encerradas de GTA 6 do canal (YouTube, Twitch ou Kick)."""
    canal = canal.rstrip("/")
    if "twitch.tv" in canal:
        paginas = [f"{canal}/videos?filter=archives&sort=time"]
    elif "kick.com" in canal:
        paginas = [f"{canal}/videos"]
    else:
        paginas = [f"{canal}/{aba}" for aba in ("videos", "streams")]
    urls = []
    with yt_dlp.YoutubeDL(yt.opcoes(extract_flat=True, playlistend=quantos, ignoreerrors=True)) as ydl:
        for pagina in paginas:
            info = ydl.extract_info(pagina, download=False) or {}
            for e in info.get("entries") or []:
                if not e or not e.get("id"):
                    continue
                titulo = (e.get("title") or "").lower()
                if e.get("live_status") == "is_live" or (e.get("duration") or 0) < 600:
                    continue  # live em andamento ou vídeo curto demais
                if any(t in titulo for t in GTA) and not any(t in titulo for t in SPOILER):
                    urls.append(e.get("url") or f"https://www.youtube.com/watch?v={e['id']}")
    return urls


def _tem_clipes(canal):
    return "twitch.tv" in canal or "kick.com" in canal


def rodar(canais="canais.txt", processados="processados.txt", max_videos=1, quantos=3,
          duracao=35, legendar=False, privacidade="private", saida="saida", titulos="pt"):
    """Cada rodada publica até `quantos` cortes.

    Twitch/Kick: usa os clipes mais vistos do dia feitos pelos espectadores (momento já validado).
    YouTube: não tem clipes públicos, então cai no corte por pico de áudio da live.
    """
    feitos = set(usados(processados))
    lista = _linhas(canais)
    if not lista:
        raise SystemExit(f"{canais} está vazio — adicione os canais, um por linha.")

    def registrar(chave, metas):
        for m in metas:
            if publicar.configurado():
                print("publicado:", publicar.enviar(m, privacidade))
            else:
                print("gerado (sem credenciais de upload):", m["arquivo"])
        with open(processados, "a", encoding="utf-8") as f:
            f.write(chave + "\n")

    # 1) clipes de espectadores, intercalando canais e começando pelos mais vistos
    por_canal = []
    for c in (c for c in lista if _tem_clipes(c)):
        try:
            achados = clipes.em_alta(c, "dia") or clipes.em_alta(c, "semana")
            por_canal.append([x for x in achados if x["id"] not in feitos])
        except Exception as erro:
            print(f"sem clipes de {c}: {str(erro)[:150]}")
    fila = [x for grupo in zip_longest(*por_canal) for x in grupo if x]
    print(f"{len(fila)} clipe(s) em alta na fila")
    feitos_agora = 0
    for clipe in fila:
        if feitos_agora >= quantos:
            break
        try:
            meta = pipeline.processar_clipe(clipe, saida, legendar=legendar)
        except (Exception, SystemExit) as erro:
            print(f"pulando {clipe['url']}: {str(erro)[:200]}")
            continue
        registrar(clipe["id"], [meta] if meta else [])  # reprovado também não volta para a fila
        feitos_agora += 1 if meta else 0

    # 2) canais do YouTube: precisam de cookies para baixar
    if feitos_agora >= quantos or not os.environ.get("YT_COOKIES"):
        return
    por_canal = [[v for v in videos_recentes(c) if v not in feitos] for c in lista if not _tem_clipes(c)]
    cortados = 0
    for vid in (v for grupo in zip_longest(*por_canal) for v in grupo if v):
        if cortados >= max_videos:
            break
        try:
            metas = pipeline.processar(vid, saida, quantos=quantos - feitos_agora, duracao=duracao,
                                       legendar=legendar, ignorar_inicio=900, titulos=titulos)
        except (Exception, SystemExit) as erro:  # um vídeo com problema não derruba a rodada
            print(f"pulando {vid}: {str(erro)[:200]}")
            continue
        cortados += 1
        registrar(vid, metas)


def montar_fila(canais="canais.txt", processados="processados.txt", por_canal=4, periodo="ambos",
                total=40, min_dia=80, min_semana=500):
    """Clipes em alta ainda não usados, intercalando os streamers (para não postar só um).

    `periodo`: "dia" (só as últimas 24h, o conteúdo fresco), "semana" ou "ambos" (dia primeiro).
    """
    feitos = set(usados(processados))
    proibidos = pipeline._proibidos()
    periodos = ("dia",) if periodo == "dia" else ("semana",) if periodo == "semana" else ("dia", "semana")
    grupos = {}
    for c in (c for c in _linhas(canais) if _tem_clipes(c)):
        dono = c.rstrip("/").split("/")[-1].lower()
        if any(b in dono for b in proibidos):
            continue
        achados = {}
        for per in periodos:
            try:
                # clipe de hoje ainda teve pouco tempo para juntar views: o corte é bem mais baixo
                for x in clipes.em_alta(c, per, limite=40, min_views=min_dia if per == "dia" else min_semana):
                    x["fresco"] = per == "dia"
                    achados.setdefault(x["id"], x)
            except Exception as erro:
                print(f"sem clipes de {c} ({per}): {str(erro)[:150]}")
        novos = [x for x in achados.values() if x["id"] not in feitos]
        if novos:
            grupos[dono] = sorted(novos, key=lambda x: (not x["fresco"], -x["views"]))[:por_canal]
    filas = sorted(grupos.values(), key=lambda g: (not g[0]["fresco"], -g[0]["views"]))
    return [x for grupo in zip_longest(*filas) for x in grupo if x][:total]


def previa(clipe, trabalho="trabalho"):
    """Baixa o clipe e monta uma folha de 10 quadros para quem vai escrever o gancho ver o que acontece."""
    import subprocess
    os.makedirs(trabalho, exist_ok=True)
    arquivo = pipeline.baixar_clipe(clipe, trabalho)
    if not arquivo:
        return None
    folha = os.path.join(trabalho, f"previa-{pipeline._slug(clipe['id'])[-12:]}.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", arquivo, "-vf",
                    f"fps=10/{max(clipe['duracao'], 10)},scale=384:-1,tile=5x2", "-frames:v", "1", folha],
                   check=True)
    return folha


def marcar(clipe_id, processados="processados.txt"):
    with open(processados, "a", encoding="utf-8") as f:
        f.write(f"{clipe_id} {date.today().isoformat()}\n")
