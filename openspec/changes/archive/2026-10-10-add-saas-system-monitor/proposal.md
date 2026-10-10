# Proposal

## Why

O proprietário precisa correlacionar experiência, filas, recursos e atividade com evidências persistentes. O diagnóstico atual é manual e a campanha existente não mede capacidade máxima.

## What Changes

- Monitor administrativo com fontes, lacunas, atualidade, séries históricas, incidentes e exportação sanitizada.
- Permissões independentes, vazias por padrão, para métricas, árvore, incidentes e relatórios.
- Propriedade única vinculada ao UUID permanente da conta; endereço atual somente para identificação inicial, permitindo troca futura de e-mail. Diagnósticos operacionais exclusivos do proprietário, mesmo diante de grants concedidos a outra identidade.
- Instrumentação agregada de HTTP, aquisição de conexões e ciclos de trabalho; coleta periódica limitada; atividade autenticada limitada por sessão.
- Árvore paginada de contas e clientes, sem equiparar sessão válida a presença.
- Adaptador explícito de snapshot do host, sem agentes privilegiados ou mudanças OCI automáticas.
- Preservação do card de capacidade, das campanhas e das alterações preexistentes.

## Capabilities

### New Capabilities
- `deployment-operations/system-monitor`: coleta, histórico, alertas, interface e exportação operacional.
- `auth/administrative-activity`: autorização específica e sinais de atividade para árvore administrativa.

### Modified Capabilities
- `deployment-operations/admin-capacity-diagnostics`: guarda adicional de propriedade para capacidade e observabilidade facial, conforme diretriz humana posterior. Preserva o contrato métrico e complementa o operador explícito da change de piloto existente.

## Impact

Backend FastAPI/SQLAlchemy, migration expansiva, workers, frontend Next e testes sem servidor local. Implantação, aplicação da migration, concessões reais e configuração de coleta exigem liberação operacional própria. O pedido de 09/10/2026 autoriza criar os artefatos e implementar nesta mesma execução; supera a pausa padrão do fluxo propose. A campanha anterior permanece com seus gates próprios e não é alterada.
