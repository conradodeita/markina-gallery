# Proposal

## Why

A instalação atual não oferece ao administrador um diagnóstico conjunto das conexões PostgreSQL, dos limites efetivos do pool e da espera nas filas duráveis. O primeiro recorte de P0.3 deve tornar essas informações verificáveis antes de discutir expansão, sem transformar contadores locais ou números históricos de benchmark em capacidade global comprovada.

## What Changes

- Acrescentar diagnóstico somente leitura, acessível exclusivamente ao administrador vinculado à conta única ativa, preservando os guardas de ownership existentes.
- Mostrar conexões agregadas do banco da aplicação e do servidor PostgreSQL ao qual ela já se conecta, reservas técnicas disponíveis e limites/ocupação do pool do processo API que respondeu. Toda informação terá classificação, unidade, instante UTC, fonte e escopo explícitos.
- Mostrar contagens e idade da pendência nas filas de mídia, ajuste de prévias e nas três classes faciais (`search`, `index`, `maintenance`). Separar trabalho aguardando, agendado e em processamento; declarar quando a idade disponível é somente aproximação da espera. Outboxes/mensagens e outras rotinas ficam explicitamente fora da cobertura inicial.
- Expor `GET /admin/capacity-observability` e reutilizar a Visão geral `/admin` com seção recolhível “Diagnóstico de capacidade”, carregada sob demanda e com atualização manual. Preservar `/admin/validation-summary` e `/admin/facial-observability`.
- Documentar inventário necessário ao orçamento global, incluindo processos, engines/pools, tarefas pontuais e reservas. Como a API não conhece todos esses consumidores, devolver orçamento global indisponível e suas lacunas; não estimar réplicas seguras nem multiplicar o pool local por serviços presumidos.
- Limitar consultas e cardinalidade, degradar por seção e retornar apenas agregados sanitizados. Não ler payloads de jobs, consultas SQL em execução, fotos, tokens, nomes, telefones ou biometria.

## Capabilities

### New Capabilities

- `deployment-operations/admin-capacity-diagnostics`: contrato de diagnóstico administrativo somente leitura, fontes e limites das medições, cobertura de filas e declaração do orçamento incompleto.

### Modified Capabilities

Nenhuma. A nova capacidade complementa as regras de operação e a interface administrativa existentes sem substituí-las.

## Impact

Backend FastAPI/SQLAlchemy, projeção administrativa tipada, seção React na Visão geral e testes locais sintéticos. Reutilizar autenticação, engine, modelos de filas, componentes de estado e padrões de minimização; não chamar o coletor facial de histórico ilimitado para construir esta resposta. Sem migration, novo serviço, dependência externa ou mudança de infraestrutura prevista.

## Non-goals

Este recorte não conclui P0.3: SLOs gerais, esquema métrico completo, ledger restrito por tenant, séries temporais, latência de serviço/API, bytes e orçamento global aprovado continuam dependências futuras, assim como B05/B06/B11. Limites faciais existentes não viram SLO geral. P0.2 (fairness/quotas) e isolamento entre múltiplos fotógrafos permanecem fora do escopo.

Não alterar defaults, `.env`, segredos, pools, réplicas, quotas, limites de negócio, claims, prioridade, retenção ou guardas de instalação única. Não adicionar billing, autoscale, exporter, benchmark em servidor compartilhado nem promessa de capacidade/SLA. Nenhuma operação de CI, servidor, navegador, OTP, dados remotos, publicação ou deploy integra esta proposta.

## Review

Estado: planejamento para decisão humana, sem implementação autorizada nesta entrega. Revisar o contrato mínimo, a cobertura inicial de cinco classes de fila, a apresentação sob demanda e o orçamento explicitamente indisponível. Uma futura solicitação de aplicação é necessária antes do código; deploy, sync e archive têm seus próprios gates.

Fonte de direção: relatório local não versionado `docs/ROADMAP-ARQUITETURA-ELASTICA-20260929.md`, identificador PYP-ELASTIC-20260929, seções 12, 14, 17 e 21, consultado no checkout principal apenas como referência. Suas decisões pertinentes estão reproduzidas neste planejamento, sem copiar o relatório nem depender dele para executar as tasks. Base inspecionada: `abd4d21f8fec1efd0f18eb0a8eebe4c0f2444293`.
