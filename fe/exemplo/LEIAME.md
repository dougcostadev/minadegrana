# Exemplos do canal de fé e motivacional

Dois vídeos de exemplo, com 25 a 35 segundos cada, no formato combinado:

- narração com a **voz B original** (`vozes/vozes.json`), gerada frase a frase pelo OmniVoice (`../piloto/gerar.py`);
- gancho escrito na tela desde o primeiro quadro;
- legenda grande, palavra por palavra, com a palavra falada em amarelo;
- versículo real com referência, em serifa dourada;
- pintura em domínio público com zoom lento, trocando de plano a cada 2 ou 3 segundos;
- pedido de comentário ou de salvar o vídeo no final;
- **sem música.** O som em alta do TikTok entra na hora de postar.

Roteiros:

- `fe-tempestade.json`: mensagem de fé (tempestade, Marcos 4 e Isaías 43:2).
- `motivacional-escuro.json`: motivacional sem tema religioso.

Para montar um vídeo, gere as falas em `<pasta>/fala/1.wav, 2.wav...` e rode:

```
python montar.py fe-tempestade.json <pasta>
```

O roteiro aceita estes campos por frase:

- `foco`: onde fica o centro do recorte 9:16, de 0 a 1.
- `aperto`: o zoom do recorte (1 é a altura toda).
- `zoom`: in ou out.
- `corte`: um segundo enquadramento, que entra na palavra indicada.
- `estilo`: versiculo ou cta.

Para pôr trilha, adicione `"musica": {"arquivo": ..., "de": 0, "volume": 3}` ao roteiro.

Imagens em `img/`, todas pinturas em domínio público do Wikimedia Commons:

- Rembrandt, *Cristo na tempestade no mar da Galileia* (1633);
- Rembrandt, *O retorno do filho pródigo* (c. 1668);
- Caspar David Friedrich, *O viajante sobre o mar de névoa* (1818);
- Caspar David Friedrich, *Mulher diante do sol poente* (c. 1818).
