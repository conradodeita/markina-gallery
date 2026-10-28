# Tasks

## 1. Inventário de consumidores e contrato sanitizado

- [x] 1.1 Mapear usos de `APP_ENV`, `INTEGRATION_SECRET_ENV`, `*_CREDENTIAL_ENV`, keyrings e AAD ambiental em código, Compose e evidências operacionais disponíveis; registrar matriz de consumidores e provar cobertura com busca/teste automatizado sem valores secretos, identificando runtime ainda não inventariado como bloqueio. Ver `inventory.md` e `validation.md`; teste de cobertura 2/2 e Ruff aprovados.
- [x] 1.2 Definir o contrato do inventário somente-leitura e fingerprint com ambiente em categorias permitidas, contagens agregadas, serviços/portas, schema e checksums, incluindo contagem de ciphertexts biométricos sem abri-los; verificar com fixtures sentinela que logs/recibos não contêm valores, payloads, IDs ou caminhos sensíveis. Implementado em `backend/app/environment_transition_inventory.py`; 12 testes focados e Ruff aprovados.

## 2. Transição local de envelopes

- [x] 2.1 Implementar contextos de cifra explícitos para origem e destino, validando igualdade dos campos ambientais e keyrings sem alterar `os.environ`; verificar cobertura com testes unitários de AAD, chave ausente e envelope incompatível. `IntegrationCipher.from_explicit_context()` e `for_environment()` implementados; 20 testes e Ruff aprovados.
- [x] 2.2 Implementar plano e execução da re-cifragem dos envelopes elegíveis numa única transação, com fingerprint revalidado, controle de concorrência e abortamento integral; verificar com PostgreSQL de teste que IDs, vínculos tenant/credencial, snapshots e registros financeiros permanecem idênticos. Teste PostgreSQL isolado aprovado no CI `40737909487` (shard 1: 543 testes aprovados); evidência em `validation.md`.
- [x] 2.3 Implementar recuperação dos envelopes e contexto ambiental anterior a partir de backup cifrado verificado; verificar por ensaio sintético de falha antes, durante e após a transação que não há estado parcial liberado. Backup autenticado e recovery implementados; testes focados cobrem corrupção prévia, rollback no meio e restauração após transição.
- [x] 2.4 Classificar WhatsApp, SMTP e configuração facial separadamente, sem copiar ou revelar valores, e bloquear mudança global enquanto um consumidor externo estiver desconhecido ou incompatível; verificar os casos validado, desativado e não classificado. Implementado `classify_external_integrations()` com evidência booleana sanitizada; cenários cobertos por testes focados.
- [x] 2.5 Bloquear a transição se embeddings, referências, localizadores, notificações ou outros ciphertexts biométricos dependerem do ambiente de origem; verificar com fixtures sintéticas que nenhum payload facial é aberto ou alterado por esta operação. O contrato bloqueia fingerprint com qualquer contagem biométrica positiva; testes percorrem todas as categorias sem carregar payloads.

## 3. Procedimento operacional e prontidão

- [ ] 3.1 Implementar e testar coletor remoto de inventário APP_ENV em modo estritamente somente-leitura, por workflow manual em `main` e comando SSH restrito com SHA/blob fixados; exibir relatório sanitizado mesmo com bloqueios e nunca emitir fingerprint quando alguma fonte estiver incompleta. Validar contratos do output, allowlist, ausência de valores/IDs/payloads/caminhos e inexistência de writes, pausas ou chamadas a provedores.
- [ ] 3.2 Exigir para mutação inventário/fingerprint idênticos, backup recuperável, plano revisável, autorização operacional específica, gate de pagamentos reais fechado e pausa graciosa somente dos consumidores próprios identificados; verificar que qualquer divergência aborta antes do primeiro write. Gate local implementado e testado; falta ensaio operacional controlado da pausa graciosa e recibo do backup persistido.
- [x] 3.3 Documentar o procedimento de execução, evidências sanitizadas, recuperação e validação de consistência; verificar que um operador consegue seguir o roteiro em ambiente sintético sem ler segredos nem emitir tráfego externo. Ver `operations.md`; o ensaio ponta a ponta persiste/recarrega backup cifrado, aplica a guarda, migra e restaura exclusivamente com fixtures locais.
- [x] 3.4 Fazer revisão focalizada de código obsoleto/substituído na área alterada, rodar testes direcionados, lint/typecheck/build aplicáveis e validação OpenSpec estrita; registrar evidências e bloqueios sem marcar produção como migrada. Revisão focalizada sem remoções elegíveis; 128 testes relevantes aprovados, Ruff/compileall/OpenSpec válidos. Não há typecheck ou build backend configurado.

## 4. Aplicação operacional em produção

- [ ] 4.1 Executar a transição somente após inventário real atualizado e revisão/aprovação humana do plano específico com serviços, portas, fingerprint, impacto e recuperação; registrar recibo sanitizado e validar configuração, envelopes, isolamento e saúde sem alterar histórico financeiro. Qualquer ciphertext biométrico no contexto de origem bloqueia esta task até change e autorização próprias.
- [ ] 4.2 Reexecutar o preflight da change de liberação geral e apresentar seu plano próprio; manter `MERCADOPAGO_ALLOW_LIVE_PAYMENTS` fechado até que os gates e a autorização operacional dessa change sejam satisfeitos.
