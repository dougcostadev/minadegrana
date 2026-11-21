"""Legendas automáticas (opcional): transcreve com faster-whisper e gera .ass estilo shorts."""


def _t(s):
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def gerar_ass(video, destino, y_px, idioma="pt", modelo="small", palavras_por_bloco=3):
    """Cria o .ass com blocos curtos de palavras. Retorna False se o whisper não estiver instalado."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return False
    segmentos, _ = WhisperModel(modelo, compute_type="int8").transcribe(
        video, language=idioma, word_timestamps=True)
    palavras = [p for s in segmentos for p in (s.words or [])]
    linhas = []
    for i in range(0, len(palavras), palavras_por_bloco):
        bloco = palavras[i:i + palavras_por_bloco]
        texto = "".join(p.word for p in bloco).strip().upper().replace("{", "").replace("}", "")
        linhas.append(f"Dialogue: 0,{_t(bloco[0].start)},{_t(bloco[-1].end)},P,,0,0,0,,{texto}")
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
