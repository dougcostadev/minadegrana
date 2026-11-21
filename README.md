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
