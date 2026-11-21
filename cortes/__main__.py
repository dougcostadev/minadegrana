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

    a = p.parse_args()
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
                                        ignorar_inicio=a.ignorar_inicio):
                print(json.dumps(m, ensure_ascii=False))


if __name__ == "__main__":
    main()
