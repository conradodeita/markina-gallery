# Tasks

## 1. Operação delimitada e testes locais

- [x] 1.1 Implementar ferramenta sem rota/runtime do produto, com allowlist, validação integral, fingerprint, simulação e auditoria; comprovar recuperação/restauração/PIX sintéticos preservando snapshots e compra confirmada externa ao lote.
- [x] 1.2 Cobrir recusa de actor/tenant, fundos confirmados, fingerprint obsoleto, elegibilidade/PIX inválidos, rollback, repetição após nova compra, retorno tardio e concorrência PostgreSQL; registrar resultados de pytest/Ruff/OpenSpec e revisão proporcional.

## 2. Revisão e operação autorizada

- [ ] 2.1 Preparar PR draft independente, revisar diff e concluir CI pertinente no head; registrar SHA/run sem modificar PRs #261/#262/#263 nem ampliar gates de publicação.
- [ ] 2.2 Apresentar inventário próprio, versão API/portas/subdomínio e impacto transacional; executar simulação remota com rollback e salvar pré-imagem 0600; verificar fotos/totais/meios e registrar divergências antes de aplicar.
- [ ] 2.3 Aplicar somente o lote autorizado com fingerprint validado e conferir por leitura PIX/seleção/snapshots antigos, idempotência e preservação de 04381887; registrar resultado e risco de links externos não invalidados, sem deploy.

## Workflow follow-up

- Sincronizar/arquivar somente após revisão humana. A autorização “Prossiga sem essa confirmação” vale para a recuperação delimitada destas três compras; não autoriza bypass geral, mudança de segredos, nova API de cobrança ou publicação de serviços.
