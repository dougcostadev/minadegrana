"""Texto queimado no vídeo: gancho fixo (a frase que dá contexto) e legendas automáticas."""
import subprocess
import textwrap

import numpy as np


def _t(s):
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _limpo(texto):
    return texto.replace("{", "").replace("}", "").replace("\n", " ").strip()


def transcrever(video, idioma=None, modelo="small"):
    """Palavras com tempo [(inicio, fim, texto)], ou None se o faster-whisper não estiver instalado."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    # decodifica com o ffmpeg (evita depender da versão do PyAV que o faster-whisper usa)
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "f32le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(bruto, dtype=np.float32)
    segmentos, _ = WhisperModel(modelo, compute_type="int8").transcribe(
        audio, language=idioma, word_timestamps=True, vad_filter=True)
    return [(p.start, p.end, p.word) for s in segmentos for p in (s.words or [])]


def texto(palavras):
    return "".join(p[2] for p in palavras or []).strip()


def escrever_ass(destino, duracao, palavras=None, y_legenda=1200, gancho=None, y_gancho=540,
                 palavras_por_bloco=3, censura=None, y_censura=1200):
    """Gera o .ass (1080x1920). Retorna False se não houver nada para escrever."""
    linhas = []
    if gancho:
        quebrado = "\\N".join(textwrap.wrap(_limpo(gancho), 22)[:3])
        linhas.append(f"Dialogue: 1,{_t(0)},{_t(duracao + 1)},G,,0,0,{y_gancho},,{quebrado}")
    for ini, fim in censura or []:  # selo sobre o painel pixelizado
        linhas.append(f"Dialogue: 2,{_t(ini)},{_t(fim)},C,,0,0,{y_censura},,CENSURADO")
    palavras = palavras or []
    for i in range(0, len(palavras), palavras_por_bloco):
        bloco = palavras[i:i + palavras_por_bloco]
        fim = min(bloco[-1][1], bloco[0][0] + 2.0)  # não deixa legenda parada na tela
        fala = _limpo("".join(p[2] for p in bloco)).upper()
        if fala:
            linhas.append(f"Dialogue: 0,{_t(bloco[0][0])},{_t(fim)},P,,0,0,{y_legenda},,{fala}")
    if not linhas:
        return False
    cabecalho = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: P,DejaVu Sans,74,&H0000FFFF,&H00000000,&H80000000,1,1,6,2,8,60,60,0
Style: G,DejaVu Sans,62,&H00000000,&H00FFFFFF,&H00FFFFFF,1,3,18,0,8,50,50,0
Style: C,DejaVu Sans,70,&H00FFFFFF,&H00000000,&H00000000,1,3,22,0,8,50,50,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(destino, "w", encoding="utf-8") as f:
        f.write(cabecalho + "\n".join(linhas) + "\n")
    return True
