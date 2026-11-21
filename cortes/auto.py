"""Modo automático: vídeos novos dos canais de canais.txt -> cortes -> (opcional) upload."""
import os

import yt_dlp

from . import pipeline, publicar, yt


# a Rockstar derruba vídeo com final da história; pula lives de zeramento
SPOILER = ("finale", "ending", "final mission", "final boss", "zerando", "final do jogo")


def _linhas(caminho):
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def videos_recentes(canal, quantos=5):
    """URLs dos últimos vídeos e lives encerradas de GTA 6 do canal (YouTube ou Twitch)."""
    ids = []
    with yt_dlp.YoutubeDL(yt.opcoes(extract_flat=True, playlistend=quantos, ignoreerrors=True)) as ydl:
        if "twitch.tv" in canal:
            paginas = [f"{canal.rstrip('/')}/videos?filter=archives&sort=time"]
        else:
            paginas = [f"{canal.rstrip('/')}/{aba}" for aba in ("videos", "streams")]
        for pagina in paginas:
            info = ydl.extract_info(pagina, download=False) or {}
            for e in info.get("entries") or []:
                titulo = (e or {}).get("title") or ""
                if e and e.get("id") and e.get("live_status") != "is_live" \
                        and any(t in titulo.lower() for t in ("gta 6", "gta vi", "gta6")) \
                        and not any(t in titulo.lower() for t in SPOILER):
                    ids.append(e.get("url") or f"https://www.youtube.com/watch?v={e['id']}")
    return ids


def rodar(canais="canais.txt", processados="processados.txt", max_videos=1, quantos=3,
          duracao=35, legendar=False, privacidade="private", saida="saida", titulos="pt"):
    feitos = set(_linhas(processados))
    lista = _linhas(canais)
    if not lista:
        raise SystemExit(f"{canais} está vazio — adicione os canais autorizados, um por linha.")
    fila = [v for c in lista for v in videos_recentes(c) if v not in feitos][:max_videos]
    print(f"{len(fila)} vídeo(s) novo(s) para cortar")
    for vid in fila:
        metas = pipeline.processar(vid, saida, quantos=quantos,
                                   duracao=duracao, legendar=legendar, ignorar_inicio=900,
                                   titulos=titulos)
        for m in metas:
            if publicar.configurado():
                print("publicado:", publicar.enviar(m, privacidade))
            else:
                print("gerado (sem credenciais de upload):", m["arquivo"])
        with open(processados, "a", encoding="utf-8") as f:
            f.write(vid + "\n")
