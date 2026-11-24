---
name: cortes-do-dia
description: Roda agora uma rodada de produção do canal Clipes Leonida — busca os clipes de GTA 6 que viralizaram nas últimas 24h nos canais acompanhados, avalia, monta os cortes verticais com gancho e textos de cada rede e coloca tudo na biblioteca de clipes. Use quando o usuário pedir "rodada", "mais clipes", "gera os cortes", "abastece a biblioteca" ou algo parecido.
---

# Cortes do dia

Execute o roteiro completo de `AGENTE.md`, na raiz do repositório, do passo 1 ao 9, sem pedir
confirmação a cada etapa.

Ajustes que o usuário pode pedir ao chamar a skill:

- **quantidade**: o padrão é o do roteiro (todos os aprovados, até 8 cortes por rodada); se ele
  pedir um lote maior (por exemplo "20 clipes"),
  monte a fila com `python -m cortes fila --periodo ambos --por-canal 8 --min-semana 120 --total 72`,
  avalie mais prévias (até 4 por corte pedido) e mantenha a variedade de streamers. Para lotes
  grandes, vale dividir a fila entre agentes em paralelo, cada um com uma fatia dos números.
- **período**: o padrão é começar pelo conteúdo das últimas 24h; "da semana" usa `--periodo semana`.
- **canais**: para acompanhar um streamer novo, acrescente a URL do canal (Twitch ou Kick) em
  `canais.txt` antes de montar a fila.

No fim, responda com a lista dos cortes que entraram e o link da biblioteca.
