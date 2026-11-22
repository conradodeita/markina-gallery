# Tasks

## 1. Contratos e persistência

- [x] 1.1 Reconciliar contratos e consumidores de host/signup/onboarding, decisão do proprietário e política de refatoração; artefatos strict válidos e inventário em validation.md.
- [x] 1.2 Implementar estado de reserva aditivo e proteção no resolvedor/links; 5 testes SQLite e 6 testes PostgreSQL (incluindo migration/rollback preservador) passaram, evidências em validation.md.

## 2. Reserva autenticada

- [x] 2.1 Implementar leitura/reserva inicial com validação, nomes protegidos, sessão verificada, unicidade global, idempotência e auditoria; 21 testes passaram em PostgreSQL sintético local, incluindo concorrência A/B e mesma conta; Ruff passou.

## 3. Primeiro acesso e UI

- [x] 3.1 Exibir aviso no painel e etapa de escolha em Configurações com prévia/check/preparação pendente; 9 testes de componente passaram, incluindo conflito/rede/retry, estado inválido e exclusão de dono/legados; lint/typecheck sem erros.
- [x] 3.2 Validar fluxo local pela UI, lint, typecheck, build e regressões pertinentes; Chrome desktop/mobile, 14 testes frontend, 35 regressões backend e smoke opcional posteriormente executado passaram; evidências e limites em validation.md.
- [x] 3.3 Tratar a resposta 403 esperada da leitura opcional `GET /api/admin/onboarding/address` como ausência da capacidade, sem aviso global de acesso negado; manter o tratamento de 401 e dos demais 403. Validado com SessionBoundary (35 testes) e jornada UI do proprietário; evidência em `validation.md`.

## 4. Integração e continuidade

- [x] 4.1 Revisar diff, compatibilidade/segredos e refatoração proporcional, validar OpenSpec strict e registrar roteiro para gate posterior em activation-gates.md; nenhuma prontidão pública inferida, sem sync/arquivo/deploy.

## Workflow follow-up

- Revisão humana, sync e arquivo somente após os requisitos aplicáveis estarem validados.

## 5. Refinamento visual após revisão humana

- [x] 5.1 Tornar inequívoco que a escolha define o link/URL da marca, alinhar o aviso do primeiro acesso ao conteúdo administrativo com estilo local responsivo e revisar somente CSS/cópia diretamente afetados, preservando o aviso compartilhado de outros gates. Evidência: CSS Module próprio, aviso dentro de `admin-content`, componentes e cópia sem mudança do contrato de reserva.
- [x] 5.2 Validar os contratos da interface, lint/typecheck aplicáveis e a apresentação local em desktop e mobile; registrar evidências e limitações em `validation.md`. Testes 26/26, ESLint, typecheck e OpenSpec strict passaram; apresentação local conferida em 390×844 e desktop, com a conta sintética já reservada (o banner é coberto por teste de componente e fica oculto por regra de produto nessa conta).
