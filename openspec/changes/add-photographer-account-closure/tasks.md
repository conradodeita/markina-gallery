# Tasks

Todas as tarefas são locais. A existência destes artefatos não significa comportamento implementado. Registrar comandos, resultados, skips e limites da evidência na change durante a aplicação.

## 1. Modelo e transições

- [x] 1.1 Inventariar consumidores de status/tenant, sessões, filas e dados pessoais nos módulos afetados; entregar mapa de operações permitidas em `open`, `closing` e `closed`, conferido contra as specs, preservando a distinção de suspensão. Evidência: `inventory.md`.
- [x] 1.2 Implementar modelo de lifecycle e histórico de solicitações com UUID, UTC, idempotência e constraints; validar migration aditiva e dados legados em PostgreSQL descartável, incluindo recusa de downgrade quando houver histórico. Evidência: `validation.md`, migration 0117.
- [x] 1.3 Implementar solicitação autenticada, confirmação explícita de saldo e transição para `closing`; testar repetição, corrida concorrente e tentativa por outro tenant, registrando contratos e evidência. Evidência: `validation.md`; serviço sem rota pública até integração dos guards.

## 2. Acesso e proteção de obrigações

- [x] 2.1 Bloquear novas galerias e uploads antes de bytes/reserva em `closing`; testar backend e sessão antiga, mantendo tratamento das obrigações existentes e documentando guards alterados. Evidência: `validation.md`, recusa pré-body/readiness legado/reserva e sete rotas.
- [x] 2.2 Aplicar lifecycle em login, sessões, rotas e jobs sem interromper clientes autorizados nos prazos vigentes; bloquear novas buscas e políticas faciais desde `closing`, preservando a conclusão de trabalho já iniciado. Testar isolamento entre tenants e suspensão combinada com encerramento. Evidência: `validation.md`, checkpoint integrado e provas focadas de sessão/filas/retenção.
- [x] 2.3 Preservar conciliação, webhooks e auditoria em caminhos restritos de serviço; executar contratos de confirmação financeira e replay para tenant em encerramento/encerrado sem conceder sessão operacional. Evidência: `validation.md`, webhook assinado em três lifecycles.

## 3. Avaliação e conclusão

- [x] 3.1 Implementar avaliador tenant-scoped de prazos, reaberturas, pedidos, pagamentos, produção/entrega, reservas e mídia; testar pendências, fonte indisponível, pasta legada indeterminada, pasta comprovadamente nunca liberada elegível diretamente e carrinho abandonado após a janela, reutilizando guards existentes. Evidência: `validation.md`, avaliador e contratos de integração.
- [x] 3.2 Integrar avaliação com arquivamento por pasta e reavaliação retomável, incluindo exceção temporal só para pastas comprovadamente nunca liberadas; provar que falha/transferência incompleta mantém `closing` e preserva bytes locais, sem segunda fila ou cliente Drive. Evidência: `validation.md`; inclui capa isolada aprovada durante aplicação.
- [x] 3.3 Implementar conclusão atômica com instante UTC, auditoria e revogação de acesso; testar concorrência com checkout, obrigações novas, replay e saldo remanescente preservado sem débito/estorno implícito. Evidência: `validation.md`, corrida PostgreSQL e 10 contratos do avaliador/finalização.
- [x] 3.4 Registrar e testar a regra aprovada para avisos: linhas push/WhatsApp `queued` não atrasam o encerramento e não são enviadas nem alteradas enquanto `closed`; entregas `processing` continuam bloqueando até resolução. Evidência em `validation.md`: 3 testes direcionados aprovados e Ruff aprovado.
- [x] 3.5 Serializar claims de push/WhatsApp, recuperação de leases parados e reconciliação de entregas incertas com a finalização pela linha do tenant; incluir no bloqueio `processing` os outboxes diretos de vínculo, reabertura e busca facial, e serializar o materializador da projeção de pagamento. Manter `queued` preservado. A suíte focada passou **17 testes locais**; a prova PostgreSQL 17.11 exercitou push e WhatsApp vencendo e perdendo a disputa, confirmando bloqueio de encerramento ou preservação de `queued` sem envio. Ruff, compilação Python e OpenSpec estrito passaram; evidências em `validation.md`.

## 4. Recuperação administrativa

- [x] 4.1 Criar lote administrativo de recuperação ligado às operações por pasta, com autorização e reautenticação do proprietário; testar tenant alvo, idempotência, prioridade global e falha parcial com storage sintético.
- [x] 4.2 Integrar reserva/cobrança existente, isenção somente do tenant proprietário e prazo de 7/14/30 dias; provar saldo/capacidade insuficientes, liberação na falha e um único débito por sucesso, inclusive retries.
- [x] 4.3 Implementar reabertura separada após restauração íntegra do conjunto exigido; testar negação por recuperação parcial e por fotógrafo/cliente, preservando histórico e disponibilidade de suspensão.

## 5. Retenção e CPF

- [x] 5.5 Impedir que a confirmação de identidade pelo host de outro tenant encerrado invalide ou consuma o desafio original. A regressão com dois hosts resolvidos reproduziu a alteração indevida para `expired`; filtro por tenant aplicado antes de lock/mutação. Suíte de identidade: oito testes aprovados, conferindo estado/material/tentativas após expirar o cache ORM. Evidência em `validation.md` (15/11/2026).

- [x] 5.1 Inventariar campos de nome/e-mail/CPF e suas cópias, finalidades e constraints; documentar plano restrito de redução após dez anos, exceções e preservação de aceite/financeiro, sem executar expurgo persistente. Evidência estática em `inventory.md` e `validation.md`; nenhum dado persistente foi lido ou alterado.
- [x] 5.2 Implementar verificador protegido de CPF com associação ao tenant e versão da chave, preservando fingerprints legados e unicidade global entre versões; testar comparação, tenant divergente, chave ausente, compatibilidade legada e rotação mantendo chaves referenciadas, sem segredos nem CPF nos logs/respostas. Evidência: `validation.md`, implementação em `photographer_cpf.py` e migration 0120.
- [x] 5.3 Implementar fluxo limitado no host canônico do tenant para conferir CPF e verificar dados atuais por e-mail após dez anos; a reabertura consulta a verificação persistida e continua sendo decisão final do proprietário. Testes focados passaram; evidências e o limite da migração PostgreSQL sem URL de teste estão em `validation.md`.
- [x] 5.4 Implementar redução explícita de CPF/endereço e remoção do verificador somente nas condições aprovadas. A redução do perfil exige revisão após dez anos, proprietário reautenticado, ausência de obrigações e HMAC utilizável ou recibo íntegro de exclusão completa; preserva identidade mínima, mídia, financeiro e aceites. Remoção do HMAC permanece exclusiva do fluxo auditado de exclusão completa. 14 contratos do perfil e migration 0123 passaram em PostgreSQL descartável; UI autenticada comprovou recusa e sucesso, 23 testes frontend e build passaram. Evidência detalhada em `validation.md`; nenhuma operação persistente ou produção.

## 6. Interface e informação contratual

- [x] 6.1 Implementar solicitação e acompanhamento autenticados em Configurações, com consequências, saldo e pendências claras; API e componente validam escopo, Termos vigentes, idempotência, falhas, responsividade estrutural e acessibilidade. Evidências em `validation.md`.
- [x] 6.2 Implementar no console os lifecycles separados da disponibilidade, contador em dias completos e revisão manual calculada pelo servidor no décimo aniversário UTC do ciclo atual; listar/atualizar lotes e operações, solicitar recuperação e oferecer reabertura separada com os gates e reautenticação existentes. Testes de 29/02, ciclo anterior/incoerente, autorização, conta suspensa e ausência de CPF/fingerprint/códigos internos passaram; controles comuns de status não alteram tenant `closed`. Evidência em `validation.md`.
- [x] 6.3 Atualizar Termos versionados com seção de Aviso de Privacidade no mesmo documento e hash; cobrir encerramento, recuperação por créditos, categorias e retenções aprovadas, sem revelar mecanismo interno; testar preservação do aceite anterior, texto/hash e gate da versão vigente, incluindo referência protegida do CPF. Evidências em `validation.md`; minuta permanece apenas como rascunho local, sem publicação.
- [x] 6.4 Revisar UI autenticada com contas sintéticas em 390/768/1440 px e temas suportados; registrar capturas e corrigir desalinhamento, overflow, contraste, estados vazios e feedback de falha. Chrome com login real sintético (incluindo TOTP do proprietário), matriz de 24 combinações de tamanho/tema do fotógrafo, encerramento pendente e console fechado, estados vazio/carregamento/falha e recuperação da consulta. Corrigidos keys duplicadas, cartões aninhados, tokens de tema inexistentes, erro de transporte cru e aviso de sucesso obsoleto. 22 testes frontend, ESLint, TypeScript e build passaram; evidência em `validation.md`.

## 7. Integração e prontidão local

- [x] 7.1 Executar jornada sintética de encerramento com prazo/pedido pendente, arquivo, saldo remanescente, recuperação e reabertura antes/depois de dez anos; registrar evidência de isolamento e condições de bloqueio, sem chamadas reais ao Drive. Bateria integrada de contratos passou; evidência em `validation.md`.
- [x] 7.2 Executar validação integrada de migrations descartáveis, contratos críticos e checks de backend/frontend apropriados; revisar diff contra duplicação/código obsoleto na área afetada e documentar ausência de limpeza segura quando aplicável. Evidências em `validation.md`; a revisão visual 6.4 foi concluída em 10/11 e está registrada separadamente.
- [x] 7.3 Validar OpenSpec estrito e reconciliar tasks, specs, evidências e limites; entregar resultado local revisável e dependências de produção sem marcar ensaio Workspace, deploy ou autorização como executados. Resultado e bloqueios finais em `validation.md`; sincronização/arquivo seguem sujeitos à revisão humana.

## 8. Biometria ao encerrar a conta

- [x] 8.1 Marcadores UTC e barreira tenant-scoped implementados. Novas buscas e mudanças de política são bloqueadas desde `closing`; o primeiro ciclo persiste o marcador e desativa políticas; após o marcador, novos claims e gravações em fila ficam bloqueados, enquanto leases válidos podem terminar. PostgreSQL confirmou a serialização entre request concorrente e marcador; testes cobrem claims, enqueue, lease e retry. Evidência em `validation.md`.
- [x] 8.2 Migration aditiva `20261111_0125` e `FacialSearchConsentProof` tenant-scoped implementados. A prova preserva somente ID/contexto, método, versões, declaração e instante, sem payload biométrico. PostgreSQL descartável confirmou upgrade, downgrade vazio e recusa de downgrade quando há prova ou marcador; não há backfill. Evidência em `validation.md`.
- [x] 8.3 Limpeza retomável implementada antes de `closed`: cancela trabalho pendente/expirado, aguarda leases, copia prova idempotente e remove dados operacionais, referências, arquivos e payloads. Falha mantém `closing`; testes sintéticos confirmam retry e isolamento entre dois tenants. Dados de cliente, créditos, mídia comercial e auditoria não são apagados pelo serviço biométrico; comprovantes mínimos não recebem expurgo automático. Evidência em `validation.md`.
- [x] 8.4 Reabertura não restaura requests faciais removidos nem consome comprovante antigo como novo consentimento. Termos versionados e matriz de retenção foram atualizados; testes cobrem encerramento/reabertura, confirmação mínima, migração, concorrência e falha/retry. Revisão de refatoração sem remoção segura elegível. Evidências em `validation.md` e `../add-photographer-signup-portal/production-release-readiness.md`. Nenhuma ação de produção, Drive ou publicação.

## Workflow follow-up

- Revisar proposta/specs/design/tasks antes de código conforme o mandato e o fluxo de planejamento utilizado.
- Sincronizar specs principais e arquivar somente após revisão humana exigida pelo repositório.
- A configuração real/ensaio Workspace usa o proprietário e exige autorização operacional própria antes de abertura a tenants. Nenhuma tarefa local autoriza deploy, migration persistente, expurgo, push ou alteração de infraestrutura.
