"""Textos de postagem para cada rede, agenda sugerida e o pacote final (POSTAR.md + postar.html)."""
import base64
import glob
import html
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
# Almoço e noite: as faixas em que os guias de horário para o Brasil mais concordam.
HORARIOS = ["12:00", "18:30", "21:00"]
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def _tag(canal):
    return "#" + re.sub(r"[^a-z0-9]", "", canal.lower())


def textos(m):
    """Título, descrição, legenda e tags prontos para colar em cada rede."""
    canal = m["canal_original"]
    titulo = m.get("titulo_base") or re.sub(r"\s*😱?\s*#.*$", "", m.get("titulo", "")).strip()
    legenda = m.get("legenda") or titulo
    link = m.get("link_original") or ""
    tag = _tag(canal)
    titulo_yt = f"{titulo[:83].rstrip()} #gta6 #shorts"
    return {
        "youtube": {
            "titulo": titulo_yt,
            "descricao": f"{legenda}\n\n🎮 Corte de {canal}. Live completa: {link}\n\n#gta6 #gtavi {tag} #cortes",
            "tags": f"gta 6, gta vi, gta 6 gameplay, gta 6 brasil, {canal}, {canal} gta 6, cortes gta 6, "
                    "momentos engraçados gta 6",
        },
        "tiktok": f"{legenda} 🎮 {canal}\n#gta6 #gtavi {tag} #gta6brasil #cortes",
        "instagram": (f"{legenda}\n\n🎮 Corte de {canal}. Segue o perfil para ver o melhor do GTA 6 todo dia.\n\n"
                      f"#gta6 #gtavi {tag} #gta6brasil #cortes"),
    }


def carregar(saida="saida"):
    metas = []
    for caminho in sorted(glob.glob(os.path.join(saida, "*.json"))):
        with open(caminho, encoding="utf-8") as f:
            m = json.load(f)
        if os.path.exists(m.get("arquivo", "")) and m.get("canal_original"):
            m.setdefault("redes", textos(m))
            metas.append(m)
    return metas


def agendar(metas, agora=None):
    """Ordena intercalando os streamers (os mais vistos primeiro) e dá um horário a cada corte."""
    agora = agora or datetime.now(FUSO)
    por_canal = {}
    for m in sorted(metas, key=lambda m: m.get("views_do_clipe", 0), reverse=True):
        por_canal.setdefault(m["canal_original"], []).append(m)
    filas = sorted(por_canal.values(), key=lambda f: f[0].get("views_do_clipe", 0), reverse=True)
    ordem = []
    while any(filas):
        for f in filas:
            if f:
                ordem.append(f.pop(0))
    dia, i = agora.date(), 0
    for m in ordem:
        while True:
            h, mi = map(int, HORARIOS[i % len(HORARIOS)].split(":"))
            quando = datetime(dia.year, dia.month, dia.day, h, mi, tzinfo=FUSO)
            i += 1
            if i % len(HORARIOS) == 0:
                dia += timedelta(days=1)
            if quando >= agora + timedelta(minutes=45):
                break
        m["postar_em"] = quando.isoformat()
        m["postar_em_texto"] = f"{DIAS[quando.weekday()]} {quando:%d/%m} às {quando:%H:%M}"
    return ordem


def _miniatura(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        video], capture_output=True, text=True)
    t = float(r.stdout.strip() or 0) * 0.4
    jpg = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                          "scale=216:384", "-q:v", "7", "-f", "image2", "-c:v", "mjpeg", "-"],
                         capture_output=True).stdout
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode() if jpg else ""


GUIA = [
    ("Em todas", [
        "O que decide a entrega é quanto tempo as pessoas assistem. Os primeiros 3 segundos pesam mais que curtida ou hashtag.",
        "Suba o arquivo original em cada rede. Vídeo baixado de outra rede com marca d'água perde alcance.",
        "Responda os primeiros comentários na primeira hora e fixe um comentário com o crédito do streamer.",
        "Os horários são ponto de partida. Depois de uma semana, troque pelos horários de pico do analytics de cada conta.",
    ]),
    ("YouTube Shorts", [
        "O título aparece cortado no feed: o assunto vem nas primeiras palavras.",
        "Use o campo Tags do Studio com as tags sugeridas. Marque \"não é conteúdo para crianças\".",
        "Acompanhe em Analytics a taxa de \"visualizaram x deslizaram\": é o termômetro de cada corte.",
    ]),
    ("TikTok", [
        "A legenda funciona como busca: nome do streamer e \"GTA 6\" escritos por extenso ajudam a categorizar.",
        "Poucas hashtags e específicas. As cinco sugeridas bastam.",
        "Escolha a capa no momento de maior reação, não no primeiro quadro.",
    ]),
    ("Instagram Reels", [
        "Marque o perfil do streamer no vídeo quando souber o @ dele.",
        "Contas que só repostam conteúdo de terceiros perdem recomendação para não seguidores. Misture conteúdo próprio assim que der.",
        "Compartilhe o Reel nos Stories logo depois de postar.",
    ]),
]


def escrever_md(ordem, caminho):
    linhas = ["# Pauta de postagem — Leonida Clipes", "",
              f"{len(ordem)} cortes, na ordem sugerida. Mesmo horário nas três redes.", ""]
    for n, m in enumerate(ordem, 1):
        r = m["redes"]
        linhas += [
            f"## {n:02d} · {m['canal_original']} · {m['postar_em_texto']}", "",
            f"Arquivo: `{os.path.basename(m['arquivo'])}`  ",
            f"Gancho na tela: {m.get('gancho') or '(sem gancho)'}", "",
            "**YouTube Shorts — título**", "", "```", r["youtube"]["titulo"], "```", "",
            "**YouTube Shorts — descrição**", "", "```", r["youtube"]["descricao"], "```", "",
            "**YouTube — tags**", "", "```", r["youtube"]["tags"], "```", "",
            "**TikTok — legenda**", "", "```", r["tiktok"], "```", "",
            "**Instagram Reels — legenda**", "", "```", r["instagram"], "```", "",
        ]
    linhas += ["## Como postar", ""]
    for titulo, itens in GUIA:
        linhas += [f"**{titulo}**", ""] + [f"- {i}" for i in itens] + [""]
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


def _campo(rotulo, texto, ident):
    e = html.escape
    return (f'<div class="campo"><div class="campo-topo"><span class="rotulo">{e(rotulo)}</span>'
            f'<button type="button" class="copiar" data-alvo="{ident}">Copiar</button></div>'
            f'<pre id="{ident}" class="texto" tabindex="0">{e(texto)}</pre></div>')


def escrever_html(ordem, caminho):
    e = html.escape
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "pauta.css"), encoding="utf-8") as f:
        css = f.read()
    with open(os.path.join(here, "pauta.js"), encoding="utf-8") as f:
        js = f.read()
    canais = sorted({m["canal_original"] for m in ordem})
    agenda, cartoes = [], []
    for n, m in enumerate(ordem, 1):
        cid = re.sub(r"[^a-z0-9]", "", str(m.get("id") or os.path.basename(m["arquivo"])).lower())[-14:]
        r = m["redes"]
        agenda.append(
            f'<li><a href="#c{cid}"><span class="quando">{e(m["postar_em_texto"])}</span>'
            f'<span class="num">{n:02d}</span><span class="oque">{e(m.get("gancho") or m.get("titulo_base", ""))}'
            f'</span><span class="quem">{e(m["canal_original"])}</span></a></li>')
        redes = ""
        for chave, nome, campos in (
                ("yt", "YouTube Shorts", [("Título", r["youtube"]["titulo"]), ("Descrição", r["youtube"]["descricao"]),
                                           ("Tags", r["youtube"]["tags"])]),
                ("tt", "TikTok", [("Legenda", r["tiktok"])]),
                ("ig", "Instagram Reels", [("Legenda", r["instagram"])])):
            blocos = "".join(_campo(rot, txt, f"t-{cid}-{chave}-{i}") for i, (rot, txt) in enumerate(campos))
            redes += (f'<section class="rede rede-{chave}"><header><h4>{nome}</h4>'
                      f'<label class="feito"><input type="checkbox" id="p-{cid}-{chave}"> postado</label>'
                      f'</header>{blocos}</section>')
        views = m.get("views_do_clipe")
        cartoes.append(
            f'<article class="corte" id="c{cid}"><div class="cabeca">'
            f'<img class="mini" src="{_miniatura(m["arquivo"])}" alt="Quadro do corte {n:02d}" width="108" height="192">'
            f'<div class="resumo"><p class="ordem">Corte {n:02d}</p>'
            f'<h3>{e(m.get("gancho") or m.get("titulo_base", ""))}</h3>'
            f'<dl><div><dt>Streamer</dt><dd>{e(m["canal_original"])}</dd></div>'
            f'<div><dt>Postar</dt><dd>{e(m["postar_em_texto"])}</dd></div>'
            f'<div><dt>Arquivo</dt><dd class="arquivo">{e(os.path.basename(m["arquivo"]))}</dd></div>'
            + (f'<div><dt>Clipe original</dt><dd>{views:,} views</dd></div>'.replace(",", ".") if views else "")
            + f'</dl></div></div><div class="redes">{redes}</div></article>')
    guia = "".join(f'<section><h3>{e(t)}</h3><ul>{"".join(f"<li>{e(i)}</li>" for i in itens)}</ul></section>'
                   for t, itens in GUIA)
    pagina = f"""<title>Pauta Leonida Clipes</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;500;600;700&display=swap">
<style>
{css}
</style>
<div class="pagina">
<header class="topo">
  <p class="marca">Leonida Clipes</p>
  <h1>Pauta de postagem</h1>
  <p class="sub">{len(ordem)} {"corte" if len(ordem) == 1 else "cortes"} de {len(canais)} {"streamer" if len(canais) == 1 else "streamers"} ({e(", ".join(canais))}). Cada corte traz o texto pronto para YouTube Shorts, TikTok e Instagram Reels. Poste o mesmo corte nas três redes no horário indicado e marque o que já foi.</p>
</header>
<section class="bloco" aria-labelledby="h-agenda">
  <h2 id="h-agenda">Agenda</h2>
  <ol class="agenda">{"".join(agenda)}</ol>
</section>
<section class="bloco" aria-labelledby="h-cortes">
  <h2 id="h-cortes">Cortes</h2>
  {"".join(cartoes)}
</section>
<section class="bloco guia" aria-labelledby="h-guia">
  <h2 id="h-guia">Como postar</h2>
  <div class="guia-grade">{guia}</div>
</section>
</div>
<script>
{js}
</script>
"""
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(pagina)


def pacote(saida="saida"):
    """Gera saida/POSTAR.md e saida/postar.html a partir dos cortes já renderizados."""
    ordem = agendar(carregar(saida))
    if not ordem:
        return []
    escrever_md(ordem, os.path.join(saida, "POSTAR.md"))
    escrever_html(ordem, os.path.join(saida, "postar.html"))
    return ordem
