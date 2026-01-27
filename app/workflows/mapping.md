# Mapping

## Workflow: 1. Lia_V3.1

- File: `n8n_workflows/1. Lia_V3.1.json`
- Python module: `app/workflows/1_lia_v3_1.py`
- Routes/Triggers:
  - `POST /v3.1` -> `app/routes/1_lia_v3_1.py::webhook_mensagem_recebida`
- Nodes:
  - Mensagem chegando? (n8n-nodes-base.filter, id: f3a917f8-b7d2-4769-aeb1-f4d9b303fedd) -> `app/workflows/1_lia_v3_1.py::node_mensagem_chegando`
  - Mensagem recebida (n8n-nodes-base.webhook, id: dc69fb75-17b4-4574-9d60-daded7b65374) -> `app/workflows/1_lia_v3_1.py::node_mensagem_recebida`
  - Mensagem encavalada? (n8n-nodes-base.code, id: 8fa19d54-ae6f-40d4-bcc2-549a1d157b65) -> `app/workflows/1_lia_v3_1.py::node_mensagem_encavalada`
  - Buscar mensagens (n8n-nodes-base.postgres, id: f5bb5b9c-0109-4906-9367-48df87c660d9) -> `app/workflows/1_lia_v3_1.py::node_buscar_mensagens`
  - Concatenar mensagens (n8n-nodes-base.set, id: c8d9ec83-6542-43ce-ad23-fa3e429428b5) -> `app/workflows/1_lia_v3_1.py::node_concatenar_mensagens`
  - Limpar fila de mensagens (n8n-nodes-base.postgres, id: a51493d4-efb0-4ba2-ae4c-606163a40c2f) -> `app/workflows/1_lia_v3_1.py::node_limpar_fila_de_mensagens`
  - Sticky Note2 (n8n-nodes-base.stickyNote, id: 4ccb67d7-5c10-482f-aa29-324532f71fc5) -> `app/workflows/1_lia_v3_1.py::node_sticky_note2`
  - Esperar (n8n-nodes-base.wait, id: 67043511-8db6-475a-bd66-f55d73ce0d7b) -> `app/workflows/1_lia_v3_1.py::node_esperar`
  - Sticky Note3 (n8n-nodes-base.stickyNote, id: e8126e5e-cbd4-446a-b520-4ae19782ed4b) -> `app/workflows/1_lia_v3_1.py::node_sticky_note3`
  - Sticky Note4 (n8n-nodes-base.stickyNote, id: e158c0f9-6e8b-4903-9813-a5c2adcdc5ca) -> `app/workflows/1_lia_v3_1.py::node_sticky_note4`
  - Sticky Note5 (n8n-nodes-base.stickyNote, id: daab215a-0aaf-44b5-bd92-5dadd39ff37e) -> `app/workflows/1_lia_v3_1.py::node_sticky_note5`
  - Tipo de mensagem (n8n-nodes-base.switch, id: d291e5e3-902c-4631-86be-9f9a1b93dfff) -> `app/workflows/1_lia_v3_1.py::node_tipo_de_mensagem`
  - Transcrever áudio (@n8n/n8n-nodes-langchain.openAi, id: 2b8ba7b0-f6d5-43b3-8b20-d880edfee428) -> `app/workflows/1_lia_v3_1.py::node_transcrever_audio`
  - Sticky Note6 (n8n-nodes-base.stickyNote, id: f02d2e6e-159b-4b2e-a2d4-0082d9613d98) -> `app/workflows/1_lia_v3_1.py::node_sticky_note6`
  - Resetar status (n8n-nodes-evolution-api.evolutionApi, id: 72e5ffd6-df7e-4136-bbb9-dab0bde9c246) -> `app/workflows/1_lia_v3_1.py::node_resetar_status`
  - Converter áudio para base64 (n8n-nodes-base.extractFromFile, id: 8bc6d117-b93d-4e76-8129-04f5c2e172dc) -> `app/workflows/1_lia_v3_1.py::node_converter_audio_para_base64`
  - Sticky Note12 (n8n-nodes-base.stickyNote, id: 21dfa125-530b-4a6d-81d0-6e7825c23c36) -> `app/workflows/1_lia_v3_1.py::node_sticky_note12`
  - Gerar áudio (n8n-nodes-base.httpRequest, id: 700ef2a7-4535-4798-b20e-adc8b7b77f06) -> `app/workflows/1_lia_v3_1.py::node_gerar_audio`
  - Formatar SSML (@n8n/n8n-nodes-langchain.chainLlm, id: a525e6fe-8331-41bc-996e-cd7eedf20128) -> `app/workflows/1_lia_v3_1.py::node_formatar_ssml`
  - Tipo de mensagem1 (n8n-nodes-base.switch, id: d3cd199a-38d9-4308-889a-4358f97c249f) -> `app/workflows/1_lia_v3_1.py::node_tipo_de_mensagem1`
  - Memory (@n8n/n8n-nodes-langchain.memoryPostgresChat, id: f2b4fa71-067e-41df-9241-0585f654e9bf) -> `app/workflows/1_lia_v3_1.py::node_memory`
  - Responder mensagem áudio (n8n-nodes-evolution-api.evolutionApi, id: 3ba92b3e-5219-4c81-9b45-00b594602203) -> `app/workflows/1_lia_v3_1.py::node_responder_mensagem_audio`
  - Converter base64 para áudio. (n8n-nodes-base.convertToFile, id: 14e3ef56-d059-4507-926f-ae5869fb93ec) -> `app/workflows/1_lia_v3_1.py::node_converter_base64_para_audio`
  - Enfileirar mensagem. (n8n-nodes-base.postgres, id: 30db27c0-35c3-4e26-882a-14fc0a5f4828) -> `app/workflows/1_lia_v3_1.py::node_enfileirar_mensagem`
  - Google Gemini Chat Model. (@n8n/n8n-nodes-langchain.lmChatGoogleGemini, id: 4832ba2c-efff-4989-93ad-d4616015efeb) -> `app/workflows/1_lia_v3_1.py::node_google_gemini_chat_model`
  - Info (n8n-nodes-base.set, id: f7eb1080-324f-4508-9dc7-0757b857514e) -> `app/workflows/1_lia_v3_1.py::node_info`
  - cancelar_pedido (n8n-nodes-base.httpRequestTool, id: 7614af66-47bd-49d6-b03b-a4ae5201a259) -> `app/workflows/1_lia_v3_1.py::node_cancelar_pedido`
  - Code (n8n-nodes-base.code, id: 4e62e363-6d65-4f98-a59b-b602b5c5725e) -> `app/workflows/1_lia_v3_1.py::node_code`
  - Loop Over Items (n8n-nodes-base.splitInBatches, id: 7680728b-a97a-40b1-bd92-37ec4c106c98) -> `app/workflows/1_lia_v3_1.py::node_loop_over_items`
  - HTTP Request (n8n-nodes-base.httpRequest, id: 9d3d1c90-f2ee-4380-8b8b-6badc0bb4470) -> `app/workflows/1_lia_v3_1.py::node_http_request`
  - HTTP Request1 (n8n-nodes-base.httpRequest, id: 1df8c600-732e-40d9-ac4b-2ab1a7321c81) -> `app/workflows/1_lia_v3_1.py::node_http_request1`
  - HTTP Request2 (n8n-nodes-base.httpRequest, id: 31cdc6e0-4b2c-4700-b7e2-aee3deb384d3) -> `app/workflows/1_lia_v3_1.py::node_http_request2`
  - Marcar como lida texto (n8n-nodes-evolution-api.evolutionApi, id: 3b9ce552-7cf4-4650-ba27-e61e97e5e6cd) -> `app/workflows/1_lia_v3_1.py::node_marcar_como_lida_texto`
  - controle atendimentos (n8n-nodes-base.postgres, id: b3638eae-e47e-4dfe-94d0-3c8b577cb64d) -> `app/workflows/1_lia_v3_1.py::node_controle_atendimentos`
  - atualiza atendimento (n8n-nodes-base.postgres, id: 9e09756c-5e31-4387-8665-39bdd0d913c2) -> `app/workflows/1_lia_v3_1.py::node_atualiza_atendimento`
  - Marcar como lida audio (n8n-nodes-evolution-api.evolutionApi, id: 4e3dec4b-34cd-4576-81c7-56c8e907d3fc) -> `app/workflows/1_lia_v3_1.py::node_marcar_como_lida_audio`
  - controle atendimentos1 (n8n-nodes-base.postgres, id: 85fbcfb1-8427-4482-a34f-d56164231287) -> `app/workflows/1_lia_v3_1.py::node_controle_atendimentos1`
  - Convert to File (n8n-nodes-base.convertToFile, id: 25ca5262-c729-4127-8b8e-ac57ea758b6d) -> `app/workflows/1_lia_v3_1.py::node_convert_to_file`
  - OpenAI (@n8n/n8n-nodes-langchain.openAi, id: a00b60df-b19a-4b1c-a588-466059385342) -> `app/workflows/1_lia_v3_1.py::node_openai`
  - Sticky Note (n8n-nodes-base.stickyNote, id: ae694ad5-fddc-4287-ac52-0a82006f75a9) -> `app/workflows/1_lia_v3_1.py::node_sticky_note`
  - Marcar como lida audio1 (n8n-nodes-evolution-api.evolutionApi, id: 4f01ea44-7ddd-421f-8801-458dc94b83bd) -> `app/workflows/1_lia_v3_1.py::node_marcar_como_lida_audio1`
  - controle atendimentos2 (n8n-nodes-base.postgres, id: ba5e58a4-adae-4005-9b03-586f59cd601c) -> `app/workflows/1_lia_v3_1.py::node_controle_atendimentos2`
  - Atendente (@n8n/n8n-nodes-langchain.agent, id: ddeb99a3-9f98-46a5-a2e7-98296d1f2916) -> `app/workflows/1_lia_v3_1.py::node_atendente`
  - taxa_entrega (n8n-nodes-base.postgresTool, id: bff1176e-4b56-4ed1-9898-4df7de5d56a0) -> `app/workflows/1_lia_v3_1.py::node_taxa_entrega`
  - Chat Memory Manager (@n8n/n8n-nodes-langchain.memoryManager, id: bc46ec9c-3751-45e4-81d6-7702aed9fb81) -> `app/workflows/1_lia_v3_1.py::node_chat_memory_manager`
  - Postgres Chat Memory (@n8n/n8n-nodes-langchain.memoryPostgresChat, id: 2aef5b99-c5a8-483f-854f-dbcbb26d6529) -> `app/workflows/1_lia_v3_1.py::node_postgres_chat_memory`
  - When clicking ‘Execute workflow’ (n8n-nodes-base.manualTrigger, id: 3c552c81-3f61-41cf-bf9a-101ca6101290) -> `app/workflows/1_lia_v3_1.py::node_when_clicking_execute_workflow`
  - OpenAI2 (@n8n/n8n-nodes-langchain.lmChatOpenAi, id: c6883af4-5819-4d6f-9dd8-527667aa4b83) -> `app/workflows/1_lia_v3_1.py::node_openai2`
  - Convert to File2 (n8n-nodes-base.convertToFile, id: 4fb97b33-5ff7-4220-a77a-29f562f767be) -> `app/workflows/1_lia_v3_1.py::node_convert_to_file2`
  - enviar_pedido (n8n-nodes-base.httpRequestTool, id: ef10f770-3ae2-4bde-83f5-9fafd28cd05e) -> `app/workflows/1_lia_v3_1.py::node_enviar_pedido`
  - Convert to File1 (n8n-nodes-base.convertToFile, id: 21514567-6f4f-41f0-bcf1-e3e568587a4f) -> `app/workflows/1_lia_v3_1.py::node_convert_to_file1`
  - Analyze document (@n8n/n8n-nodes-langchain.googleGemini, id: ed8fbb5c-1cf1-4717-8832-42bfd2398c02) -> `app/workflows/1_lia_v3_1.py::node_analyze_document`
  - Sticky Note1 (n8n-nodes-base.stickyNote, id: 0258b464-472f-4234-90aa-468d16a62a3a) -> `app/workflows/1_lia_v3_1.py::node_sticky_note1`
  - Marcar como lida audio2 (n8n-nodes-evolution-api.evolutionApi, id: e20150ff-8eae-4e95-a00a-4dafe9964701) -> `app/workflows/1_lia_v3_1.py::node_marcar_como_lida_audio2`
  - controle atendimentos3 (n8n-nodes-base.postgres, id: d0d2155e-1872-497f-83a6-35d4a28d0800) -> `app/workflows/1_lia_v3_1.py::node_controle_atendimentos3`
  - calcular_totais (@n8n/n8n-nodes-langchain.toolCode, id: 320dcae4-754d-4b0b-b160-b464759054ac) -> `app/workflows/1_lia_v3_1.py::node_calcular_totais`
  - Execution Data (n8n-nodes-base.executionData, id: bc148a11-c7ec-4d68-933d-7248c4e93e3b) -> `app/workflows/1_lia_v3_1.py::node_execution_data`
  - stages (n8n-nodes-base.postgresTool, id: 73651afc-3948-484e-b463-34573ef27296) -> `app/workflows/1_lia_v3_1.py::node_stages`
  - cardapio (n8n-nodes-base.postgresTool, id: 2459e30e-3c76-4a5b-bd0d-b71997a91b08) -> `app/workflows/1_lia_v3_1.py::node_cardapio`
  - maps (@n8n/n8n-nodes-langchain.toolWorkflow, id: e990fbf6-c983-4a5d-baaa-a0de3fad5105) -> `app/workflows/1_lia_v3_1.py::node_maps`
  - Sticky Note13 (n8n-nodes-base.stickyNote, id: bfd2d491-bf3f-4f27-8be9-2146d577d0d1) -> `app/workflows/1_lia_v3_1.py::node_sticky_note13`
  - liberado (n8n-nodes-base.postgres, id: 695d18fd-e05f-486c-bd18-e4a2b72ee1e3) -> `app/workflows/1_lia_v3_1.py::node_liberado`
  - humano assumiu (n8n-nodes-base.postgres, id: 4ef66efc-6856-4ffe-9369-e51fc2c726b2) -> `app/workflows/1_lia_v3_1.py::node_humano_assumiu`
  - Filtro de Remetente (n8n-nodes-base.if, id: a3dfd2e7-d160-433b-b4a2-568e8243a834) -> `app/workflows/1_lia_v3_1.py::node_filtro_de_remetente`
  - historico1 (n8n-nodes-base.postgres, id: a37af949-52e3-4e52-9a13-93781355bdf5) -> `app/workflows/1_lia_v3_1.py::node_historico1`

## Workflow: 4. Cancelar_pedido

- File: `n8n_workflows/4. Cancelar_pedido.json`
- Python module: `app/workflows/4_cancelar_pedido.py`
- Routes/Triggers:
  - `POST /cancelar_pedido` -> `app/routes/4_cancelar_pedido.py::webhook_webhook`
- Nodes:
  - Webhook (n8n-nodes-base.webhook, id: b33d1e3c-934b-4bd9-9b7a-632312017a13) -> `app/workflows/4_cancelar_pedido.py::node_webhook`
  - Postgres (n8n-nodes-base.postgres, id: b0e779e2-f9bb-4136-ba17-74b5b8309f8d) -> `app/workflows/4_cancelar_pedido.py::node_postgres`
  - HTTP Request (n8n-nodes-base.httpRequest, id: 43cf27e3-6f9f-4abc-aecd-d46b0290a7c1) -> `app/workflows/4_cancelar_pedido.py::node_http_request`

## Workflow: 5. Atualização_de_pedidos

- File: `n8n_workflows/5. Atualização_de_pedidos.json`
- Python module: `app/workflows/5_atualizacao_de_pedidos.py`
- Routes/Triggers:
  - `POST /marcio_lanches` -> `app/routes/5_atualizacao_de_pedidos.py::webhook_webhook`
- Nodes:
  - Webhook (n8n-nodes-base.webhook, id: 9e119b9d-ca97-480e-a2cb-bd69c9dd29c4) -> `app/workflows/5_atualizacao_de_pedidos.py::node_webhook`
  - Verificar Status (n8n-nodes-base.switch, id: 47cc30d8-7a80-4483-96b7-b4602083d136) -> `app/workflows/5_atualizacao_de_pedidos.py::node_verificar_status`
  - Confirmado (n8n-nodes-base.postgres, id: 3c1098ac-9082-4473-92df-2c0589218a69) -> `app/workflows/5_atualizacao_de_pedidos.py::node_confirmado`
  - Aguardando entrega (n8n-nodes-base.postgres, id: 7d1d26e5-a15f-439a-889d-8ed44a17576a) -> `app/workflows/5_atualizacao_de_pedidos.py::node_aguardando_entrega`
  - Saiu para entrega (n8n-nodes-base.postgres, id: 13c43016-22ef-44ec-a482-2d92ac73b2d6) -> `app/workflows/5_atualizacao_de_pedidos.py::node_saiu_para_entrega`
  - Entregue (n8n-nodes-base.postgres, id: bb603380-026f-4aac-ba8c-6d4a11ed78ef) -> `app/workflows/5_atualizacao_de_pedidos.py::node_entregue`
  - Cancelado (n8n-nodes-base.postgres, id: 803ca9bd-1404-499e-b7d9-091c35b19f4f) -> `app/workflows/5_atualizacao_de_pedidos.py::node_cancelado`
  - Postgres (n8n-nodes-base.postgres, id: b1bb18d3-e418-47ad-81ec-b02d8ad55407) -> `app/workflows/5_atualizacao_de_pedidos.py::node_postgres`
  - Postgres1 (n8n-nodes-base.postgres, id: 8e021fef-74ae-49c1-9213-27e37ddabd33) -> `app/workflows/5_atualizacao_de_pedidos.py::node_postgres1`
  - Enviar mensagem (n8n-nodes-base.httpRequest, id: 3c800162-67f1-4f9f-b655-a8f73fe576c8) -> `app/workflows/5_atualizacao_de_pedidos.py::node_enviar_mensagem`
  - Enviar mensagem1 (n8n-nodes-base.httpRequest, id: 05c3181a-2456-4315-a975-f45f7e4418fb) -> `app/workflows/5_atualizacao_de_pedidos.py::node_enviar_mensagem1`
  - Postgres2 (n8n-nodes-base.postgres, id: c05a595b-2661-4142-87b6-8662d035bf3f) -> `app/workflows/5_atualizacao_de_pedidos.py::node_postgres2`
  - Enviar mensagem2 (n8n-nodes-base.httpRequest, id: 2d4b3451-19c0-4bd8-b7c3-7345c9aff1f8) -> `app/workflows/5_atualizacao_de_pedidos.py::node_enviar_mensagem2`
  - Postgres3 (n8n-nodes-base.postgres, id: e089fe34-461d-443e-8f95-80d1b2da4a48) -> `app/workflows/5_atualizacao_de_pedidos.py::node_postgres3`
  - Enviar mensagem3 (n8n-nodes-base.httpRequest, id: 0b699df8-cae3-4e1c-bf08-5d351b71b325) -> `app/workflows/5_atualizacao_de_pedidos.py::node_enviar_mensagem3`
  - Postgres4 (n8n-nodes-base.postgres, id: 2ff69857-e567-476e-b398-5c9a5e75fdf1) -> `app/workflows/5_atualizacao_de_pedidos.py::node_postgres4`
  - Enviar mensagem4 (n8n-nodes-base.httpRequest, id: 1b45b778-b4d4-4c91-8653-fc6d2ed2ab55) -> `app/workflows/5_atualizacao_de_pedidos.py::node_enviar_mensagem4`

## Workflow: 6. Recuperar_pedidos

- File: `n8n_workflows/6. Recuperar_pedidos.json`
- Python module: `app/workflows/6_recuperar_pedidos.py`
- Routes/Triggers: none
- Nodes:
  - Schedule Trigger (n8n-nodes-base.scheduleTrigger, id: c3656b31-0692-4a7b-9a1a-25b7d9903d31) -> `app/workflows/6_recuperar_pedidos.py::node_schedule_trigger`
  - Postgres1 (n8n-nodes-base.postgres, id: 5b2f7976-c8fd-4107-bd08-0704998ebcfc) -> `app/workflows/6_recuperar_pedidos.py::node_postgres1`
  - Loop Over Items (n8n-nodes-base.splitInBatches, id: 45a04e87-cf6a-4ef7-9072-fad172ae7558) -> `app/workflows/6_recuperar_pedidos.py::node_loop_over_items`
  - AI Agent (@n8n/n8n-nodes-langchain.agent, id: eb44bf6e-74aa-487e-ba99-beb0741a16f5) -> `app/workflows/6_recuperar_pedidos.py::node_ai_agent`
  - Edit Fields (n8n-nodes-base.set, id: 508667e5-181f-42a2-bfa1-3190a4d5c693) -> `app/workflows/6_recuperar_pedidos.py::node_edit_fields`
  - Google Gemini Chat Model (@n8n/n8n-nodes-langchain.lmChatGoogleGemini, id: 720c20c7-52f4-44c0-a523-4028c19c0d6f) -> `app/workflows/6_recuperar_pedidos.py::node_google_gemini_chat_model`
  - Postgres Chat Memory (@n8n/n8n-nodes-langchain.memoryPostgresChat, id: 6eb6f9f2-81c5-4354-86e0-d91aa74e5310) -> `app/workflows/6_recuperar_pedidos.py::node_postgres_chat_memory`
  - Evolution API (n8n-nodes-evolution-api.evolutionApi, id: f54ece1c-4a07-45a8-ab40-3525a6d64b75) -> `app/workflows/6_recuperar_pedidos.py::node_evolution_api`
  - Postgres (n8n-nodes-base.postgres, id: cda4a656-afa6-46a0-be8a-a937c19696d8) -> `app/workflows/6_recuperar_pedidos.py::node_postgres`

## Workflow: 7. Validação_Endereços

- File: `n8n_workflows/7. Validação_Endereços.json`
- Python module: `app/workflows/7_validacao_enderecos.py`
- Routes/Triggers: none
- Nodes:
  - Start (n8n-nodes-base.executeWorkflowTrigger, id: f0da5f92-70ae-491c-a82c-8d5dc8d6684f) -> `app/workflows/7_validacao_enderecos.py::node_start`
  - HTTP Request (n8n-nodes-base.httpRequest, id: 839cd279-5ac3-443a-88cb-d416b31d1a4a) -> `app/workflows/7_validacao_enderecos.py::node_http_request`
  - Code in JavaScript (n8n-nodes-base.code, id: 9c1e6dd8-5afa-41f6-a95a-ccbe37a1f891) -> `app/workflows/7_validacao_enderecos.py::node_code_in_javascript`

## Workflow: Atualiza Cardápio

- File: `n8n_workflows/Atualiza Cardápio.json`
- Python module: `app/workflows/atualiza_cardapio.py`
- Routes/Triggers: none
- Nodes:
  - consulta_cardapio (n8n-nodes-base.httpRequest, id: 54314f11-93e9-435a-b99b-fe53480ffb2c) -> `app/workflows/atualiza_cardapio.py::node_consulta_cardapio`
  - Schedule Trigger (n8n-nodes-base.scheduleTrigger, id: 08d3540c-5160-447f-a417-4de5e3517aea) -> `app/workflows/atualiza_cardapio.py::node_schedule_trigger`
  - Code in JavaScript (n8n-nodes-base.code, id: 8d7ffbef-c426-40bd-8b97-3f9b55a8a2f0) -> `app/workflows/atualiza_cardapio.py::node_code_in_javascript`
  - Execute a SQL query (n8n-nodes-base.postgres, id: ce20c0b0-c35a-45cb-95e8-e48a3d797dda) -> `app/workflows/atualiza_cardapio.py::node_execute_a_sql_query`
  - Insert rows in a table (n8n-nodes-base.postgres, id: 0e3eb3f8-9881-412f-9471-362ff3d7178e) -> `app/workflows/atualiza_cardapio.py::node_insert_rows_in_a_table`

## Workflow: Enviar_pedido

- File: `n8n_workflows/Enviar_pedido.json`
- Python module: `app/workflows/enviar_pedido.py`
- Routes/Triggers:
  - `POST /enviar-pedido` -> `app/routes/enviar_pedido.py::webhook_webhook`
- Nodes:
  - Webhook (n8n-nodes-base.webhook, id: 49a0d126-91c1-43be-89cd-201c7074718a) -> `app/workflows/enviar_pedido.py::node_webhook`
  - Enviar_pedido_Saipos (n8n-nodes-base.httpRequest, id: 5781eed6-c595-449f-a637-cb48214601d7) -> `app/workflows/enviar_pedido.py::node_enviar_pedido_saipos`
  - Salva_pedido_banco (n8n-nodes-base.postgres, id: f83c929b-997d-45aa-9782-34445fc5dc80) -> `app/workflows/enviar_pedido.py::node_salva_pedido_banco`
  - Wait (n8n-nodes-base.wait, id: e291e237-df8b-439a-b6cf-7c2792321e5e) -> `app/workflows/enviar_pedido.py::node_wait`
  - active_sessions_finished (n8n-nodes-base.postgres, id: 4364169f-1680-46b0-8c72-5e73799a9e9d) -> `app/workflows/enviar_pedido.py::node_active_sessions_finished`
  - Sticky Note (n8n-nodes-base.stickyNote, id: abb0dea4-389c-486b-93f4-e97a3184ff2d) -> `app/workflows/enviar_pedido.py::node_sticky_note`
  - Search Index (n8n-nodes-base.postgres, id: 901b57b7-33f7-4ff0-9ad5-fa892329b1c8) -> `app/workflows/enviar_pedido.py::node_search_index`
  - Match Fingerprint (n8n-nodes-base.code, id: 7c50fc56-1f4b-45e4-bd50-0818a0e4a5c6) -> `app/workflows/enviar_pedido.py::node_match_fingerprint`
  - Formatar JSON Saipos (n8n-nodes-base.code, id: fd9921c4-bba0-41ae-8c12-b9ee43479319) -> `app/workflows/enviar_pedido.py::node_formatar_json_saipos`

## Workflow: Gerar Embeddings Cardápio

- File: `n8n_workflows/Gerar Embeddings Cardápio.json`
- Python module: `app/workflows/gerar_embeddings_cardapio.py`
- Routes/Triggers: none
- Nodes:
  - Supabase - Buscar Itens (n8n-nodes-base.postgres, id: 6323229a-c2ec-450f-bcb5-c026cc4574af) -> `app/workflows/gerar_embeddings_cardapio.py::node_supabase_buscar_itens`
  - Supabase - Inserir (n8n-nodes-base.postgres, id: dd39f683-68ee-45a3-a459-58c48547b2ff) -> `app/workflows/gerar_embeddings_cardapio.py::node_supabase_inserir`
  - Loop Over Items1 (n8n-nodes-base.splitInBatches, id: fde00433-a3f4-4be3-82e4-07c4710dadfd) -> `app/workflows/gerar_embeddings_cardapio.py::node_loop_over_items1`
  - When clicking ‘Execute workflow’ (n8n-nodes-base.manualTrigger, id: 64d25dcc-39fa-444f-83f6-8802df1323ce) -> `app/workflows/gerar_embeddings_cardapio.py::node_when_clicking_execute_workflow`
  - HTTP Request (n8n-nodes-base.httpRequest, id: 544bb0c4-7a17-4334-85b3-106fde0cb2aa) -> `app/workflows/gerar_embeddings_cardapio.py::node_http_request`
  - Code in JavaScript (n8n-nodes-base.code, id: 07a43228-7109-4636-b22a-6cca4a0fc13c) -> `app/workflows/gerar_embeddings_cardapio.py::node_code_in_javascript`

## Workflow: Token_Saipos

- File: `n8n_workflows/Token_Saipos.json`
- Python module: `app/workflows/token_saipos.py`
- Routes/Triggers: none
- Nodes:
  - Token de Autorização (n8n-nodes-base.httpRequest, id: daad98bc-6677-4617-b439-77fcfdd0a31b) -> `app/workflows/token_saipos.py::node_token_de_autorizacao`
  - When clicking ‘Execute workflow’ (n8n-nodes-base.manualTrigger, id: 72b5ea2e-a0a1-4ad3-9e49-5090067966a3) -> `app/workflows/token_saipos.py::node_when_clicking_execute_workflow`

## Workflow: Webhook_Central_Saipos

- File: `n8n_workflows/Webhook_Central_Saipos.json`
- Python module: `app/workflows/webhook_central_saipos.py`
- Routes/Triggers:
  - `POST /saipos-central` -> `app/routes/webhook_central_saipos.py::webhook_webhook`
- Nodes:
  - Webhook (n8n-nodes-base.webhook, id: 833758ef-ccca-48c5-b193-01bbeb18b937) -> `app/workflows/webhook_central_saipos.py::node_webhook`
  - Switch (n8n-nodes-base.switch, id: e171ed9c-a76d-42cc-85e7-04d3f1e76d9b) -> `app/workflows/webhook_central_saipos.py::node_switch`
  - Márcio Lanches (n8n-nodes-base.httpRequest, id: bad994c6-d1ad-45c4-936d-1ffe431a862f) -> `app/workflows/webhook_central_saipos.py::node_marcio_lanches`
