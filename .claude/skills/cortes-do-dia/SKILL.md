---
name: cortes-do-dia
description: Roda agora uma rodada de produção do canal Leonida Clipes — busca os clipes de GTA 6 que viralizaram nas últimas 24h nos canais acompanhados, avalia, monta os cortes verticais com gancho e textos de cada rede e coloca tudo na pauta de postagem. Use quando o usuário pedir "rodada", "cortes de hoje", "gera os cortes", "atualiza a pauta" ou algo parecido.
---

# Cortes do dia

Execute o roteiro completo de `AGENTE.md`, na raiz do repositório, do passo 1 ao 9, sem pedir
confirmação a cada etapa.

Ajustes que o usuário pode pedir ao chamar a skill:

- **quantidade**: o padrão é até 2 cortes por rodada; se ele pedir mais (por exemplo "5 cortes"),
  avalie mais prévias (até 4 por corte pedido) e mantenha a variedade de streamers.
- **período**: o padrão é só o conteúdo das últimas 24h (`--periodo dia`); se ele pedir "da
  semana" ou "reserva", use `--periodo semana` e feche o lote com `python -m cortes pacote`
  (sem `--rodada`), que espalha os cortes pelos próximos dias.
- **canais**: para acompanhar um streamer novo, acrescente a URL do canal (Twitch ou Kick) em
  `canais.txt` antes de montar a fila.

No fim, responda com a lista dos cortes que entraram e o link da pauta.
