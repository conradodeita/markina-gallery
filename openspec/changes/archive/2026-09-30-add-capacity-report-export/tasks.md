# Tasks

## 1. Contrato e serialização do relatório

- [x] 1.1 Extrair os tipos do snapshot usados pelo frontend e implementar o serializador puro `capacity-report/v1` com ordem fixa, valores brutos, versões e projeção explícita de todos os campos permitidos; verificar com teste unitário do relatório completo que não usa DOM, rede ou estado global.
- [x] 1.2 Cobrir no teste do serializador zero observado, evidências calculada/estimada, `value=null` com motivo, ordenação determinística e campos extras com sentinelas sensíveis; verificar que o texto preserva as lacunas e não contém nenhuma sentinela fora da allowlist.

## 2. Ação administrativa e documentação

- [x] 2.1 Integrar **Copiar relatório** ao snapshot atual com estado de progresso e feedback acessível de sucesso; verificar no teste do componente que a ação escreve exatamente o relatório esperado, não chama `fetch` novamente e impede cópias concorrentes.
- [x] 2.2 Tratar API de clipboard ausente ou rejeitada e limpar o estado de cópia quando uma coleta começa ou perde autorização; verificar no teste do componente que a falha mantém o snapshot, que uma resposta 401/403 remove snapshot e botão e que não há download, persistência ou envio alternativo.
- [x] 2.3 Atualizar `docs/admin-capacity-diagnostics.md` com o procedimento, formato versionado, campos, interpretação, privacidade e limitações; verificar por revisão documental que o exemplo conserva UTC, cache, evidências e indisponibilidades sem prometer visão por fotógrafo, histórico ou SLO.

## 3. Integração e evidências

- [x] 3.1 Executar os testes do frontend, lint, `tsc --noEmit` e build de produção; corrigir regressões causadas pela mudança e registrar os comandos e resultados em `validation.md`.
- [x] 3.2 Revisar o diff para confirmar ausência de endpoint, migration, segredo, telemetria, armazenamento e arquivos não relacionados; executar `openspec validate add-capacity-report-export --strict` e registrar a validação final em `validation.md` antes de marcar a change pronta para commit e revisão.
