"""Nota automática de qualidade de cada .wav (MOS estimado, STOI, PESQ, tom). Não substitui ouvir.
Uso: $FE_PY fe/avaliar.py fala1.wav fala2.wav ..."""
import sys, glob, torch, torchaudio
import torchaudio.functional as F
from torchaudio.pipelines import SQUIM_SUBJECTIVE, SQUIM_OBJECTIVE
subj = SQUIM_SUBJECTIVE.get_model(); obj = SQUIM_OBJECTIVE.get_model()
import soundfile as sf
def carrega(p):
    x, sr = sf.read(p, dtype="float32", always_2d=True)
    x = torch.from_numpy(x.T).mean(0, keepdim=True)
    return F.resample(x, sr, 16000)
ref = carrega(__import__("os").path.join(__import__("os").environ.get("FE_DIR", __import__("os").path.expanduser("~/.fe")), "VoiceStudio/backend/assets/samples/demo_voice.wav"))[:, :16000*8]
for p in sorted(sys.argv[1:]):
    x = carrega(p)
    with torch.no_grad():
        mos = subj(x, ref).item(); stoi, pesq, sisdr = [v.item() for v in obj(x)]
    f0 = F.detect_pitch_frequency(x, 16000, frame_time=0.02, freq_low=60, freq_high=400)
    f0 = f0[(f0 > 65) & (f0 < 390)]
    print(f"{p.split('/')[-1]:24} MOS estimado {mos:.2f} | STOI {stoi:.2f} PESQ {pesq:.2f} | F0 mediana {f0.median().item():.0f} Hz, variação {f0.std().item():.0f} Hz")
