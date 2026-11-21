"""Opções comuns do yt-dlp. YT_COOKIES_FILE aponta para um cookies.txt (necessário em IP de datacenter)."""
import os


def opcoes(**extra):
    opts = {"quiet": True, "ignoreerrors": False}
    cookies = os.environ.get("YT_COOKIES_FILE")
    if cookies and os.path.exists(cookies):
        opts["cookiefile"] = cookies
    opts.update(extra)
    return opts
