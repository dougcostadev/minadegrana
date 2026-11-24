# minadegrana — fábrica de cortes de GTA 6

Pega vídeos/lives de GTA 6 do YouTube, acha os melhores momentos e gera cortes
verticais (1080x1920) com a **facecam em cima e o gameplay embaixo**, prontos para
Shorts / TikTok / Reels.

## Instalar

```bash
pip install -r requirements.txt      # precisa também do ffmpeg instalado
pip install faster-whisper           # opcional: legendas automáticas
```

## Usar

```bash
# 1. Ver quais canais e vídeos de GTA 6 estão em alta (gera candidatos.json)
python -m cortes descobrir

# 2. Gerar cortes de um ou mais vídeos
python -m cortes cortar "https://www.youtube.com/watch?v=ID" --quantos 5 --duracao 35 --legendas

# também funciona com arquivo local
python -m cortes cortar gravacao.mp4 --quantos 3
```

Cada corte sai em `saida/` como `.mp4` + um `.json` com título, descrição (com
crédito e link do original no minuto exato), nota do momento e posição da cam.

Opções úteis de `cortar`:

| opção | para quê |
|---|---|
| `--cam x:y:w:h` | informa a posição da webcam quando a detecção automática errar |
| `--sem-cam` | vídeo sem facecam: gameplay centralizado sobre fundo desfocado |
| `--ignorar-inicio N` | pula os N primeiros segundos (tela de espera da live) |
| `--legendas` | transcreve e queima legendas estilo shorts |

## Clipes em alta (Twitch e Kick)

O caminho principal para canais da Twitch e da Kick: em vez de adivinhar o momento pelo
áudio, pega os **clipes mais vistos feitos pelos espectadores** — momentos que já provaram
que chamam atenção — e monta o vertical com um **gancho fixo na tela**, na divisória entre
a cam e o gameplay.

```bash
python -m cortes clipes https://www.twitch.tv/alanzoka --periodo semana            # só lista
python -m cortes clipes https://www.twitch.tv/alanzoka --periodo semana --gerar 3  # gera os 3 mais vistos
```

Com `ANTHROPIC_API_KEY` no ambiente, o Claude vê quadros do clipe e a transcrição, escreve
um gancho específico ("ELE SÓ FOI CONSERTAR A PIA...") e reprova clipe sem contexto,
propaganda, sorteio, cena de sexo do jogo e spoiler do final. Sem a chave, o gancho é o
título que o espectador deu ao clipe, quando ele presta, e um filtro por palavras barra o
resto.

## Biblioteca de clipes

A biblioteca é uma página (um Artifact do Claude) com todos os cortes prontos: capa, vídeo
para baixar e os textos de YouTube Shorts, TikTok e Instagram Reels. Não há agenda: quem posta
escolhe o que, quando e onde, e marca na página onde cada corte já saiu. Ela lê tudo do banco
de dados dela mesma, então cada rodada só acrescenta dados:

```bash
python -m cortes fila --periodo dia   # clipes das últimas 24h de todos os canais de canais.txt
python -m cortes previa 3             # folha de quadros do clipe 3, para avaliar
python -m cortes montar 3 --gancho "..." --titulo "..." --legenda "..."
python -m cortes pacote               # vídeos e capas em saida/postar/
python -m cortes linhas saida/assets.json   # documentos do banco, depois de anexar os vídeos
```

`python -m cortes pagina` monta a página (`saida/pauta.html`) quando o layout muda.
A lista de clipes já usados fica no documento `estado/usados` do mesmo banco
(`python -m cortes estado carregar|exportar`). `python -m cortes canal` lista os Shorts
públicos do canal com as views.

O roteiro completo de uma rodada está em `AGENTE.md`; a skill `/cortes-do-dia` executa esse
roteiro sob demanda, e uma tarefa agendada o executa três vezes por dia.

## Automático (GitHub Actions)

O workflow `.github/workflows/cortes.yml` roda 2x por dia: pega os clipes mais vistos do
dia nos canais de `canais.txt`, gera até 3 cortes com gancho e publica no YouTube. Os cortes também ficam como artefato da execução
por 7 dias. O agendamento só vale depois que o workflow estiver na branch padrão.

Secrets do repositório (Settings → Secrets and variables → Actions):

| secret | de onde vem |
|---|---|
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET` | Google Cloud Console → projeto com *YouTube Data API v3* ativada → credencial OAuth do tipo "App para computador" |
| `YT_REFRESH_TOKEN` | rode `python -m cortes autorizar` na sua máquina (com as duas variáveis acima no ambiente) e faça login com a conta do canal |
| `ANTHROPIC_API_KEY` | chave da API do Claude (console.anthropic.com) — ganchos escritos por IA e triagem dos clipes |
| `YT_COOKIES` | conteúdo de um `cookies.txt` do YouTube — necessário se o YouTube bloquear o download a partir dos servidores do GitHub |

Sem os três primeiros, o workflow só gera os cortes e não publica. Os vídeos
sobem como **privados** por padrão; para publicar direto, crie a variável de
repositório `PRIVACIDADE` com o valor `public`.

## Como funciona

- **Melhores momentos** (`momentos.py`): volume do áudio por segundo — picos e
  subidas repentinas (grito, risada, explosão) — somado ao gráfico "mais
  repetidos" do YouTube quando o vídeo tem. O corte começa 8s antes do pico.
- **Download** (`pipeline.py`): baixa só o áudio para analisar e depois só os
  trechos escolhidos, não o VOD inteiro.
- **Facecam** (`facecam.py`): detecta rosto em ~40 frames e fica com a região
  onde ele aparece de forma estável (webcam não se mexe; rosto de NPC sim).
- **Render** (`render.py`): ffmpeg, 30 fps, áudio normalizado em -14 LUFS.

## Direitos e monetização

Cortar vídeo dos outros sem autorização rende strike de direitos autorais e o
YouTube nega monetização por "conteúdo reutilizado". Use canais que liberam
cortes (muitos streamers têm regra pública ou programa de clipadores), mantenha o
crédito que o `.json` já gera e edite o título/gancho de cada corte antes de postar.

## Canal de fé e motivacional (`fe/`)

Um segundo canal, separado dos Clipes Leonida: vídeos verticais de 22 a 32 s com narração na voz B
(OmniVoice, `vozes/vozes.json`), pinturas em domínio público com zoom lento, legenda palavra a
palavra e versículo real. Saem sem música, porque o som em alta entra na hora de postar.

```bash
source fe/preparar.sh                         # ambiente (torch CPU, motor de voz, whisper)
$FE_PY -m fe produzir fe/roteiros/*.json      # voz + vídeo + capa + textos em saida-fe/postar/
```

O roteiro de uma rodada (escrever roteiros, produzir, conferir e colocar na biblioteca do canal)
está em `fe/AGENTE.md`. Uma tarefa agendada executa esse roteiro uma vez por dia.
Na CPU, cada vídeo leva ~6 min: ~4,5 de voz e ~1 de montagem.
