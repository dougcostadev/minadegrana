import argparse
import json

from . import facecam


def main():
    p = argparse.ArgumentParser(prog="cortes", description="Fábrica de cortes verticais de GTA 6")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("descobrir", help="lista os vídeos/canais de GTA 6 em alta")
    d.add_argument("--saida", default="candidatos.json")
    d.add_argument("--por-busca", type=int, default=40)
    d.add_argument("--min-views", type=int, default=10_000)
    d.add_argument("--top", type=int, default=15)

    c = sub.add_parser("cortar", help="gera os cortes de um vídeo (URL ou arquivo local)")
    c.add_argument("fonte", nargs="+")
    c.add_argument("--quantos", type=int, default=5, help="cortes por vídeo")
    c.add_argument("--duracao", type=int, default=35, help="segundos por corte")
    c.add_argument("--cam", type=facecam.interpretar, help="posição da facecam x:y:w:h (pula a detecção)")
    c.add_argument("--sem-cam", action="store_true", help="layout só com gameplay")
    c.add_argument("--legendas", action="store_true", help="queima legendas (requer faster-whisper)")
    c.add_argument("--ignorar-inicio", type=int, default=0, help="pula os N primeiros segundos (intro/espera)")
    c.add_argument("--saida", default="saida")
    c.add_argument("--titulos", default="pt", choices=["pt", "en"], help="idioma dos títulos")

    au = sub.add_parser("auto", help="corta vídeos novos dos canais de canais.txt e publica")
    au.add_argument("--max-videos", type=int, default=1)
    au.add_argument("--quantos", type=int, default=3)
    au.add_argument("--legendas", action="store_true")
    au.add_argument("--titulos", default="pt", choices=["pt", "en"])
    au.add_argument("--privacidade", default="private", choices=["private", "unlisted", "public"])
    cl = sub.add_parser("clipes", help="lista os clipes de espectadores em alta de um canal (Twitch/Kick)")
    cl.add_argument("canal")
    cl.add_argument("--periodo", default="dia", choices=["dia", "semana"])
    cl.add_argument("--gerar", type=int, default=0, help="gera os N primeiros como vídeo vertical")
    fi = sub.add_parser("fila", help="salva em fila.json os clipes em alta ainda não usados, de todos os canais")
    fi.add_argument("--saida", default="fila.json")
    fi.add_argument("--canais", default="canais.txt", help="arquivo com a lista de canais")
    fi.add_argument("--periodo", default="ambos", choices=["dia", "semana", "ambos"],
                    help="dia = só clipes das últimas 24h")
    pv = sub.add_parser("previa", help="baixa o clipe N da fila e gera uma folha de quadros para avaliar")
    pv.add_argument("n", type=int)
    mo = sub.add_parser("montar", help="gera (e publica, se houver credenciais) o clipe N da fila com o gancho dado")
    mo.add_argument("n", type=int)
    mo.add_argument("--gancho", required=True)
    mo.add_argument("--titulo", required=True)
    mo.add_argument("--legenda", help="1 ou 2 frases para a legenda do post, terminando com uma pergunta")
    mo.add_argument("--cam", type=facecam.interpretar,
                    help="posição da facecam no vídeo original, x:y:w:h, quando a detecção errar")
    mo.add_argument("--censurar", help='trechos em segundos em que o painel do jogo fica pixelizado: "12-19,24-30"')
    mo.add_argument("--tarja", help='tarjas pretas: "inicio-fim:x,y,w,h" (frações do painel do jogo), separadas por ";"')
    mo.add_argument("--privacidade", default="private", choices=["private", "unlisted", "public"])
    pc = sub.add_parser("pacote", help="fecha o lote: agenda, vídeos numerados em saida/postar/ e POSTAR.md")
    pc.add_argument("--rodada", action="store_true", help="produção do dia: tudo no mesmo dia, de hora em hora")
    pc.add_argument("--agora", help="data/hora de referência (ISO), para refazer uma agenda")
    pc.add_argument("--ocupados", help="pasta com os documentos dos cortes já na pauta, para não repetir horário")
    pc.add_argument("--todos", action="store_true", help="inclui cortes desta pasta que já foram para a pauta")
    pc.add_argument("--horarios", help="horários escolhidos à mão, separados por vírgula (AAAA-MM-DDTHH:MM)")
    pc.add_argument("--ids", help="com --horarios: ids dos clipes na ordem desejada, separados por vírgula")
    li = sub.add_parser("linhas", help="gera os documentos do banco da pauta a partir do mapa de anexos")
    li.add_argument("assets", nargs="?", help="JSON {arquivo numerado: id do anexo}")
    sub.add_parser("pagina", help="monta saida/pauta.html (a página da pauta, lida do banco)")
    es = sub.add_parser("estado", help="leva e traz a lista de clipes já usados do banco da pauta")
    es.add_argument("acao", choices=["carregar", "exportar"])
    es.add_argument("arquivo", nargs="?", default="saida/estado.json")
    de = sub.add_parser("descartar", help="marca o clipe N da fila como usado, sem gerar")
    de.add_argument("n", type=int)
    for x in (pv, mo, de):
        x.add_argument("--fila", default="fila.json")
    ca = sub.add_parser("canal", help="lista os Shorts públicos do canal no YouTube, com as views")
    ca.add_argument("--canal", default="@clipeleonida")
    sub.add_parser("autorizar", help="gera o YT_REFRESH_TOKEN (rodar uma vez, na sua máquina)")

    a = p.parse_args()
    if a.cmd == "auto":
        from . import auto
        return auto.rodar(max_videos=a.max_videos, quantos=a.quantos, legendar=a.legendas,
                          privacidade=a.privacidade, titulos=a.titulos)
    if a.cmd == "clipes":
        from . import clipes, pipeline
        achados = clipes.em_alta(a.canal, a.periodo)
        for c in achados:
            print(f"  {c['views']:>8,}  {c['duracao']:>3.0f}s  {c['titulo']}")
        for c in achados[:a.gerar]:
            print(json.dumps(pipeline.processar_clipe(c), ensure_ascii=False))
        return
    if a.cmd == "fila":
        from . import auto
        fila = auto.montar_fila(a.canais, periodo=a.periodo)
        with open(a.saida, "w", encoding="utf-8") as f:
            json.dump(fila, f, ensure_ascii=False, indent=1)
        for n, c in enumerate(fila):
            print(f"{n:>3}  {'hoje' if c.get('fresco') else '    '}  {c['canal']:<16} {c['views']:>7,}  "
                  f"{c['duracao']:>3.0f}s  {c['titulo']}")
        return
    if a.cmd in ("previa", "montar", "descartar"):
        from . import auto, pipeline, publicar
        with open(a.fila, encoding="utf-8") as f:
            clipe = json.load(f)[a.n]
        if a.cmd == "previa":
            print(auto.previa(clipe) or "não é GTA 6 (ou não baixou)")
        elif a.cmd == "descartar":
            auto.marcar(clipe["id"])
        else:
            censura = [tuple(float(v) for v in t.split("-")) for t in a.censurar.split(",")] if a.censurar else None
            tarjas = None
            if a.tarja:
                tarjas = []
                for item in a.tarja.split(";"):
                    tempo, caixa = item.split(":")
                    tarjas.append(tuple(float(v) for v in tempo.split("-")) + tuple(float(v) for v in caixa.split(",")))
            meta = pipeline.processar_clipe(clipe, gancho=a.gancho, titulo=a.titulo, legenda=a.legenda,
                                            censura=censura, tarjas=tarjas, cam=a.cam)
            if meta and publicar.configurado():
                meta["publicado"] = publicar.enviar(meta, a.privacidade)
            auto.marcar(clipe["id"])
            print(json.dumps(meta, ensure_ascii=False))
        return
    if a.cmd == "pacote":
        from datetime import datetime
        from . import postagem
        agora = datetime.fromisoformat(a.agora).replace(tzinfo=postagem.FUSO) if a.agora else None
        ocupados = postagem.horarios_ocupados(a.ocupados) if a.ocupados else ()
        horarios = a.horarios.split(",") if a.horarios else None
        ids = a.ids.split(",") if a.ids else None
        for n, m in enumerate(postagem.pacote(rodada=a.rodada, agora=agora, ocupados=ocupados, todos=a.todos,
                                              horarios=horarios, ordem_ids=ids), 1):
            print(f"{n:02d}  {m['postar_em_texto']:<20} {m['nome']:<16} {m.get('gancho') or ''}")
        print("Vídeos numerados em saida/postar/ e textos em saida/POSTAR.md")
        return
    if a.cmd == "linhas":
        from . import postagem
        mapa = {}
        if a.assets:
            with open(a.assets, encoding="utf-8") as f:
                mapa = json.load(f)
        writes, faltando = postagem.linhas(mapa_assets=mapa)
        print(f"{len(writes)} documento(s) em saida/linhas/ e a lista de gravações em saida/lote.json")
        if faltando:
            print("SEM ANEXO (o botão de baixar não vai funcionar):", ", ".join(faltando))
        return
    if a.cmd == "pagina":
        from . import postagem
        print(postagem.pagina())
        return
    if a.cmd == "estado":
        from . import auto
        if a.acao == "carregar":
            print(auto.estado_carregar(a.arquivo), "id(s) novos trazidos do banco")
        else:
            print(auto.estado_exportar(a.arquivo), "id(s) recentes gravados em", a.arquivo)
        return
    if a.cmd == "canal":
        import yt_dlp
        from . import yt
        with yt_dlp.YoutubeDL(yt.opcoes(extract_flat=True, playlistend=200, ignoreerrors=True)) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/{a.canal}/shorts", download=False) or {}
        itens = [e for e in info.get("entries") or [] if e]
        print(f"{info.get('channel')} · {info.get('channel_follower_count')} inscritos · {len(itens)} Shorts públicos")
        for e in itens:
            print(f"  {e.get('view_count') or 0:>7,}  {e.get('title')}")
        return
    if a.cmd == "autorizar":
        from . import publicar
        return publicar.autorizar()
    if a.cmd == "descobrir":
        from . import descobrir
        videos = descobrir.buscar(por_busca=a.por_busca, min_views=a.min_views)
        if not videos:
            raise SystemExit("Nenhum vídeo encontrado — sem acesso ao YouTube ou filtro --min-views alto demais.")
        dados = descobrir.salvar(videos, a.saida)
        print("CANAIS")
        for x in dados["canais"][:a.top]:
            print(f"  {x['views']:>12,}  {x['videos']:>2} vídeos  {x['canal']}")
        print("VÍDEOS")
        for v in dados["videos"][:a.top]:
            print(f"  {v['views']:>12,}  {'🔴' if v['ao_vivo'] else '  '} {v['url']}  {v['canal']} — {v['titulo']}")
        print(f"\nLista completa em {a.saida}")
    else:
        from . import pipeline
        for fonte in a.fonte:
            for m in pipeline.processar(fonte, a.saida, quantos=a.quantos, duracao=a.duracao, cam=a.cam,
                                        sem_cam=a.sem_cam, legendar=a.legendas,
                                        ignorar_inicio=a.ignorar_inicio, titulos=a.titulos):
                print(json.dumps(m, ensure_ascii=False))


if __name__ == "__main__":
    main()
