# Piloto do segmento de fé (canal separado do Clipes Leonida)

Rascunho de 24/11/2026, ainda sem produção automática. Os caminhos apontam para `/home/user/voz`,
a pasta de trabalho onde o piloto foi montado.

- `gerar.py`: narração com o OmniVoice, o motor de voz do VoiceStudio (github.com/debpalash/VoiceStudio).
  Ambiente: `python -m venv venv`, `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`,
  `pip install "transformers>=5.10.0" accelerate pydub numpy soundfile audioop-lts`, e
  `PYTHONPATH=<clone do VoiceStudio>`. O modelo (3 GB) baixa do Hugging Face na primeira vez. Sem GPU,
  cada segundo de áudio leva uns 6 a 10 segundos.
- `avaliar.py`: nota automática de qualidade de cada voz (não substitui ouvir).
- `montar.py`: junta as frases com pausas, legenda palavra a palavra, planos e trilha.
- Imagens: pinturas em domínio público do Wikimedia Commons e dois vídeos do Mixkit (licença gratuita).
- Trilha: "At Rest", Kevin MacLeod (incompetech.com), CC BY 4.0. Exige crédito na legenda do post.
