"""Narração com a voz B (OmniVoice, motor do VoiceStudio), em lote e com o modelo carregado uma vez só.

Precisa do clone do VoiceStudio no PYTHONPATH (o pacote `omnivoice`); fe/preparar.sh monta o ambiente.
"""
import json, os, sys, time
import torch

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_m, _prompt = None, None
LOTE = int(os.environ.get("FE_LOTE", "1"))  # na CPU, uma frase por passada é o mais rápido (lote de 3: +22%, de 9: +36%)


def modelo():
    global _m
    if _m is None:
        from omnivoice.models.omnivoice import OmniVoice
        torch.set_num_threads(os.cpu_count() or 4)
        dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
        _m = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=dispositivo,
                                       dtype=torch.float16 if dispositivo == "cuda" else torch.float32,
                                       allow_tokenizer_fallback=True)
    return _m


def voz_b():
    """Prompt de clonagem da voz B, calculado uma vez (vozes/vozes.json)."""
    global _prompt
    if _prompt is None:
        v = json.load(open(os.path.join(RAIZ, "vozes", "vozes.json"), encoding="utf-8"))["motivacional"]
        _prompt = (modelo().create_voice_clone_prompt(ref_audio=os.path.join(RAIZ, v["ref_audio"]), ref_text=v["ref_text"]),
                   v["speed"])
    return _prompt


def falar_lote(textos, saidas, num_step=16, semente=7):
    """Gera cada texto em sua saída (.wav), em passadas de até LOTE frases; pula as saídas que já existem."""
    from omnivoice.utils.audio import save_audio
    pares = [(t, s) for t, s in zip(textos, saidas) if not os.path.exists(s)]  # fala já gerada é reaproveitada
    if not pares:
        return
    textos, saidas = [p[0] for p in pares], [p[1] for p in pares]
    m = modelo(); prompt, speed = voz_b()
    for i in range(0, len(textos), LOTE):
        tx, sa = textos[i:i + LOTE], saidas[i:i + LOTE]
        torch.manual_seed(semente)
        with torch.inference_mode():
            audios = m.generate(text=tx, language=["pt"] * len(tx), voice_clone_prompt=[prompt] * len(tx),
                                speed=[speed] * len(tx), num_step=num_step)
        for a, s in zip(audios, sa):
            os.makedirs(os.path.dirname(s), exist_ok=True)
            save_audio(s, a, m.sampling_rate)


if __name__ == "__main__":  # python fe/voz.py roteiro.json pasta  -> pasta/fala/1.wav, 2.wav...
    rot = json.load(open(sys.argv[1], encoding="utf-8")); pasta = sys.argv[2]
    t0 = time.time()
    falar_lote([f["texto"] for f in rot["frases"]], [f"{pasta}/fala/{i+1}.wav" for i in range(len(rot["frases"]))])
    print(len(rot["frases"]), "frases em", round(time.time() - t0), "s")
