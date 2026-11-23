"""Textos de postagem para cada rede, agenda sugerida e o pacote final (POSTAR.md + postar.html)."""
import base64
import glob
import html
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
# Almoço e noite: as faixas em que os guias de horário para o Brasil mais concordam.
HORARIOS = ["12:00", "18:30", "21:00"]
# Horários que a produção do dia pode ocupar, além dos fixos acima.
GRADE = ["12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:30", "19:30", "20:30", "21:00",
         "22:00", "23:00"]
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


# login da plataforma -> nome pelo qual o público conhece o streamer
NOMES = {"tioorochitwitch": "Tio Orochi", "paulinholokobr": "Paulinho o Loko", "xarola_": "Xarola",
         "rincon061tv": "Rincon", "gabepeixe": "Gabepeixe", "bistecone": "Bistecone",
         "bisteconee": "Bistecone", "snopey": "Snopey", "brino": "Brino", "thedarkness": "The Darkness",
         "blackoutz": "Blackoutz", "baiano": "Baiano", "malena0202": "Malena", "brabox": "Brabox",
         "yoda": "YoDa", "tck10": "TCK", "jonvlogs": "Jon Vlogs"}


def nome(canal):
    return NOMES.get(canal.lower(), canal)


def _tag(canal):
    return "#" + re.sub(r"[^a-z0-9]", "", nome(canal).lower())


def textos(m):
    """Título, descrição, legenda e tags prontos para colar em cada rede."""
    canal = nome(m["canal_original"])
    titulo = m.get("titulo_base") or re.sub(r"\s*😱?\s*#.*$", "", m.get("titulo", "")).strip()
    legenda = m.get("legenda") or titulo
    link = m.get("link_original") or ""
    tag = _tag(m["canal_original"])
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


def carregar(saida="saida", incluir_publicados=False):
    metas = []
    for caminho in sorted(glob.glob(os.path.join(saida, "*.json"))):
        with open(caminho, encoding="utf-8") as f:
            m = json.load(f)
        if not isinstance(m, dict):  # agenda.json e lote.json também moram em saida/
            continue
        if (m.get("na_pauta") or m.get("segurar")) and not incluir_publicados:
            continue  # já está na biblioteca, ou foi segurado de propósito ("segurar": true no .json)
        if os.path.exists(m.get("arquivo", "")) and m.get("canal_original"):
            m["_json"] = caminho
            m["redes"] = textos(m)
            m["nome"] = nome(m["canal_original"])
            metas.append(m)
    return metas


def horarios_ocupados(pasta):
    """Horários (ISO) dos cortes que já estão na pauta, lidos de uma pasta com os documentos JSON."""
    ocupados = set()
    for caminho in glob.glob(os.path.join(pasta, "*.json")):
        try:
            with open(caminho, encoding="utf-8") as f:
                doc = json.load(f)
            quando = None if doc.get("descartado") else doc.get("postar_em")  # descartado libera o horário
            if quando:
                ocupados.add(datetime.fromisoformat(quando).astimezone(FUSO).replace(second=0, microsecond=0))
        except (ValueError, OSError, AttributeError):
            continue
    return ocupados


def intercalar(metas):
    """Ordem para apresentar um lote: alterna os streamers, cada um começando pelo clipe mais visto."""
    por_canal = {}
    for m in sorted(metas, key=lambda m: m.get("views_do_clipe", 0), reverse=True):
        por_canal.setdefault(m.get("nome") or m["canal_original"], []).append(m)
    filas = sorted(por_canal.values(), key=lambda f: f[0].get("views_do_clipe", 0), reverse=True)
    ordem = []
    while any(filas):
        for f in filas:
            if f:
                ordem.append(f.pop(0))
    return ordem


def agendar(metas, agora=None, rodada=False, ocupados=(), horarios=None):
    """Ordena intercalando os streamers (os mais vistos primeiro) e dá um horário a cada corte.

    Padrão: um corte por horário fixo (12h00, 18h30, 21h00), dia após dia.
    `rodada=True` (produção do dia): o primeiro vai no próximo horário fixo e os demais de hora
    em hora depois dele, tudo no mesmo dia.
    """
    agora = agora or datetime.now(FUSO)
    por_canal = {}
    for m in sorted(metas, key=lambda m: m.get("views_do_clipe", 0), reverse=True):
        por_canal.setdefault(m["nome"], []).append(m)
    filas = sorted(por_canal.values(), key=lambda f: f[0].get("views_do_clipe", 0), reverse=True)
    ordem = []
    while any(filas):
        for f in filas:
            if f:
                ordem.append(f.pop(0))
    if horarios:  # horários escolhidos à mão, um por corte, na ordem
        for m, texto in zip(ordem, horarios):
            quando = datetime.fromisoformat(texto).replace(tzinfo=FUSO)
            m["postar_em"] = quando.isoformat()
            m["postar_em_texto"] = f"{DIAS[quando.weekday()]} {quando:%d/%m} às {quando:%H:%M}"
        return ordem[:len(horarios)]
    if rodada:
        # grade do dia: do almoço até o fim da noite, para um corte feito de manhã sair à tarde
        grade = []
        for d in range(4):
            for h in GRADE:
                hh, mi = map(int, h.split(":"))
                grade.append(datetime.combine(agora.date() + timedelta(days=d), datetime.min.time(), FUSO)
                             .replace(hour=hh, minute=mi))
        livres = [q for q in sorted(set(grade))
                  if q >= agora + timedelta(minutes=15) and q not in set(ocupados)]
        for m, quando in zip(ordem, livres):
            m["postar_em"] = quando.isoformat()
            m["postar_em_texto"] = f"{DIAS[quando.weekday()]} {quando:%d/%m} às {quando:%H:%M}"
        return ordem
    dia, i = agora.date(), 0
    for m in ordem:
        while True:
            h, mi = map(int, HORARIOS[i % len(HORARIOS)].split(":"))
            quando = datetime(dia.year, dia.month, dia.day, h, mi, tzinfo=FUSO)
            i += 1
            if i % len(HORARIOS) == 0:
                dia += timedelta(days=1)
            if quando >= agora + timedelta(minutes=15):
                break
        m["postar_em"] = quando.isoformat()
        m["postar_em_texto"] = f"{DIAS[quando.weekday()]} {quando:%d/%m} às {quando:%H:%M}"
    return ordem


def _capa(video, destino):
    """Grava um quadro do vídeo (360x640) para servir de capa na pauta."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        video], capture_output=True, text=True)
    t = float(r.stdout.strip() or 0) * 0.4
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf",
                    "scale=360:640", "-q:v", "5", destino], check=True)
    return destino


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
    linhas = ["# Cortes prontos — Leonida Clipes", "", f"{len(ordem)} cortes com os textos de cada rede.", ""]
    for n, m in enumerate(ordem, 1):
        r = m["redes"]
        linhas += [
            f"## {n:02d} · {m['nome']}" + (f" · {m['postar_em_texto']}" if m.get("postar_em_texto") else ""), "",
            f"Arquivo: `{os.path.basename(m.get('arquivo_postagem') or m['arquivo'])}`  ",
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


def pagina(destino="saida/pauta.html"):
    """Monta a página da pauta (um arquivo só, com CSS e JS embutidos).

    A página não carrega nenhum corte no código: ela lê tudo do banco de dados dela mesma
    (coleção `cortes`), então só precisa ser republicada quando o layout muda.
    """
    aqui = os.path.dirname(os.path.abspath(__file__))
    partes = {}
    for nome_arq in ("pauta.html", "pauta.css", "pauta.js"):
        with open(os.path.join(aqui, nome_arq), encoding="utf-8") as f:
            partes[nome_arq] = f.read()
    guia = "".join(
        f'<section><h3>{html.escape(t)}</h3><ul>{"".join(f"<li>{html.escape(i)}</li>" for i in itens)}</ul></section>'
        for t, itens in GUIA)
    doc = (partes["pauta.html"].replace("/*CSS*/", partes["pauta.css"])
           .replace("/*JS*/", partes["pauta.js"]).replace("<!--GUIA-->", guia))
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(doc)
    return destino


def limpeza(pasta):
    """Lê os documentos da biblioteca salvos em `pasta` (coleção `cortes`).

    Devolve ([(doc_id, id do anexo de vídeo)], disponíveis): os clipes já postados nas três
    redes que ainda guardam o vídeo, e quantos clipes seguem disponíveis para postar.
    """
    apagar, disponiveis = [], 0
    for arq in sorted(glob.glob(os.path.join(pasta, "*.json"))):
        with open(arq, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            continue
        postado = d.get("postado") or {}
        if all(postado.get(k) is True for k in ("yt", "tt", "ig")):
            if d.get("asset"):
                apagar.append((os.path.basename(arq)[:-5], d["asset"]))
        elif not d.get("descartado"):
            disponiveis += 1
    return apagar, disponiveis


def _doc_id(m):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(m.get("id") or os.path.basename(m["arquivo"])))[-40:]


def linhas(saida="saida", mapa_assets=None):
    """Prepara um documento JSON por corte para o banco da pauta (coleção `cortes`).

    `mapa_assets`: {nome do arquivo numerado: id do anexo} devolvido pelo upload dos vídeos
    (.mp4) e das capas (.jpg) de saida/postar/.
    Grava saida/linhas/<id>.json e saida/lote.json (a lista `writes` para gravar tudo de uma vez).
    """
    mapa_assets = mapa_assets or {}
    with open(os.path.join(saida, "agenda.json"), encoding="utf-8") as f:
        ordem = json.load(f)
    pasta = os.path.join(saida, "linhas")
    os.makedirs(pasta, exist_ok=True)
    writes, faltando = [], []
    for m in ordem:
        arquivo = os.path.basename(m["arquivo_postagem"])
        asset = mapa_assets.get(arquivo)
        if not asset:
            faltando.append(arquivo)
        doc = {
            "id": str(m.get("id") or ""), "nome": m["nome"], "canal": m["canal_original"],
            "plataforma": m.get("plataforma"), "gancho": m.get("gancho") or m.get("titulo_base") or "",
            "titulo_base": m.get("titulo_base"), "legenda": m.get("legenda"), "redes": m["redes"],
            "arquivo": arquivo, "asset": asset,
            "capa": mapa_assets.get(os.path.splitext(arquivo)[0] + ".jpg"),
            "postar_em": m.get("postar_em"), "postar_em_texto": m.get("postar_em_texto"),
            "views": m.get("views_do_clipe"), "duracao_s": m.get("duracao_s"),
            "link_original": m.get("link_original"), "aviso": m.get("aviso"),
            "criado_em": datetime.now(FUSO).isoformat(timespec="seconds"),
            "postado": {"yt": False, "tt": False, "ig": False},
        }
        caminho = os.path.abspath(os.path.join(pasta, _doc_id(m) + ".json"))
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False)
        writes.append({"op": "set", "collection": "cortes", "doc_id": _doc_id(m), "file_path": caminho})
    with open(os.path.join(saida, "lote.json"), "w", encoding="utf-8") as f:
        json.dump(writes, f, ensure_ascii=False, indent=1)
    if mapa_assets:  # marca os cortes como já enviados: o próximo `pacote` desta pasta não os repete
        for m in ordem:
            origem = m.get("_json")
            if origem and os.path.exists(origem):
                with open(origem, encoding="utf-8") as f:
                    meta = json.load(f)
                meta["na_pauta"] = True
                with open(origem, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
    return writes, faltando


def pacote(saida="saida", rodada=False, agora=None, ocupados=(), todos=False, horarios=None, ordem_ids=None,
           agendado=False):
    """Fecha o lote: vídeos e capas em saida/postar/, POSTAR.md e agenda.json.

    Padrão (biblioteca): sem horário; quem posta decide quando e onde. Com `agendado`, `rodada`
    ou `horarios`, cada corte recebe um horário sugerido e os arquivos saem numerados.
    Depois de subir os vídeos como anexos da página, `linhas()` gera os documentos do banco.
    """
    com_horario = agendado or rodada or bool(horarios)
    metas = carregar(saida, incluir_publicados=todos)
    from . import render
    for m in metas:  # garante que todo vídeo cabe como anexo da pauta
        render.compactar(m["arquivo"])
    if ordem_ids:  # ordem escolhida à mão (ids dos clipes); o resto fica de fora
        por_id = {str(m.get("id")): m for m in metas}
        metas = [por_id[i] for i in ordem_ids if i in por_id]
        for m, texto in zip(metas, horarios or []):
            quando = datetime.fromisoformat(texto).replace(tzinfo=FUSO)
            m["postar_em"] = quando.isoformat()
            m["postar_em_texto"] = f"{DIAS[quando.weekday()]} {quando:%d/%m} às {quando:%H:%M}"
        ordem = metas[:len(horarios or [])]
    elif com_horario:
        ordem = agendar(metas, agora, rodada, ocupados, horarios)
    else:
        ordem = intercalar(metas)
    if not ordem:
        return []
    # cópias numeradas na ordem de postagem, para não haver dúvida de qual vídeo é qual
    pasta = os.path.join(saida, "postar")
    os.makedirs(pasta, exist_ok=True)
    for antigo in glob.glob(os.path.join(pasta, "*.mp4")) + glob.glob(os.path.join(pasta, "*.jpg")):
        os.remove(antigo)
    for n, m in enumerate(ordem, 1):
        prefixo = f"{n:02d}-" if com_horario else ""  # na biblioteca o nome do arquivo não muda
        m["arquivo_postagem"] = os.path.join(pasta, prefixo + os.path.basename(m["arquivo"]))
        shutil.copyfile(m["arquivo"], m["arquivo_postagem"])  # cópia de verdade: o upload recusa hard link
        _capa(m["arquivo"], os.path.splitext(m["arquivo_postagem"])[0] + ".jpg")
    escrever_md(ordem, os.path.join(saida, "POSTAR.md"))
    with open(os.path.join(saida, "agenda.json"), "w", encoding="utf-8") as f:
        json.dump(ordem, f, ensure_ascii=False)
    return ordem
