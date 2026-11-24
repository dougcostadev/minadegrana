#!/usr/bin/env bash
# Monta o ambiente da produção do canal de fé numa máquina nova (uns 3 a 5 minutos).
# Uso: source fe/preparar.sh   -> deixa FE_PY (o python certo) e PYTHONPATH prontos.
set -e
FE_DIR="${FE_DIR:-$HOME/.fe}"
VS_COMMIT=202e2139814897a438541c707668e6ae90c159d2   # VoiceStudio testado (motor OmniVoice)
mkdir -p "$FE_DIR"
if [ ! -d "$FE_DIR/VoiceStudio/.git" ]; then
  git clone -q https://github.com/debpalash/VoiceStudio.git "$FE_DIR/VoiceStudio"
fi
git -C "$FE_DIR/VoiceStudio" fetch -q --depth 1 origin "$VS_COMMIT" 2>/dev/null || true
git -C "$FE_DIR/VoiceStudio" checkout -q "$VS_COMMIT" 2>/dev/null || echo "aviso: usando a versão atual do VoiceStudio"
if [ ! -x "$FE_DIR/venv/bin/python" ]; then
  python3 -m venv "$FE_DIR/venv"
  "$FE_DIR/venv/bin/pip" install -q --upgrade pip
  "$FE_DIR/venv/bin/pip" install -q torch==2.15.0 torchaudio==2.11.1 --index-url https://download.pytorch.org/whl/cpu
  "$FE_DIR/venv/bin/pip" install -q "transformers==5.24.0" "accelerate==1.16.0" "numpy==2.5.5" "soundfile==0.14.0" \
      "pydub==0.25.1" audioop-lts "faster-whisper==1.2.1"
fi
command -v ffmpeg >/dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg fonts-dejavu-core; }
export FE_PY="$FE_DIR/venv/bin/python"
export PYTHONPATH="$FE_DIR/VoiceStudio${PYTHONPATH:+:$PYTHONPATH}"
echo "ambiente pronto: $FE_PY"
