## Context

Veja `proposal.md` para a motivação e o delta de `gallery-sales/operational-gallery-interface` para o contrato. A Visão geral já consulta `/api/admin/validation-summary`, cuja coleção `recent_galleries` fornece `id`, `name`, prazo e estado. A ficha privada já possui rota administrativa baseada nesse mesmo `id`; hoje apenas a renderização do nome no card não oferece navegação.

## Goals / Non-Goals

**Goals:**

- Reutilizar o contrato autenticado e a rota administrativa existentes.
- Oferecer navegação semântica e acessível pelo nome da galeria recente.
- Preservar a leitura independente do prazo e do estado de acesso.

**Non-Goals:**

- Tornar a linha inteira clicável, alterar a ordenação ou ampliar a quantidade de galerias recentes.
- Alterar a API, o modelo de dados, as regras de autorização ou o conteúdo da ficha privada.
- Introduzir prefetch, cache ou uma nova consulta de rede.

## Decisions

### 1. O nome será o alvo explícito do link

O nome renderizado no card será substituído por um link interno para a ficha administrativa correspondente. Manter apenas o nome como alvo evita tornar o badge de estado ou a indicação de prazo parte de uma área clicável ambígua. A alternativa de envolver a linha inteira foi rejeitada por aumentar o risco de ativação acidental e reduzir a clareza semântica.

### 2. O destino reutilizará exclusivamente o identificador retornado pelo resumo

O frontend formará a navegação com `recent_galleries[].id`, seguindo o mesmo padrão da listagem de galerias privadas. Não haverá busca por nome, novo endpoint nem dado adicional. Se a galeria deixar de existir entre o resumo e o clique, a própria ficha continuará responsável por apresentar seu estado de indisponibilidade.

### 3. A validação será direcionada ao painel

O teste do componente verificará que o nome possui destino para a ficha do `id` recebido e que o badge de estado continua renderizado. Isso cobre o comportamento novo sem executar localmente uma suíte completa para uma alteração de apresentação isolada.

## Risks / Trade-offs

- [Nome pouco perceptível como link] → usar o componente visual de link já compartilhado pelo painel e verificar seu papel acessível no teste.
- [Galeria removida após carregar a Visão geral] → manter o tratamento de erro já existente na ficha, sem conservar dados obsoletos no browser.
- [Mudança acidental do badge ou prazo] → preservar a estrutura atual fora do nome e cobrir o estado no teste direcionado.

## Migration Plan

Não há migration nem alteração de dados. A entrega seguirá branch focada, PR, CI obrigatório e deploy autorizado em homologação; em caso de regressão visual, o componente pode ser revertido sem qualquer ação sobre banco, mídia ou serviços de processamento.
