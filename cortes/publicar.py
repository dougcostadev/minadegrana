"""Sobe os cortes no YouTube pela API oficial (Data API v3), usando um refresh token."""
import os

ESCOPO = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
VARS = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")


def configurado():
    return all(os.environ.get(v) for v in VARS)


def autorizar():
    """Roda UMA vez na sua máquina: abre o navegador e imprime o refresh token."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    cid, seg = os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"]
    fluxo = InstalledAppFlow.from_client_config({"installed": {
        "client_id": cid, "client_secret": seg, "token_uri": TOKEN_URI,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "redirect_uris": ["http://localhost"]}}, ESCOPO)
    cred = fluxo.run_local_server(port=0, access_type="offline", prompt="consent")
    print("\nYT_REFRESH_TOKEN =", cred.refresh_token)


def enviar(meta, privacidade="private"):
    """Envia um corte (dict do .json gerado pelo pipeline). Retorna a URL do vídeo."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    cred = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], token_uri=TOKEN_URI,
                       client_id=os.environ["YT_CLIENT_ID"],
                       client_secret=os.environ["YT_CLIENT_SECRET"], scopes=ESCOPO)
    yt = build("youtube", "v3", credentials=cred, cache_discovery=False)
    corpo = {
        "snippet": {"title": meta["titulo"][:100], "description": meta["descricao"],
                    "categoryId": "20", "tags": ["gta 6", "gta vi", "gta6", "cortes", "shorts"]},
        "status": {"privacyStatus": privacidade, "selfDeclaredMadeForKids": False},
    }
    midia = MediaFileUpload(meta["arquivo"], mimetype="video/mp4", chunksize=-1, resumable=True)
    r = yt.videos().insert(part="snippet,status", body=corpo, media_body=midia).execute()
    return f"https://youtube.com/shorts/{r['id']}"
