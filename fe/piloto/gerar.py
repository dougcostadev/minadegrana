"""Gera narrações com o OmniVoice (motor do VoiceStudio), carregando o modelo uma vez só."""
import json, sys, time
import torch
from omnivoice.models.omnivoice import OmniVoice
from omnivoice.utils.audio import save_audio

_m = None
def modelo():
    global _m
    if _m is None:
        _m = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32, allow_tokenizer_fallback=True)
    return _m

def falar(texto, saida, instruct=None, ref_audio=None, ref_text=None, speed=0.85, num_step=16, semente=7):
    torch.manual_seed(semente)
    m = modelo()
    a = m.generate(text=texto, language="pt", instruct=instruct, ref_audio=ref_audio, ref_text=ref_text,
                   speed=speed, num_step=num_step)
    save_audio(saida, a[0], m.sampling_rate)
    return saida

if __name__ == "__main__":
    for t in json.load(open(sys.argv[1], encoding="utf-8")):
        t0 = time.time()
        falar(**t)
        print(t["saida"], round(time.time() - t0), "s", flush=True)
