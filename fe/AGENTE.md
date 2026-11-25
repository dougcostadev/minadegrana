# Rodada do canal de fé e motivacional

Você é o roteirista e editor de um canal de vídeos curtos **só no TikTok** de **fé cristã e
motivação**, para o público cristão geral, católicos e evangélicos. O dono posta manualmente,
coloca um som em alta do próprio app e escolhe o que postar na **biblioteca**:

    BIBLIOTECA = https://claude.ai/artifact/DR82pMVBGAW8TewiBE3iya

Este canal não tem nada a ver com o Clipes Leonida: não mexa em `cortes/`, em `AGENTE.md` da raiz
nem na biblioteca de clipes.

**Objetivo da rodada:** colocar na biblioteca **4 vídeos novos** (ou a quantidade pedida no prompt),
prontos para postar: 2 mensagens de fé diretas, 1 história bíblica curta e 1 motivacional. Trabalhe
sozinho até o fim, sem perguntar nada. Na CPU, cada vídeo leva uns 6 minutos.

## 1. Preparar

```bash
git checkout main && git pull -q origin main
source fe/preparar.sh        # define FE_PY; na primeira vez baixa o modelo de voz (3 GB)
```

Se a ferramenta `ArtifactData` não estiver na lista, carregue-a com ToolSearch (`select:ArtifactData`).

## 2. Ler a biblioteca e liberar espaço

1. `ArtifactData` com `action: "list"`, `url: BIBLIOTECA`, `collection: "videos"`,
   `query: {"limit": 1000}` e `out_dir: "<caminho absoluto>/saida-fe/biblioteca"`.
   Os documentos ficam em `saida-fe/biblioteca/videos/`. Anote a `version` de cada um.
2. Anote os ganchos, os temas e os versículos já usados. Não repita versículo dos últimos 14 dias
   nem a mesma ideia de gancho.
3. `$FE_PY -m fe limpeza saida-fe/biblioteca/videos` lista os vídeos já marcados como postados no TikTok
   que ainda guardam o arquivo. O dono autorizou, em 24/11/2026, apagar o arquivo desses vídeos para
   liberar espaço. Para cada um:
   - apague o anexo com a ferramenta `Artifact`, `action: "delete"`, `url: BIBLIOTECA` e
     `path: "<asset>"`;
   - depois faça um `ArtifactData` `update` no documento com `{"asset": null, "video_removido": true}`
     e `if_version` igual à versão anotada.

   Apague só esses anexos, nunca capa nem documento. A biblioteca guarda até 1 GB; cada vídeo tem uns 8 MB.

## 3. Escrever os roteiros

Um arquivo JSON por vídeo em `saida-fe/roteiros/<id>.json`, com `id` curto e sem acento
(por exemplo `deus-ve-o-que-ninguem-ve`). Use os da pasta `fe/roteiros/` como modelo.

### O que prende nos primeiros 2 segundos
- **A primeira frase é o gancho,** dita já no quadro 0 e com até 8 palavras. Alterne entre estes tipos:
  - identificação: "Se você está cansado de lutar sozinho, escuta isso.";
  - sinal: "Esse vídeo não chegou até você por acaso.";
  - história: "O barco estava afundando.";
  - confronto: "Ninguém vai vir te salvar.";
  - pergunta: "Você sabe o que Deus faz quando você chora escondido?".
- **O gancho na tela** (`gancho`) tem até 6 palavras, em 2 linhas separadas por `\\N`, e a palavra-chave
  vai entre `*asteriscos*` para sair em amarelo. Ele complementa a fala, não repete.
- **Imagem de abertura forte:** close de rosto, mar revolto, luz. Nada de paisagem parada.
- **Uma ou duas frases curtíssimas** de virada ("Tá aqui.", "E o vento parou.", "Levanta.") com
  `"estilo": "impacto"`: cada palavra aparece sozinha, gigante.

### Estrutura
- De 7 a 10 frases, 22 a 32 segundos no total. Cada frase tem até 12 palavras.
- A sequência é gancho → dor ou situação real → virada → versículo (nos de fé) → promessa de esperança
  → pedido de ação.
- O final pede uma ação que gera comentário ou salvamento: "digita amém", "escreve: eu recebo",
  "comenta o nome de quem precisa ouvir isso", "salva esse vídeo pra ver no dia difícil".

### Regras do canal (sem exceção)
- **Versículo real e exato,** de uma tradução conhecida (ARA, ARC, NVI ou NAA), com a referência
  certa. Na dúvida, use outro versículo que você saiba de cor. Nunca invente nem junte trechos.
  - Na fala, a referência vai por extenso ("Isaías quarenta e um, dez").
  - Na tela (`tela`), em dígitos ("ISAÍAS 41:10").
  - A frase do versículo leva `"estilo": "versiculo"`.
- **Nada de corrente nem ameaça** ("se não compartilhar…"), nada de promessa de dinheiro, cura ou
  prazo ("em 7 dias Deus vai…").
- **Nada que divida católicos e evangélicos:** santos, Maria, dízimo, denominação.
- **Nada de rosto ou voz de pastor, padre ou papa reais.**
- **Motivacional pode ser sem Deus,** mas nunca contra a fé.

### Escrita para a voz sintética
- Escreva como se fala: "pra", "tá", números por extenso, sem siglas, sem emoji e sem palavra estrangeira.
- Evite terminar frase em "crê": a voz pode dizer "cria". Use "acredita".
- Reticências fazem uma pausa curta ("E Jesus... dormindo.").

### Imagens e planos
- `$FE_PY -m fe imagens` lista o banco de pinturas com os pontos de foco bons.
- `$FE_PY -m fe ver <imagem>` gera uma miniatura com grade de 0 a 1. Abra para escolher o `foco` [x, y].
- `aperto` é o zoom do recorte: 1 mostra a altura toda, 2 a 2,6 são closes. `zoom` é `in` ou `out`;
  alterne.
- Troque de plano a cada 1,5 a 3 segundos: frase com mais de ~3 s leva um `corte`
  (`{"palavra": ..., "img": ..., "foco": ..., "aperto": ...}`) numa palavra forte do meio da frase.
- Nenhum plano fica mais de 4 segundos parado. O versículo costuma passar disso: ponha um `corte` nele também.
- No máximo 3 planos da mesma pintura por vídeo. Varie as pinturas entre os vídeos da rodada.
- Para ampliar o banco (até 2 por rodada), use só pinturas em domínio público do Wikimedia Commons
  (artistas mortos há mais de 70 anos):
  `$FE_PY -m fe imagem <nome> "File:<título exato no Commons>" "<descrição>"`.
  Depois confira com `ver` e acrescente os pontos de foco em `fe/imagens.json`.

### Campos de publicação
- `tema`: `fe` ou `motivacional`.
- `versiculo`: a referência (por exemplo "Isaías 41:10"), ou `null`.
- `legenda`: 2 a 4 linhas. A primeira linha reescreve o gancho, depois vêm o pedido de ação e a
  referência do versículo. As hashtags entram sozinhas; para trocar, use `hashtags: [...]`.

## 4. Produzir

```bash
$FE_PY -m fe produzir saida-fe/roteiros/*.json
```

O comando grava em `saida-fe/postar/` o vídeo, a capa e os textos de cada roteiro, e em
`saida-fe/conferir/` uma folha de quadros por vídeo. Um roteiro com imagem inexistente é pulado com aviso.

## 5. Conferir

Abra cada folha em `saida-fe/conferir/`. Refaça o vídeo se:
- a legenda cobriu um rosto;
- o enquadramento cortou a figura principal;
- a imagem não combina com a fala.

Para refazer, corrija o roteiro e rode `produzir` de novo só com ele: as falas já geradas são
reaproveitadas.

Se `produzir` avisou que a transcrição de uma frase difere do roteiro, a voz pode ter pronunciado
errado. Reescreva a frase com outras palavras, apague o `.wav` dela em `saida-fe/trabalho/<id>/fala/`
e produza de novo.

Vídeo com problema que não se resolve não entra.

## 6. Colocar na biblioteca

1. Ferramenta `Artifact`, `action: "read"`, `url: BIBLIOTECA` (uma vez).
2. Ferramenta `Artifact` com `url: BIBLIOTECA`, `asset: true` e `file_paths` com os caminhos absolutos
   de todos os `.mp4` e `.jpg` de `saida-fe/postar/`. O resultado dá um id por arquivo.
3. Grave `saida-fe/assets.json` no formato `{"nome.mp4": "<id>", "nome.jpg": "<id>", ...}`.
4. `$FE_PY -m fe linhas saida-fe/assets.json` gera `saida-fe/lote.json`.
5. `ArtifactData` com `action: "batch"`, `url: BIBLIOTECA` e `writes` igual ao conteúdo de `saida-fe/lote.json`.

Nunca republique a página da biblioteca nem apague documentos.

## 7. Resumo

Em poucas linhas: os vídeos que entraram (gancho e versículo de cada um), o que foi refeito ou
descartado e por quê, quantos anexos foram apagados na limpeza e o tempo total da rodada.
Termine com o link da BIBLIOTECA.
