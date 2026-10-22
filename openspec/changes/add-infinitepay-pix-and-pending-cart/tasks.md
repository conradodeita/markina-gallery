# Tasks

## 1. Contrato persistido e confirmação
- [x] 1.1 Implementar snapshot de métodos, método confirmado e desistência visual em migration0086/modelo, com preservação do legado e downgrade protegido; validar migration e contrato. Evidência:4 testes PostgreSQL aprovados em61,12s;Ruff aprovado.
- [x] 1.2 Implementar criação mista e confirmação PIX/cartão pelo snapshot com testes HTTP/domínio, isolamento/idempotência e compatibilidade de links antigos. Evidência:20 casos de confirmação passaram no ensaio PG;29 HTTP finais passaram inclusive em APP_ENV=test.

## 2. Recebimento de retorno
- [x] 2.1 Configurar webhook paid e processar candidatos por payment_check autenticado usando credencial histórica; validar falsificação, erro, repetição/concorrência e retorno tardio sem confiar no navegador/payload. Evidência:15 casos PG aprovados96,40s e2casos threadpool/concorrência/retry17,83s;HTTP29/0 eRuff.

## 3. Carrinho e interface
- [x] 3.1 Projetar pendências com fotos no Carrinho, omitir da lista Compras conforme contrato e permitir desistência visual auditada sem liberar reservas; validar ownership/revisão/corridas e nova seleção independente. Evidência:5 casos PG aprovados44,08s;regressão de projeção falhou antes do ajuste.
- [x] 3.2 Adequar UI Carrinho/Compras/painel/configuração e textos para os dois meios, PIX manual separado e método confirmado real; testar mensagens/ações/remoção e estados antigos. Evidência:88 testes focados aprovados;624/624 frontend na repetição completa, sem alteração no teste facial intermitente;Ruff/ESLint sem erros.

## 4. Integração
- [ ] 4.1 Executar regressões/gates backend/frontend/migration/OpenSpec, revisar diff/manutenção proporcional, atualizar plano0086 e mesmo PR262 draft e conferir CI final; sem merge/deploy/migration real/segredos.

## Workflow follow-up

Não habilitar PIX na InfinitePay até a implementação publicada; proprietário confirmou essa decisão. Revisão, autorização operacional, inventário, backups/keyring/restore e release0086 permanecem gates humanos próprios. Não alterar PR261 ou ampliar escopo do PR266 aprovado.
