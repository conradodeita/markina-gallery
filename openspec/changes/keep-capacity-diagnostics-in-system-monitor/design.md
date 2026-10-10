# Design

## Context

As duas páginas montam InstallationDiagnostics, componente que consulta capability própria antes de exibir o card. A autorização do diagnóstico é separada dos grants do monitor. Consulte proposal.md para a motivação.

## Goals / Non-Goals

Localização única no Monitor do Sistema. Sem mudanças em coleta, permissões, atualização manual ou serialização do relatório; o campo label da árvore passa a identificar o fotógrafo por e-mail.

## Decisions

Remover somente import e montagem em frontend/app/admin/page.tsx. Preservar componente e montagem no monitor; esconder por CSS manteria consulta desnecessária e não satisfaria a retirada. Regressão da Visão Geral verifica ausência do card e de consultas de diagnóstico mesmo com capability positiva. Regressão do monitor verifica presença autorizada e comportamento sob demanda, aproveitando testes existentes de coleta/cópia/revogação.

Para a árvore, obter e-mail da única identidade administrativa com vínculo ativo na conta, por projeção SQL agregada correlacionada e limitada. Conta sem vínculo único exibe Fotógrafo [e-mail indisponível], sem escolher arbitrariamente um administrador nem eliminar a conta da árvore. Pesquisa por e-mail mantém os filtros/isolamento existentes. UUID continua chave de paginação/expansão. E-mail fica somente na árvore protegida por tree + proprietário e private,no-store; não entra em métricas, dimensões, auditoria ou exportações. A opção de adicionar nome foi cancelada pelo proprietário antes de qualquer mudança no modelo.

## Risks / Trade-offs

Retirada acidental na segunda tela → teste explícito do monitor. Referências antigas à Visão Geral → delta altera localização do card e da cópia, preservando os cenários anteriores. A spec de monitor exige preservar o card sem fixar sua localização; design arquivado mantém a decisão histórica, substituída por esta solicitação.

## Migration Plan

Sem migration ou configuração. PR para develop; CI e deploy existentes. Pausar após push conforme orientação humana. Após publicação verde, validar as duas páginas no servidor autorizado com sessão normal do proprietário. Rollback pelo fluxo Git/deploy vigente, sem operações destrutivas.
