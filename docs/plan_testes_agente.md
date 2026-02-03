Plano de Implementacao de Testes do Agente
=========================================

Objetivo
--------
Garantir que o agente funcione com alta confiabilidade usando testes automatizados,
replay de historicos reais e testes E2E controlados no WhatsApp.

Escopo
------
1) Unit + Integracao (local)
2) Replay de historico real (staging)
3) E2E controlado (WhatsApp de teste)
4) Teste de carga/volume (staging)

Regras de Seguranca (sempre ativas em testes)
--------------------------------------------
- SAIPOS_DRY_RUN=true (nao enviar para Saipos)
- FOLLOWUP_ENABLED=false (evitar mensagens automaticas)
- Usar banco/instancia de staging quando possivel
- Nao usar numero real de clientes em testes E2E
- Registrar logs/CSV para auditoria

Fase 0 - Preparacao do Ambiente
-------------------------------
1) Criar ambiente de staging com as mesmas variaveis do prod
2) Garantir SAIPOS_DRY_RUN=true e FOLLOWUP_ENABLED=false
3) Confirmar acesso ao banco (staging)
4) Confirmar chaves de OpenAI e Google Maps (staging)
5) Garantir que o Evolution esta apontando para instancia de teste

Fase 1 - Testes Automatizados (Local)
-------------------------------------
Objetivo: validar regressao rapida.

Passos:
1) Rodar testes locais:
   - python3 -m pytest -q
2) Corrigir falhas antes de prosseguir para staging.

Saidas:
- Relatorio simples (PASS/FAIL)

Fase 2 - Preparar Historico Real (Replay)
-----------------------------------------
Objetivo: transformar historico real em dados reprodutiveis.

Passos:
1) Exportar conversas do WhatsApp (Marcio Lanches & Pizzas).
2) Sanitizar dados sensiveis (telefone, nome, endereco).
3) Converter para JSON padrao (exemplo abaixo).

Formato recomendado do JSON:
[
  {
    "session_id": "teste_0001",
    "messages": [
      {"ts": "2026-02-03T11:59:00Z", "text": "Quero fazer um pedido"},
      {"ts": "2026-02-03T11:59:03Z", "text": "1 X galinha com bacon"}
    ]
  }
]

Fase 3 - Replay de Historico (Staging)
--------------------------------------
Objetivo: rodar conversas reais em volume sem atingir clientes reais.

Passos:
1) Criar um script de replay que envie mensagens para o endpoint /v3.1.
2) Salvar todas as respostas do agente em CSV/JSON.
3) Rodar por lotes: 50, 200, 500, 1000 conversas.

Medidas:
- Taxa de sucesso por conversa
- Itens duplicados (nao pode)
- Pendencias resolvidas (>= 95%)
- Tempo medio ate finalizar pedido

Fase 4 - Teste de Carga / Volume
--------------------------------
Objetivo: garantir estabilidade em picos.

Passos:
1) Rodar 5-20 conversas simultaneas (replay concorrente).
2) Observar latencia e taxa de erro.
3) Ajustar timeouts e limites se necessario.

Fase 5 - E2E Controlado no WhatsApp
-----------------------------------
Objetivo: validar fluxo real com numero de teste.

Passos:
1) Usar apenas numeros internos/de teste.
2) Executar os cenarios abaixo manualmente.
3) Validar se o carrinho e o pedido final batem com o esperado.

Tabela de Cenarios (base)
-------------------------
Use a tabela abaixo como checklist e copie para planilha.

| ID | Cenario | Entrada resumida | Esperado |
|----|---------|------------------|----------|
| 01 | Pedido simples | 1 item | Interpreta, salva carrinho, confirma |
| 02 | Adicional | item + adicional | adicional separado e precificado |
| 03 | Observacao | item + observacao | observacao salva em "observacoes" |
| 04 | Multi-mensagens | itens em varias msgs | interpreta como um pedido |
| 05 | Item nao encontrado | item fora do cardapio | pede confirmacao de sugestao |
| 06 | Confirmacao "sim" | apenas "sim" | adiciona somente pendencias |
| 07 | Rejeicao sugestao | "nao, quero X" | pede nova correcao |
| 08 | Alteracao depois | "adiciona X" | atualiza carrinho sem duplicar |
| 09 | Entrega | "entrega" | salva tipo_entrega |
| 10 | Endereco completo | rua/numero/bairro | valida maps e confirma |
| 11 | Endereco incompleto | sem numero | pede novamente |
| 12 | Fora da cidade | endereco fora | informa erro e pede outro |
| 13 | Cartao | "cartao" | salva pagamento |
| 14 | Dinheiro + troco | "troco p/ 100" | salva troco_para |
| 15 | PIX texto | "pix" | solicita comprovante |
| 16 | PIX imagem | envia imagem | valida comprovante |
| 17 | Cliente cadastrado | cliente existente | usa nome e endereco |
| 18 | Pedido anterior | cliente com historico | oferece repetir |
| 19 | Cancelamento | "cancela" | cancela e limpa carrinho |
| 20 | Silencio | sem resposta | followup se habilitado |

Critérios de Aprovacao (Go/No-Go)
---------------------------------
- 0% de duplicacao de itens
- 95%+ das pendencias resolvidas corretamente
- 0% de erros 4xx/5xx em replay
- 100% dos cenarios criticos (01-10, 13-16) aprovados

Relatorio Final
---------------
1) Resumo de resultados por fase
2) CSV com conversas reprovadas
3) Lista de correcoes pendentes (se houver)

Checklist Rapido (por ordem)
----------------------------
[ ] Ambiente staging pronto e seguro
[ ] Testes locais OK
[ ] Historico convertido em JSON
[ ] Replay por lotes executado
[ ] Teste de carga executado
[ ] E2E no WhatsApp validado
[ ] Go/No-Go aprovado
