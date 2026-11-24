import argparse
import json
import os

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
    fi.add_argument("--por-canal", type=int, default=4, help="máximo de clipes por streamer na fila")
    fi.add_argument("--min-semana", type=int, default=500, help="views mínimas para clipe da semana")
    fi.add_argument("--total", type=int, default=40)
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
    mo.add_argument("--aviso", help="ressalva para o dono do canal ler antes de postar (palavrão no áudio, cam torta...)")
    mo.add_argument("--receita", help="arquivo JSON com os blocos do edit de meme (ver AGENTE.md)")
    mo.add_argument("--capa", help="título curto da capa, até 4 palavras (padrão: o gancho)")
    mo.add_argument("--capa-tempo", type=float, help="segundo do clipe que vira o fundo da capa (padrão: 40%% da duração)")
    mo.add_argument("--capa-destaque", help="palavra do título da capa que sai em amarelo (padrão: a última linha)")
    mo.add_argument("--capa-foco", type=float, default=0.5, help="onde está a ação no quadro original, de 0 (esquerda) a 1 (direita)")
    mo.add_argument("--privacidade", default="private", choices=["private", "unlisted", "public"])
    pc = sub.add_parser("pacote", help="fecha o lote: vídeos e capas em saida/postar/ e POSTAR.md (sem horários)")
    pc.add_argument("--rodada", action="store_true", help="com horários: tudo no mesmo dia, nos horários livres")
    pc.add_argument("--agendado", action="store_true", help="com horários fixos (12h00, 18h30, 21h00), dia após dia")
    pc.add_argument("--agora", help="data/hora de referência (ISO), para refazer uma agenda")
    pc.add_argument("--ocupados", help="pasta com os documentos dos cortes já na pauta, para não repetir horário")
    pc.add_argument("--todos", action="store_true", help="inclui cortes desta pasta que já foram para a pauta")
    pc.add_argument("--horarios", help="horários escolhidos à mão, separados por vírgula (AAAA-MM-DDTHH:MM)")
    pc.add_argument("--ids", help="com --horarios: ids dos clipes na ordem desejada, separados por vírgula")
    li = sub.add_parser("linhas", help="gera os documentos do banco da pauta a partir do mapa de anexos")
    li.add_argument("assets", nargs="?", help="JSON {arquivo numerado: id do anexo}")
    sub.add_parser("pagina", help="monta saida/pauta.html (a página da pauta, lida do banco)")
    lp = sub.add_parser("limpeza", help="lista os vídeos de clipes já postados nas três redes, que podem ser apagados")
    lp.add_argument("pasta", help="pasta com os documentos da coleção `cortes` baixados do banco")
    es = sub.add_parser("estado", help="leva e traz a lista de clipes já usados do banco da pauta")
    es.add_argument("acao", choices=["carregar", "exportar"])
    es.add_argument("arquivo", nargs="?", default="saida/estado.json")
    de = sub.add_parser("descartar", help="marca o clipe N da fila como usado, sem gerar")
    de.add_argument("n", type=int)
    ba = sub.add_parser("base", help="baixa o clipe N e gera o corte vertical limpo, para estudar antes do edit")
    ba.add_argument("n", type=int)
    ba.add_argument("--cam", type=facecam.interpretar, help="posição da facecam no vídeo original, x:y:w:h")
    for x in (pv, mo, de, ba):
        x.add_argument("--fila", default="fila.json")
    qd = sub.add_parser("quadros", help="folhas de quadros com o segundo de cada um, para marcar os pontos do edit")
    qd.add_argument("arquivo")
    qd.add_argument("--de", type=float, default=0)
    qd.add_argument("--ate", type=float)
    qd.add_argument("--fps", type=float, default=2)
    fa = sub.add_parser("falas", help="transcrição do vídeo com o segundo de cada frase")
    fa.add_argument("arquivo")
    me = sub.add_parser("meme", help="acervo e busca de sons e GIFs de meme")
    me.add_argument("acao", choices=["acervo", "sons", "gifs"])
    me.add_argument("termo", nargs="?")
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
        fila = auto.montar_fila(a.canais, periodo=a.periodo, por_canal=a.por_canal,
                                min_semana=a.min_semana, total=a.total)
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
            receita = None
            if a.receita:
                with open(a.receita, encoding="utf-8") as f:
                    receita = json.load(f)
            meta = pipeline.processar_clipe(clipe, gancho=a.gancho, titulo=a.titulo, legenda=a.legenda,
                                            censura=censura, tarjas=tarjas, cam=a.cam, aviso=a.aviso,
                                            receita=receita, capa_titulo=a.capa, capa_tempo=a.capa_tempo,
                                            capa_destaque=a.capa_destaque, capa_foco=a.capa_foco)
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
                                              horarios=horarios, ordem_ids=ids, agendado=a.agendado), 1):
            print(f"{n:02d}  {m.get('postar_em_texto') or '':<20} {m['nome']:<16} {m.get('gancho') or ''}")
        print("Vídeos e capas em saida/postar/ e textos em saida/POSTAR.md")
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
    if a.cmd == "base":
        from . import pipeline
        with open(a.fila, encoding="utf-8") as f:
            clipe = json.load(f)[a.n]
        feito = pipeline.base(clipe, cam=a.cam)
        if not feito:
            print("não é GTA 6 (ou não baixou)")
            return
        limpo, _, caixa, duracao = feito
        print(f"corte limpo: {limpo}\nduração: {duracao:.1f}s\ncâmera: {'x:y:w:h = ' + ':'.join(map(str, caixa)) if caixa else 'não achada (formato sem câmera)'}")
        return
    if a.cmd == "quadros":
        import subprocess
        from . import render
        fim = a.ate if a.ate is not None else render._duracao(a.arquivo)
        por_folha, n, t = 32, 0, a.de
        while t < fim - 0.01:
            trecho = min(por_folha / a.fps, fim - t)
            saida = f"{os.path.splitext(a.arquivo)[0]}.quadros-{n:02d}.png"
            marca = f"drawtext=text='%{{eif\\:{t}+n/{a.fps}\\:d}}.%{{eif\\:mod(({t}+n/{a.fps})*10\\,10)\\:d}}s':fontcolor=yellow:fontsize=26:box=1:boxcolor=black@0.6:x=6:y=6"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-t", str(trecho), "-i", a.arquivo, "-vf",
                            f"fps={a.fps},scale=200:-2,{marca},tile=8x4", "-frames:v", "1", saida], check=True)
            print(saida)
            n, t = n + 1, t + trecho
        return
    if a.cmd == "falas":
        from . import legendas
        palavras = legendas.transcrever(a.arquivo)
        if palavras is None:
            print("faster-whisper não está instalado (pip install faster-whisper)")
            return
        linha, t0 = [], None
        for ini, fim, p in palavras:
            t0 = ini if t0 is None else t0
            linha.append(p.strip())
            if len(linha) >= 10 or p.strip().endswith((".", "?", "!")):
                print(f"{t0:6.1f} - {fim:6.1f}  {' '.join(linha)}")
                linha, t0 = [], None
        if linha:
            print(f"{t0:6.1f} -         {' '.join(linha)}")
        return
    if a.cmd == "meme":
        from . import meme
        if a.acao == "acervo":
            for tipo, itens in meme.acervo().items():
                print(f"{tipo}: {', '.join(sorted(itens))}")
        elif a.acao == "sons":
            for titulo, url in meme.buscar_sons(a.termo or ""):
                print(f"{titulo[:44]:44}  {url}")
        else:
            for url in meme.buscar_gifs(a.termo or ""):
                print(url)
        return
    if a.cmd == "limpeza":
        from . import postagem
        apagar, disponiveis = postagem.limpeza(a.pasta)
        from datetime import datetime
        hoje = datetime.now(postagem.FUSO).strftime("%Y-%m-%d")
        print(f"Clipes disponíveis para postar: {disponiveis}")
        print(f"Vídeos de clipes já postados nas três redes: {len(apagar)}")
        for doc, asset in apagar:
            print(f"  doc {doc}  anexo {asset}")
        if apagar:
            print('Em cada doc, grave (update, com if_version): {"asset": {"__delete__": true}, "video_removido": "%s"}' % hoje)
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
