"""Produção do canal de fé e motivacional.

python -m fe produzir fe/roteiros/hoje/*.json     voz + vídeo + capa + textos, em saida-fe/
python -m fe linhas saida-fe/assets.json         documentos da biblioteca (saida-fe/lote.json)
python -m fe limpeza <pasta com os docs>         vídeos já postados no TikTok, cujo arquivo pode sair
python -m fe imagens                             banco de pinturas, com descrição e pontos de foco
python -m fe ver <imagem>                        miniatura com grade de coordenadas para escolher o foco
python -m fe imagem <nome> "<File:... do Wikimedia Commons>" "<descrição>"   baixa e cadastra uma pintura
python -m fe pagina                              monta a página da biblioteca (saida-fe/biblioteca.html)
"""
import argparse, glob, hashlib, json, os, re, subprocess, sys, time, urllib.parse
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SAIDA = os.path.join(RAIZ, "saida-fe")
BANCO = os.path.join(AQUI, "imagens.json")
FUSO = timezone(timedelta(hours=-3))
TAGS = {"fe": ["#fé", "#deus", "#jesus", "#oração", "#palavradedeus", "#cristão", "#gospel"],
        "motivacional": ["#motivação", "#superação", "#foco", "#disciplina", "#mentalidade", "#nãodesista", "#fé"]}


def _slug(t):
    t = re.sub(r"[^a-z0-9]+", "-", t.lower().encode("ascii", "ignore").decode()).strip("-")
    return t[:40] or "video"


def textos(rot):
    tags = rot.get("hashtags") or TAGS.get(rot.get("tema", "fe"), TAGS["fe"])
    tags = " ".join(t if t.startswith("#") else "#" + t for t in tags[:7])
    leg = rot.get("legenda", "").strip()
    return {"tiktok": f"{leg}\n\n{tags}".strip()}  # o canal posta só no TikTok


def produzir(arquivos, saida=SAIDA):
    sys.path.insert(0, AQUI)
    import voz, montar
    rots = []
    for arq in arquivos:
        rot = json.load(open(arq, encoding="utf-8"))
        usadas = [f["img"] for f in rot["frases"]] + [f["corte"]["img"] for f in rot["frases"] if f.get("corte", {}).get("img")]
        faltam = [i for i in usadas if not os.path.exists(os.path.join(AQUI, "img", i))]
        if faltam:
            print("PULADO", arq, "- imagens que não existem:", ", ".join(sorted(set(faltam)))); continue
        nome = rot.get("id") or _slug(os.path.splitext(os.path.basename(arq))[0])
        rot["saida"] = nome + ".mp4"; rot["_pasta"] = os.path.join(saida, "trabalho", nome); rot["_id"] = nome
        rots.append(rot)
    t0 = time.time()  # voz de todos os roteiros com o modelo carregado uma vez
    tx, sa = [], []
    for r in rots:
        for i, f in enumerate(r["frases"]):
            tx.append(f["texto"]); sa.append(f"{r['_pasta']}/fala/{i+1}.wav")
    voz.falar_lote(tx, sa)
    print(f"voz: {len(tx)} frases em {time.time() - t0:.0f} s", flush=True)
    os.makedirs(os.path.join(saida, "postar"), exist_ok=True)
    for r in rots:
        t1 = time.time(); avisos = []
        info = montar.montar(r, r["_pasta"], avisar=avisos.append)
        final = os.path.join(saida, "postar", r["saida"]); os.replace(info["video"], final)
        capa = final[:-4] + ".jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", final, "-frames:v", "1", "-q:v", "3", capa], check=True)
        folha = os.path.join(saida, "conferir", r["_id"] + ".jpg"); os.makedirs(os.path.dirname(folha), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", final, "-vf", "fps=1/2,scale=180:-2,tile=8x2", "-frames:v", "1",
                        folha], check=True)  # um quadro a cada 2 s, para conferir sem assistir
        meta = {"id": r["_id"], "tema": r.get("tema", "fe"), "gancho": r["gancho"].replace("\\N", " ").replace("*", ""),
                "versiculo": r.get("versiculo"), "roteiro": " ".join(f["texto"] for f in r["frases"]),
                "redes": textos(r), "arquivo": os.path.basename(final), "duracao_s": info["duracao_s"], "aviso": r.get("aviso"),
                "avisos": avisos}
        json.dump(meta, open(final[:-4] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{r['_id']}: {info['duracao_s']} s de vídeo, montado em {time.time() - t1:.0f} s" +
              ("".join("\n  " + a for a in avisos)), flush=True)
    print(f"total: {len(rots)} vídeos em {time.time() - t0:.0f} s")


def linhas(mapa_arq, saida=SAIDA):
    mapa = json.load(open(mapa_arq, encoding="utf-8")) if mapa_arq else {}
    pasta = os.path.join(saida, "linhas"); os.makedirs(pasta, exist_ok=True)
    writes = []
    for arq in sorted(glob.glob(os.path.join(saida, "postar", "*.json"))):
        m = json.load(open(arq, encoding="utf-8"))
        doc = {**{k: m[k] for k in ("id", "tema", "gancho", "versiculo", "roteiro", "redes", "arquivo", "duracao_s")},
               "nome": "Motivacional" if m["tema"] == "motivacional" else "Fé",
               "asset": mapa.get(m["arquivo"]), "capa": mapa.get(m["arquivo"][:-4] + ".jpg"),
               "aviso": m.get("aviso"),  # nota para quem posta; os avisos de transcrição ficam só com o agente
               "criado_em": datetime.now(FUSO).isoformat(timespec="seconds"), "postado": {"tt": False}}
        caminho = os.path.abspath(os.path.join(pasta, m["id"] + ".json"))
        json.dump(doc, open(caminho, "w", encoding="utf-8"), ensure_ascii=False)
        writes.append({"op": "set", "collection": "videos", "doc_id": m["id"], "file_path": caminho})
    json.dump(writes, open(os.path.join(saida, "lote.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(writes), "documentos em", os.path.join(saida, "lote.json"))


def limpeza(pasta):
    apagar, livres = [], 0
    for arq in sorted(glob.glob(os.path.join(pasta, "*.json"))):
        d = json.load(open(arq, encoding="utf-8"))
        if not isinstance(d, dict): continue
        p = d.get("postado") or {}
        if p.get("tt"):  # o canal posta só no TikTok
            if d.get("asset"): apagar.append({"doc_id": os.path.basename(arq)[:-5], "asset": d["asset"]})
        elif not d.get("descartado"):
            livres += 1
    print(json.dumps({"apagar": apagar, "disponiveis": livres}, ensure_ascii=False, indent=1))


def imagens():
    for nome, d in json.load(open(BANCO, encoding="utf-8")).items():
        print(f"{nome}: {d['descricao']}")
        for p, v in (d.get("pontos") or {}).items():
            print(f"    {p}: foco {v[0]}, aperto {v[1]}")


def ver(nome):
    arq = os.path.join(AQUI, "img", nome if nome.endswith(".jpg") else nome + ".jpg")
    sai = os.path.join(SAIDA, "ver", os.path.basename(arq)); os.makedirs(os.path.dirname(sai), exist_ok=True)
    linhas_ = ",".join(f"drawbox=x=iw*{i/10}:y=0:w=1:h=ih:color=yellow@0.6,drawbox=x=0:y=ih*{i/10}:w=iw:h=1:color=yellow@0.6"
                       for i in range(1, 10))
    rot = ",".join(f"drawtext=text='{i/10:.1f}':x=w*{i/10}+3:y=3:fontcolor=yellow:fontsize=18,"
                   f"drawtext=text='{i/10:.1f}':x=3:y=h*{i/10}+3:fontcolor=yellow:fontsize=18" for i in range(1, 10))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", arq, "-vf", f"scale=720:-2,{linhas_},{rot}", sai], check=True)
    print(sai)


def imagem(nome, titulo, descricao):
    f = titulo.replace("File:", "").replace(" ", "_"); h = hashlib.md5(f.encode()).hexdigest(); q = urllib.parse.quote(f)
    destino = os.path.join(AQUI, "img", nome + ".jpg")
    for larg in (1920, 1280, 960):
        url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{larg}px-{q}"
        for _ in range(3):
            subprocess.run(["curl", "-s", "-A", "CanalFeBot/1.0", "-o", destino, url])
            tipo = subprocess.run(["file", "-b", destino], capture_output=True, text=True).stdout
            if tipo.startswith("JPEG"):
                banco = json.load(open(BANCO, encoding="utf-8"))
                banco[nome + ".jpg"] = {"descricao": descricao, "fonte": titulo, "pontos": {}}
                json.dump(banco, open(BANCO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print("ok", destino, larg); return
            if "429" in open(destino, "rb").read().decode("utf8", "ignore"): time.sleep(20); continue
            break
    if os.path.exists(destino): os.remove(destino)
    sys.exit("não consegui baixar " + titulo)


def pagina():
    sys.path.insert(0, AQUI)
    import biblioteca
    print(biblioteca.pagina(os.path.join(SAIDA, "biblioteca.html")))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="python -m fe"); sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("produzir"); p.add_argument("roteiros", nargs="+")
    p = sub.add_parser("linhas"); p.add_argument("mapa", nargs="?")
    p = sub.add_parser("limpeza"); p.add_argument("pasta")
    sub.add_parser("imagens")
    p = sub.add_parser("ver"); p.add_argument("nome")
    p = sub.add_parser("imagem"); p.add_argument("nome"); p.add_argument("titulo"); p.add_argument("descricao")
    sub.add_parser("pagina")
    a = ap.parse_args()
    if a.cmd == "produzir": produzir(a.roteiros)
    elif a.cmd == "linhas": linhas(a.mapa)
    elif a.cmd == "limpeza": limpeza(a.pasta)
    elif a.cmd == "imagens": imagens()
    elif a.cmd == "ver": ver(a.nome)
    elif a.cmd == "imagem": imagem(a.nome, a.titulo, a.descricao)
    elif a.cmd == "pagina": pagina()
