# Plano incremental (profissional) – Lia Delivery

Objetivo: estabilizar agora e escalar depois, sem interromper operação.

## Fase 1 – Estabilidade imediata (sem mudar infra)
**Meta:** parar duplicidade e criar contexto persistente.

- **Idempotência por message_id**
  - Registrar IDs de mensagens e ignorar repetidas.
- **Histórico persistente**
  - Gravar mensagens (cliente e agente) em `n8n_historico_mensagens`.
- **Cardápio e stages sem client_id (temporário)**
  - Remover filtro por client_id para facilitar testes iniciais.
- **Lock do followup**
  - Evitar múltiplos followups quando há mais de uma instância.
- **Logs seguros**
  - Logar metadados (sem conteúdo sensível).

**Você faz:** aplicar migration no Supabase + deploy no EasyPanel.

---

## Fase 2 – Escala e performance
**Meta:** separar recepção e processamento.

- **Webhook só enfileira**
- **Worker processa e responde**
- **Debounce real com Redis**

**Você faz:** subir Redis + worker no EasyPanel.

---

## Fase 3 – Observabilidade
**Meta:** monitorar e prever problemas.

- Métricas básicas (volume, erros, duplicidade)
- Alertas simples

**Você faz:** configurar painel de métricas.

---

## Notas operacionais
- Ative logs de diagnóstico por env (sem texto das mensagens).
- Atualize envs conforme cada fase.
