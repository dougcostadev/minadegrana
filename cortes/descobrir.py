"""Busca no YouTube os vídeos e lives de GTA 6 mais relevantes e ranqueia por canal."""
import json
from collections import defaultdict

import yt_dlp

BUSCAS = [
    "GTA 6 gameplay",
    "GTA 6 ao vivo",
    "GTA VI live gameplay",
    "jogando GTA 6",
    "GTA 6 melhores momentos",
]


def buscar(buscas=BUSCAS, por_busca=40, min_views=10_000):
    opts = {"quiet": True, "extract_flat": True, "skip_download": True, "ignoreerrors": True}
    videos = {}
    with yt_dlp.YoutubeDL(opts) as ydl:
        for termo in buscas:
            info = ydl.extract_info(f"ytsearch{por_busca}:{termo}", download=False) or {}
            for e in info.get("entries") or []:
                if not e or not e.get("id"):
                    continue
                views = e.get("view_count") or e.get("concurrent_view_count") or 0
                ao_vivo = e.get("live_status") == "is_live"
                if views < min_views and not ao_vivo:
                    continue
                videos[e["id"]] = {
                    "id": e["id"],
                    "url": f"https://www.youtube.com/watch?v={e['id']}",
                    "titulo": e.get("title"),
                    "canal": e.get("channel") or e.get("uploader"),
                    "canal_id": e.get("channel_id"),
                    "views": views,
                    "duracao_s": e.get("duration"),
                    "ao_vivo": ao_vivo,
                }
    return sorted(videos.values(), key=lambda v: v["views"], reverse=True)


def ranquear_canais(videos):
    canais = defaultdict(lambda: {"views": 0, "videos": 0})
    for v in videos:
        c = canais[v["canal"] or "?"]
        c["views"] += v["views"]
        c["videos"] += 1
        c["canal_id"] = v["canal_id"]
    return sorted(
        ({"canal": k, **c} for k, c in canais.items()), key=lambda c: c["views"], reverse=True
    )


def salvar(videos, caminho):
    dados = {"canais": ranquear_canais(videos), "videos": videos}
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return dados
