# Criações do canal de fé e motivacional (v2: feita para segurar nos primeiros segundos)

Público: cristão geral (católicos e evangélicos) e motivacional. Voz B original (`vozes/vozes.json`),
gerada frase a frase com `../piloto/gerar.py`. Sai **sem música**: o som em alta do TikTok entra na postagem.

## O que segura a pessoa no começo
- **Quadro 0 já é o vídeo.** Sem tela preta nem fade: a voz começa na primeira palavra e o gancho está escrito
  gigante na tela (fonte Anton, palavra-chave em amarelo). O quadro 0 é também a capa no feed, por isso
  ele fica sem flash.
- **Soco de abertura.** Zoom de impacto, tremida e estrondo grave no primeiro plano, repetidos nas viradas
  da história ("Tá aqui.", "E Jesus... dormindo.", "Levanta.").
- **Gancho de curiosidade ou confronto** nos primeiros 2 segundos: "Esse vídeo não chegou até você por acaso",
  "O barco estava afundando", "Ninguém vai vir te salvar".
- **Ritmo:** pausas de 0,3 s, troca de plano a cada 1,5 a 3 s, com som de passagem (whoosh) em cada troca.
- **Palavra de impacto:** frases curtas aparecem uma palavra por vez, em tela cheia.
- **Versículo real com referência,** em serifa dourada, com a imagem escurecida e um brilho sonoro.
- **Final com pedido de ação:** comentar ("digita amém", "escreve: eu creio") ou salvar o vídeo.
- **Acabamento:** cor dramática, vinheta e grão de filme.

## Roteiros
- `nao-e-por-acaso.json`: fé, mensagem direta (Jeremias 29:11).
- `tempestade-v2.json`: fé, história bíblica (Marcos 4:38-39).
- `ninguem-vai-vir.json`: motivacional.

O que cada campo faz está documentado no começo de `montar.py`. Para montar:

```
python montar.py nao-e-por-acaso.json <pasta com fala/1.wav, 2.wav...>
```

## Material
- `sfx/`: efeitos sintetizados aqui mesmo com o ffmpeg (estrondo, whoosh, brilho, subida). Não têm direitos de terceiros.
- `img/`: pinturas em domínio público do Wikimedia Commons:
  - Rembrandt: *Cristo na tempestade*, *O retorno do filho pródigo*, *A ressurreição de Lázaro*;
  - Caspar David Friedrich: *O viajante sobre o mar de névoa*, *Mulher diante do sol poente*, *Nascer da lua no mar*;
  - Carl Bloch: *A ressurreição*, *Cristo e a criança*, *A transfiguração*;
  - Ivan Aivazovsky: *A nona onda*;
  - John Martin: *O grande dia da sua ira*;
  - Gustave Doré: *Jesus acalma a tempestade*;
  - Paul Delaroche: *Estudo para a cabeça de Cristo*.
