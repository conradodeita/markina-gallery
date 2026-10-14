## Why

O card “Acesso recente · Galerias privadas” da Visão geral já identifica as galerias recentes, mas o nome exibido não permite abri-las. O fotógrafo precisa passar pela listagem completa mesmo quando a galeria desejada já está diante dele, criando uma navegação desnecessária em uma área de uso recorrente.

## What Changes

- Transformar o nome de cada galeria privada recente em um link administrativo direto para a ficha dessa mesma galeria.
- Construir o destino com o UUID opaco já retornado pela projeção autenticada da Visão geral, sem acrescentar dados pessoais ao contrato.
- Preservar o estado visual de acesso, a indicação de prazo, o link “Todas” e os estados vazio, carregando e erro do card.
- Cobrir a navegação direta com teste direcionado do painel administrativo.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: acrescentar acesso direto, pela Visão geral autenticada, à ficha da galeria privada recente escolhida pelo fotógrafo.

## Impact

- Frontend administrativo: card de galerias privadas recentes em `frontend/app/admin/page.tsx` e seu teste direcionado.
- API: nenhuma alteração prevista; `/admin/validation-summary` já retorna o identificador opaco e o nome necessários.
- Banco, migrations, mídia, autenticação, privacidade, workers e dependências: sem alteração.
