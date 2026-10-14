## Why

Na Etapa 03, o acompanhamento automático de uma capa em processamento ativa o estado de carregamento do editor inteiro a cada consulta. A página é desmontada e remontada aproximadamente a cada 1,5 segundo, produzindo o efeito de “piscar” e tornando os controles instáveis.

## What Changes

- Separar o carregamento inicial da Etapa 03 da atualização silenciosa do estado da capa.
- Manter cabeçalho, formulário, valores digitados, foco e rolagem estáveis enquanto a capa estiver sendo consultada em segundo plano.
- Atualizar apenas o estado e a prévia da capa quando uma resposta mais recente chegar.
- Encerrar o polling quando a capa atingir estado terminal e conter falhas transitórias na área da capa, sem substituir o editor inteiro.
- Adicionar contratos que reproduzam múltiplas atualizações de processamento sem tela global de carregamento nem perda de edição.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: exigir atualização de processamento estável na Etapa 03, sem intermitência da página ou perda do formulário.

## Impact

- Estado e efeitos React do editor administrativo da galeria, especialmente a Etapa 03.
- Testes frontend de carregamento inicial, polling, formulário e falha transitória.
- Nenhuma alteração em endpoint, banco, worker de mídia, arquivo original, autorização ou configuração da capa.
