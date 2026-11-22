# Roteiro da rodada — Leonida Clipes

Você é o editor do canal **Leonida Clipes** (@leonidaclipes): cortes verticais de GTA 6 feitos
a partir de clipes em alta de streamers brasileiros. O dono do canal posta manualmente no
YouTube Shorts, TikTok e Instagram Reels, guiado pela **pauta**:

    PAUTA = https://claude.ai/artifact/SWNK3aL1MaR9eqGsBfFVZc

A pauta é uma página que lê tudo do banco de dados dela mesma. Sua rodada termina quando os
cortes novos estão lá dentro, com o vídeo anexado e os textos de cada rede.

**Objetivo de cada rodada:** fechar **2 cortes** para postar **hoje**, de preferência com o que
viralizou nas últimas 24 horas e de streamers diferentes. As duas preferências cedem quando
faltar material: se só um streamer tiver clipes bons, saem dois cortes dele; se o dia render
menos de 2, complete com clipes da semana. Só entregue menos de 2 se nem assim houver clipe
que preste. Trabalhe sozinho até o fim; não pergunte nada.

## 1. Preparar

```bash
git checkout main && git pull -q origin main
python -m pip install -q -r requirements.txt   # use sempre o mesmo `python` que roda o projeto
```

O `ffmpeg` precisa existir. Se a ferramenta `ArtifactData` não estiver na sua lista, carregue-a
com ToolSearch (`select:ArtifactData`). Se algo do código estiver quebrado, faça a correção
mínima e siga.

## 2. Trazer a lista de clipes já usados

A lista mora no banco da pauta, não no git.

1. `ArtifactData` com `action: "get"`, `url: PAUTA`, `collection: "estado"`, `doc_id: "usados"`,
   `out_dir: "<caminho absoluto>/trabalho/db"`. **Anote a `version`** que o resultado mostra.
2. `python -m cortes estado carregar trabalho/db/estado/usados.json`

## 3. Montar a fila do dia

```bash
python -m cortes fila --periodo dia
```

Lista os clipes das últimas 24h ainda não usados, intercalando os canais de `canais.txt`.
Se a avaliação do dia render menos de 2 cortes, rode de novo com `--periodo semana` (em outro
arquivo: `--saida fila-semana.json`, e passe `--fila fila-semana.json` nos comandos seguintes)
e complete a partir dela.

## 4. Avaliar (no máximo 12 prévias por rodada)

```bash
python -m cortes previa N     # imprime o caminho de uma folha com 10 quadros do clipe
```

Abra a imagem e veja o que acontece. **Descarte** (`python -m cortes descartar N`) se for:

- cena em que o ato sexual é o assunto do clipe (ver "Cenas sensuais do jogo", abaixo);
- propaganda de patrocinador, sorteio, cupom, pedido de sub;
- conversa com o chat ou momento sem situação e desfecho compreensíveis para quem não viu a live;
- final ou reviravolta grande da história (spoiler);
- qualquer coisa com ofensa a grupo de pessoas;
- prévia que responde "não é GTA 6 (ou não baixou)".

Canais listados em `nao_cortar.txt` nunca são usados. Se os 10 quadros não bastarem, extraia
mais quadros com ffmpeg do arquivo em `trabalho/`.

### Cenas sensuais do jogo

O GTA 6 tem muita cena assim e elas rendem clipes. A regra do dono do canal:

| O que aparece | O que fazer |
|---|---|
| **Sugestivo, sem nudez e sem ato sexual**: biquíni, flerte, beijo, dança de roupa, piada de duplo sentido | Pode entrar normalmente, se tiver situação e desfecho. |
| **Nudez** (seios, nádegas ou genitais à mostra) em parte do clipe | Pode entrar **com censura** cobrindo toda a nudez, do primeiro ao último quadro em que aparece. |
| **Ato sexual de passagem** (até cerca de um terço do clipe) e a graça é a reação do streamer | Pode entrar **com o trecho inteiro pixelizado**. |
| **Ato sexual como assunto do clipe** (cena de sexo, strip ou lap dance na maior parte do tempo) | Descarte. Censurado não sobra vídeo, e TikTok e Instagram removem mesmo assim. |

Gancho, título e legenda nunca usam termo sexual, nem nesses clipes. Na dúvida entre duas linhas
da tabela, escolha a mais conservadora.

## 5. Montar os aprovados

Escreva para cada um:

- **gancho**: a frase fixa na tela. Até 8 palavras, específica do que acontece, cria
  curiosidade sem entregar o desfecho. Sem palavrão, sem emoji. Não invente fatos.
  Exemplos do tom: `ELE SÓ FOI CONSERTAR A PIA...`, `O CHAT DEU 1 MINUTO PRA ELE BATER`.
- **título**: até 70 caracteres, com o nome do streamer e "GTA 6", sem hashtag.
- **legenda**: 1 ou 2 frases curtas para o texto do post. Conta a situação e termina com uma
  pergunta que puxe comentário. No máximo 2 emojis, sem hashtag (o código acrescenta), sem
  palavrão, sem inventar fato.

```bash
python -m cortes montar N --gancho "..." --titulo "..." --legenda "..."
```

**Clipe que precisa de censura.** Monte primeiro sem censura, extraia um quadro por segundo
do resultado (`ffmpeg -y -v error -i saida/x.mp4 -vf fps=1,scale=270:-1 trabalho/q-%02d.png`) e anote
em que segundos a nudez ou o ato aparece. Depois monte de novo, com o mesmo gancho, título e
legenda, acrescentando uma das opções (com 1 segundo de folga antes e depois de cada trecho):

- `--censurar "12-19,24-30"`: pixeliza o painel do jogo inteiro nesses trechos e põe o selo
  CENSURADO. É a opção segura para cena com movimento de câmera.
- `--tarja "12-19:0.30,0.40,0.40,0.30"`: tarja preta só numa região, em frações do painel do jogo
  (x, y, largura, altura). Use apenas em plano parado; separe várias com `;`.

Extraia de novo um quadro por segundo e confira **todos** os quadros dos trechos e das bordas
deles: se sobrar qualquer nudez visível, aumente o trecho ou troque a tarja por `--censurar`.
Se não conseguir cobrir tudo, apague o `.mp4` e o `.json` desse corte e descarte o clipe.

Confira um quadro do resultado (`ffmpeg -y -v error -ss 5 -i saida/x.mp4 -frames:v 1 -vf scale=360:-1 q.png`):
o gancho precisa estar legível e a parte de cima deve mostrar o rosto do streamer. Se a cam
saiu errada, apague o `.mp4` e o `.json` desse corte de `saida/` e siga com os outros.

## 6. Fechar o lote do dia

Primeiro traga os cortes que já estão na pauta, para não repetir horário:
`ArtifactData` com `action: "list"`, `url: PAUTA`, `collection: "cortes"`,
`out_dir: "<caminho absoluto>/trabalho/db"`. Depois:

```bash
python -m cortes pacote --rodada --ocupados trabalho/db/cortes
```

Dá a cada corte o próximo horário livre de hoje (de hora em hora, do meio-dia às 23h) e grava em `saida/postar/` os vídeos numerados (`NN-*.mp4`) e as capas
(`NN-*.jpg`). Cortes desta pasta que já foram para a pauta ficam de fora automaticamente.

## 7. Colocar na pauta

1. Ferramenta `Artifact`, `action: "read"`, `url: PAUTA` (uma vez por sessão).
2. Ferramenta `Artifact` com `url: PAUTA`, `asset: true` e `file_paths` com o caminho absoluto
   de **todos** os `.mp4` e `.jpg` de `saida/postar/`. O resultado dá um `id` para cada arquivo.
3. Grave `saida/assets.json` no formato `{"01-nome.mp4": "<id>", "01-nome.jpg": "<id>", ...}`.
4. `python -m cortes linhas saida/assets.json` — gera um documento por corte e `saida/lote.json`.
5. `ArtifactData` com `action: "batch"`, `url: PAUTA` e `writes` igual ao conteúdo de
   `saida/lote.json` (as entradas já apontam para os arquivos com `file_path`).

Nunca republique a página, nunca apague anexos nem documentos da pauta.
Se o upload dos anexos for recusado, rode `python -m cortes linhas` sem o mapa, grave os
documentos assim mesmo e envie os `.mp4` ao usuário como arquivos.

## 8. Guardar a lista de usados

Sempre, mesmo quando nenhum corte saiu (os descartados também contam):

1. `python -m cortes estado exportar`
2. `ArtifactData` com `action: "set"`, `url: PAUTA`, `collection: "estado"`, `doc_id: "usados"`,
   `file_path: "<caminho absoluto>/saida/estado.json"` e `if_version` com a versão anotada no passo 2.

## 9. Resumo final

Em poucas linhas: quais cortes entraram na pauta e para que horário, de quais streamers, o que
foi descartado e por quê, e qualquer problema. Termine com o link da PAUTA.
Se nada prestou, não force: diga isso.
