"""Modo automático: vídeos novos dos canais de canais.txt -> cortes -> (opcional) upload."""
import os
from itertools import zip_longest

import yt_dlp

from . import pipeline, publicar, yt


# a Rockstar derruba vídeo com final da história; pula lives de zeramento
SPOILER = ("finale", "ending", "final mission", "final boss", "zerando", "zeramos", "zerei",
           "final do jogo", "grande final")


def _linhas(caminho):
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


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


def rodar(canais="canais.txt", processados="processados.txt", max_videos=1, quantos=3,
          duracao=35, legendar=False, privacidade="private", saida="saida", titulos="pt"):
    feitos = set(_linhas(processados))
    lista = _linhas(canais)
    if not lista:
        raise SystemExit(f"{canais} está vazio — adicione os canais autorizados, um por linha.")
    # intercala os canais para não cortar sempre o mesmo
    por_canal = [[v for v in videos_recentes(c) if v not in feitos] for c in lista]
    fila = [v for grupo in zip_longest(*por_canal) for v in grupo if v]
    print(f"{len(fila)} vídeo(s) novo(s) na fila")
    cortados = 0
    for vid in fila:
        if cortados >= max_videos:
            break
        try:
            metas = pipeline.processar(vid, saida, quantos=quantos, duracao=duracao,
                                       legendar=legendar, ignorar_inicio=900, titulos=titulos)
        except (Exception, SystemExit) as erro:  # um vídeo com problema não derruba a rodada
            print(f"pulando {vid}: {str(erro)[:200]}")
            continue
        cortados += 1
        for m in metas:
            if publicar.configurado():
                print("publicado:", publicar.enviar(m, privacidade))
            else:
                print("gerado (sem credenciais de upload):", m["arquivo"])
        with open(processados, "a", encoding="utf-8") as f:
            f.write(vid + "\n")
