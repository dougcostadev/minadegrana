"""Clipes feitos pelos espectadores (Twitch e Kick): já vêm com título e contagem de views,
ou seja, são os momentos que comprovadamente chamaram atenção."""
import json
import urllib.request

import yt_dlp

from . import yt

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Accept": "application/json"}


def _twitch(canal, periodo, limite):
    login = canal.rstrip("/").split("/")[-1]
    faixa = {"dia": "24hr", "semana": "7d"}[periodo]
    with yt_dlp.YoutubeDL(yt.opcoes(extract_flat=True, playlistend=limite, ignoreerrors=True)) as ydl:
        info = ydl.extract_info(f"https://www.twitch.tv/{login}/clips?range={faixa}", download=False) or {}
    return [{"plataforma": "twitch", "canal": login, "id": e["id"], "url": e["url"],
             "titulo": e.get("title") or "", "views": e.get("view_count") or 0,
             "duracao": e.get("duration") or 0}
            for e in info.get("entries") or [] if e and e.get("url")]


def _kick(canal, periodo, limite):
    login = canal.rstrip("/").split("/")[-1]
    faixa = {"dia": "day", "semana": "week"}[periodo]
    req = urllib.request.Request(
        f"https://kick.com/api/v2/channels/{login}/clips?sort=view&time={faixa}", headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        dados = json.load(r)
    return [{"plataforma": "kick", "canal": (c.get("channel") or {}).get("username") or login,
             "id": c["id"], "url": c.get("clip_url") or c.get("video_url"),
             "titulo": c.get("title") or "", "views": c.get("views") or 0,
             "duracao": c.get("duration") or 0, "gta": "vi" in ((c.get("category") or {}).get("slug") or "").split("-")}
            for c in (dados.get("clips") or [])[:limite] if not c.get("is_private")]


def em_alta(canal, periodo="dia", limite=15, min_views=500, min_dur=12, max_dur=90):
    """Clipes mais vistos do canal no período, do mais visto para o menos visto."""
    busca = _kick if "kick.com" in canal else _twitch
    clipes = [c for c in busca(canal, periodo, limite)
              if c["views"] >= min_views and min_dur <= c["duracao"] <= max_dur and c.get("gta", True)]
    return sorted(clipes, key=lambda c: c["views"], reverse=True)
