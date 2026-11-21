"""Legendas automáticas (opcional): transcreve com faster-whisper e gera .ass estilo shorts."""
import subprocess

import numpy as np


def _t(s):
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def gerar_ass(video, destino, y_px, idioma=None, modelo="small", palavras_por_bloco=3):
    """Cria o .ass com blocos curtos de palavras (idioma detectado sozinho se não informado).

    Retorna False se o whisper não estiver instalado ou se não houver fala.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return False
    # decodifica com o ffmpeg (evita depender da versão do PyAV que o faster-whisper usa)
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "f32le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(bruto, dtype=np.float32)
    segmentos, _ = WhisperModel(modelo, compute_type="int8").transcribe(
        audio, language=idioma, word_timestamps=True, vad_filter=True)
    palavras = [p for s in segmentos for p in (s.words or [])]
    linhas = []
    for i in range(0, len(palavras), palavras_por_bloco):
        bloco = palavras[i:i + palavras_por_bloco]
        texto = "".join(p.word for p in bloco).strip().upper().replace("{", "").replace("}", "")
        fim = min(bloco[-1].end, bloco[0].start + 2.0)  # não deixa legenda parada na tela
        linhas.append(f"Dialogue: 0,{_t(bloco[0].start)},{_t(fim)},P,,0,0,0,,{texto}")
    cabecalho = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: P,DejaVu Sans,78,&H0000FFFF,&H00000000,&H80000000,1,1,6,2,8,60,60,{y_px}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(destino, "w", encoding="utf-8") as f:
        f.write(cabecalho + "\n".join(linhas) + "\n")
    return bool(linhas)
