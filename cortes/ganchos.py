"""Gancho (a frase na tela) e título de cada corte.

Com ANTHROPIC_API_KEY definido, o Claude lê a transcrição e escreve um gancho específico
para o que acontece no clipe — e reprova clipes sem graça ou sem contexto.
Sem a chave, usa o título que o espectador deu ao clipe, quando ele presta.
"""
import os
import re

MODELO = "claude-opus-5-5"

INSTRUCOES = """Você edita um canal de cortes de GTA 6 para Shorts/TikTok/Reels em português do Brasil.
Recebe um clipe curto de uma live: o streamer, o título que um espectador deu, quantas views o
clipe teve na plataforma, alguns quadros do vídeo em ordem cronológica e a transcrição automática
(imprecisa, mistura a fala do streamer com falas do jogo).

Decida se o clipe se sustenta sozinho para quem nunca viu a live: precisa ter uma situação
compreensível e um desfecho (susto, piada, erro, reação, descoberta). Reprove clipes que são
só anúncio de patrocinador, sorteio, conversa com o chat sem contexto, cena de sexo ou nudez do
jogo, ou spoiler do final da história.

Se aprovar, escreva:
- gancho: a frase que fica na tela o vídeo inteiro. Até 8 palavras, MAIÚSCULAS, específica do
  que acontece neste clipe, que crie curiosidade sem entregar o desfecho. Não invente fatos que
  a transcrição e o título não sustentam. Sem emoji e sem hashtag.
- titulo: título do post, até 70 caracteres, com o nome do streamer e "GTA 6". Sem hashtag.
Não use palavrão nem termo ofensivo no gancho ou no título, mesmo que apareça na transcrição."""

_RISADA = re.compile(r"^[kKaAhHsSuUeErR\s!?.]+$")
# sem IA, corta pelo título o que claramente não serve: patrocínio, sorteio e cena de sexo do jogo
_BARRADO = re.compile(r"kabum|sorteio|cupom|desconto|patroc|promo|pix|\bsub\b|sexo|secsu|sex\b|\+18|pelad|nude",
                      re.IGNORECASE)


def _titulo_presta(titulo):
    t = titulo.strip()
    return len(t.split()) >= 2 and len(t) >= 8 and not _RISADA.match(t)


def _sem_ia(canal, titulo_clipe):
    if _BARRADO.search(titulo_clipe):
        return {"aprovado": False, "gancho": None, "titulo": "", "ia": False,
                "motivo": "título indica patrocínio, sorteio ou conteúdo adulto"}
    gancho = titulo_clipe.strip().upper() if _titulo_presta(titulo_clipe) else None
    base = titulo_clipe.strip() if gancho else "Momento insano"
    return {"aprovado": True, "gancho": gancho, "titulo": f"{base} | {canal} no GTA 6"[:90], "ia": False}


def _quadros(video, quantos=5):
    """Quadros do vídeo em JPEG base64, para a IA ver o que acontece."""
    import base64
    import subprocess
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        video], capture_output=True, text=True).stdout.strip()
    dur = float(d or 0)
    imagens = []
    for i in range(quantos):
        t = dur * (i + 0.5) / quantos
        jpg = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
                              "-vf", "scale=960:-2", "-f", "image2", "-c:v", "mjpeg", "-"],
                             capture_output=True).stdout
        if jpg:
            imagens.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg",
                "data": base64.standard_b64encode(jpg).decode()}})
    return imagens


def gerar(canal, titulo_clipe, transcricao, views, video=None):
    """Retorna {'aprovado', 'gancho', 'titulo', 'ia'}."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _sem_ia(canal, titulo_clipe)
    import anthropic
    from pydantic import BaseModel

    class Avaliacao(BaseModel):
        aprovado: bool
        motivo: str
        gancho: str
        titulo: str

    try:
        r = anthropic.Anthropic().messages.parse(
            model=MODELO, max_tokens=4000, system=INSTRUCOES, output_format=Avaliacao,
            messages=[{"role": "user", "content": (_quadros(video) if video else []) + [{
                "type": "text", "text": (
                    f"Streamer: {canal}\nTítulo dado pelo espectador: {titulo_clipe}\n"
                    f"Views do clipe: {views}\n\n"
                    f"Transcrição:\n{transcricao or '(sem fala detectada)'}")}]}])
    except anthropic.APIError as erro:
        print(f"gancho por IA indisponível ({type(erro).__name__}); usando o título do clipe")
        return _sem_ia(canal, titulo_clipe)
    a = r.parsed_output
    if r.stop_reason == "refusal" or a is None:
        return _sem_ia(canal, titulo_clipe)
    if not a.aprovado:
        return {"aprovado": False, "gancho": None, "titulo": "", "ia": True, "motivo": a.motivo}
    return {"aprovado": True, "gancho": a.gancho.strip().upper(), "titulo": a.titulo.strip()[:90], "ia": True}
