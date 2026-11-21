"""Acha os melhores momentos: picos de áudio (grito, risada, caos) + 'mais repetidos' do YouTube."""
import subprocess

import numpy as np

TAXA = 16000


def volume_por_segundo(caminho):
    """RMS do áudio por segundo, decodificado em mono 16 kHz pelo ffmpeg."""
    cmd = ["ffmpeg", "-v", "error", "-i", caminho, "-vn", "-ac", "1", "-ar", str(TAXA),
           "-f", "s16le", "-"]
    # lê em blocos de 1 minuto: uma live de 48h não cabe inteira na memória
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    rms = []
    while True:
        bruto = proc.stdout.read(TAXA * 2 * 60)
        n = len(bruto) // (TAXA * 2)
        if n == 0:
            break
        blocos = np.frombuffer(bruto[: n * TAXA * 2], dtype=np.int16).astype(np.float32) / 32768.0
        rms.append(np.sqrt((blocos.reshape(n, TAXA) ** 2).mean(axis=1)))
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg não conseguiu ler o áudio de {caminho}")
    return np.concatenate(rms) if rms else np.zeros(0)


def _z(x):
    dp = x.std()
    return (x - x.mean()) / dp if dp > 1e-9 else np.zeros_like(x)


def pontuar(rms, heatmap=None, peso_heatmap=1.0):
    """Nota por segundo. Valoriza volume alto e, principalmente, *subida* repentina de volume."""
    if len(rms) == 0:
        return rms
    db = 20 * np.log10(rms + 1e-6)
    suave = np.convolve(db, np.ones(5) / 5, mode="same")
    fundo = np.convolve(db, np.ones(61) / 61, mode="same")
    nota = _z(suave) + _z(suave - fundo)
    if heatmap:
        calor = np.zeros(len(rms))
        for h in heatmap:
            a, b = int(h["start_time"]), min(len(rms), int(h["end_time"]) + 1)
            calor[a:b] = h.get("value", 0)
        nota = nota + peso_heatmap * _z(calor)
    return nota


def escolher(nota, quantos=5, duracao=35, antes=8, ignorar_inicio=0):
    """Escolhe as `quantos` melhores janelas sem sobreposição.

    Cada corte começa `antes` segundos antes do pico, para dar contexto à reação.
    Retorna lista de (inicio, fim, nota) em ordem cronológica.
    """
    total = len(nota)
    if total == 0:
        return []
    duracao = min(duracao, total)
    janela = np.convolve(nota, np.ones(duracao) / duracao, mode="valid")  # média de cada janela
    livre = np.ones(len(janela), dtype=bool)
    livre[:ignorar_inicio] = False
    cortes = []
    while len(cortes) < quantos and livre.any():
        i = int(np.argmax(np.where(livre, janela, -np.inf)))
        pico = i + int(np.argmax(nota[i:i + duracao]))
        inicio = max(0, min(pico - antes, total - duracao))
        cortes.append((inicio, inicio + duracao, float(janela[i])))
        livre[max(0, inicio - duracao):inicio + duracao] = False
        livre[max(0, i - duracao):i + duracao] = False
    return sorted(cortes)
