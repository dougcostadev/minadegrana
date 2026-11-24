"""Página da biblioteca do canal de fé: a mesma estante da biblioteca do Clipes Leonida (cortes/pauta.*),
adaptada para duas redes (TikTok e Instagram), tema no lugar de streamer e paleta dourada.

Ela lê tudo do próprio banco (coleção `videos`), então só é republicada quando o layout muda.
"""
import html, os

AQUI = os.path.dirname(os.path.abspath(__file__))
CORTES = os.path.join(os.path.dirname(AQUI), "cortes")

GUIA = [
    ("Antes de postar", [
        "Baixe o vídeo e poste o arquivo original em cada rede. Vídeo repostado com marca d'água de outra rede perde alcance.",
        "Escolha um som em alta no próprio app e deixe o volume dele baixo (uns 10 a 15%), para a voz continuar clara.",
        "Ative a marcação de conteúdo gerado por IA: a voz é sintética.",
    ]),
    ("TikTok", [
        "A legenda pronta já tem o gancho, o pedido de comentário e as hashtags. Cole sem mudar a primeira linha.",
        "Use a capa (primeiro quadro) com o gancho grande escrito.",
        "Responda os primeiros comentários de \"amém\" ou \"eu creio\" na primeira hora: comentário puxa entrega.",
    ]),
    ("Instagram Reels", [
        "Poste como Reel com a mesma legenda e compartilhe nos Stories logo depois.",
        "Fixe um comentário com o versículo completo quando o vídeo tiver um.",
    ]),
]

TROCAS = {
    "cortes/pauta.html": [
        ("<title>Biblioteca Clipes Leonida</title>", "<title>Biblioteca Fé e Motivação</title>"),
        ('<p class="marca">Clipes Leonida</p>', '<p class="marca">Fé e motivação</p>'),
        ("<h1>Biblioteca de clipes</h1>", "<h1>Biblioteca de vídeos</h1>"),
        ("Carregando os clipes…", "Carregando os vídeos…"),
        ('    <button type="button" class="seg seg-yt" data-rede="yt">YouTube <span class="n" id="n-yt"></span></button>\n', ""),
        ('placeholder="streamer ou palavra do gancho"', 'placeholder="palavra do gancho ou versículo"'),
        ('<label class="rotulo-campo" for="streamer">Streamer', '<label class="rotulo-campo" for="streamer">Tema'),
        ('        <option value="vistos">Mais vistos na live</option>\n', ""),
    ],
    "cortes/pauta.js": [
        ('    { k: "yt", curto: "YT", nome: "YouTube", campos: function (r) { return [["Título", r.youtube.titulo], ["Descrição", r.youtube.descricao], ["Tags", r.youtube.tags]]; } },\n', ""),
        ('var FAIXAS = ["livres", "feitos", "descartados"], ORDENS = ["novos", "vistos", "curtos"];',
         'var FAIXAS = ["livres", "feitos", "descartados"], ORDENS = ["novos", "curtos"];'),
        ('localStorage.getItem("biblioteca-ver")', 'localStorage.getItem("biblioteca-fe-ver")'),
        ('localStorage.setItem("biblioteca-ver"', 'localStorage.setItem("biblioteca-fe-ver"'),
        ("return rede === \"todas\" ? !(p.yt && p.tt && p.ig) : !p[rede];", "return rede === \"todas\" ? !(p.tt && p.ig) : !p[rede];"),
        ('if (c.views) partes.push(Number(c.views).toLocaleString("pt-BR") + " views na live");',
         'if (c.versiculo) partes.push(c.versiculo);'),
        ('return db.doc("cortes/" + x.id).update(patch);', 'return db.doc("videos/" + x.id).update(patch);'),
        ('String(c.arquivo || "clipe.mp4")', 'String(c.arquivo || "video.mp4")'),
        ('"Vídeo apagado depois de postado nas três redes, para liberar espaço. Os textos continuam aqui." : "Este clipe não tem vídeo anexado."',
         '"Vídeo apagado depois de postado nas duas redes, para liberar espaço. Os textos continuam aqui." : "Este vídeo não tem arquivo anexado."'),
        ('text: c.descartado ? "Restaurar clipe" : "Descartar clipe"', 'text: c.descartado ? "Restaurar vídeo" : "Descartar vídeo"'),
        ('"aria-label": "Clipe selecionado"', '"aria-label": "Vídeo selecionado"'),
        ('semAcento((x.c.gancho || "") + " " + (x.c.titulo_base || "") + " " + (x.c.nome || ""))',
         'semAcento((x.c.gancho || "") + " " + (x.c.versiculo || "") + " " + (x.c.roteiro || "") + " " + (x.c.nome || ""))'),
        ('livres: ["Nenhum clipe disponível com esse filtro.", "ainda não postados"]', 'livres: ["Nenhum vídeo disponível com esse filtro.", "ainda não postados"]'),
        ('feitos: ["Nenhum clipe postado com esse filtro.", "já postados"]', 'feitos: ["Nenhum vídeo postado com esse filtro.", "já postados"]'),
        ('descartados: ["Nenhum clipe descartado.", "descartados (dá para restaurar)"]', 'descartados: ["Nenhum vídeo descartado.", "descartados (dá para restaurar)"]'),
        ('" clipes prontos · " + (ativos.length - todosPostados) + " com rede faltando · " + todosPostados + " postados nas três redes"',
         '" vídeos prontos · " + (ativos.length - todosPostados) + " com rede faltando · " + todosPostados + " postados nas duas redes"'),
        ('(itens.length === 1 ? " clipe " : " clipes ")', '(itens.length === 1 ? " vídeo " : " vídeos ")'),
        ('". Toque num clipe para ver o vídeo e os textos."', '". Toque num vídeo para ver e copiar os textos."'),
        ('avisar("A biblioteca está vazia. Os clipes de cada rodada aparecem aqui, com o vídeo para baixar e os textos de cada rede.");',
         'avisar("A biblioteca está vazia. Os vídeos de cada rodada aparecem aqui, com o arquivo para baixar e os textos de cada rede.");'),
        ('avisar("Ainda não consegui carregar os clipes. A página continua tentando.");', 'avisar("Ainda não consegui carregar os vídeos. A página continua tentando.");'),
        ('avisar("Os clipes aparecem quando esta página é aberta pelo link do Claude.");', 'avisar("Os vídeos aparecem quando esta página é aberta pelo link do Claude.");'),
        ('avisar("Não foi possível ler os clipes agora ("', 'avisar("Não foi possível ler os vídeos agora ("'),
        ('db.collection("cortes").limit(1000)', 'db.collection("videos").limit(1000)'),
    ],
    "cortes/pauta.css": [],
}

PALETA = """
/* Paleta do canal de fé: dourado e vinho sobre papel claro; noite azul-escura no tema escuro. */
:root { --fundo: #faf7f1; --papel: #ffffff; --tinta: #221b14; --suave: #6f6456; --linha: #e8dfcf;
  --destaque: #9a6a00; --sol: #8a3b12; --campo: #f4eee2; --tt: #0f7c86; --ig: #a0308f; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --fundo: #11141c; --papel: #1a1f2b; --tinta: #f3eee4; --suave: #a9a397;
    --linha: #2c3342; --destaque: #f0c45c; --sol: #f29a6b; --campo: #151a24; --tt: #4fd1dc; --ig: #e77bd6; }
}
:root[data-theme="dark"] { --fundo: #11141c; --papel: #1a1f2b; --tinta: #f3eee4; --suave: #a9a397;
  --linha: #2c3342; --destaque: #f0c45c; --sol: #f29a6b; --campo: #151a24; --tt: #4fd1dc; --ig: #e77bd6; }
"""


def pagina(destino):
    partes = {}
    for nome, trocas in TROCAS.items():
        texto = open(os.path.join(os.path.dirname(CORTES), nome), encoding="utf-8").read()
        for velho, novo in trocas:
            if velho not in texto:
                raise SystemExit(f"a página do Leonida mudou: não achei em {nome}: {velho[:70]}")
            texto = texto.replace(velho, novo)
        partes[os.path.basename(nome)] = texto
    guia = "".join(
        f'<section><h3>{html.escape(t)}</h3><ul>{"".join(f"<li>{html.escape(i)}</li>" for i in itens)}</ul></section>'
        for t, itens in GUIA)
    doc = (partes["pauta.html"].replace("/*CSS*/", partes["pauta.css"] + PALETA)
           .replace("/*JS*/", partes["pauta.js"]).replace("<!--GUIA-->", guia)
           .replace("Como postar em cada rede", "Como postar"))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    open(destino, "w", encoding="utf-8").write(doc)
    return destino
