## Why

As APIs de acervo, galeria derivada e revisão já existem, mas o fotógrafo ainda não consegue executar o fluxo diário por telas. A validação com clientes também exige uma experiência clara e privada, não chamadas técnicas à API.

## What Changes

- Adicionar área administrativa para criar e localizar clientes, acervos, fotos JPEG e galerias privadas derivadas.
- Adicionar fluxo guiado para atribuir fotos ao cliente, definir prazo, mensagem e permissões de favorito/comentário.
- Evoluir as superfícies do cliente para biblioteca e revisão visual de galerias autorizadas, com estados de vazio, carregamento e acesso negado.
- Manter o acervo-mãe exclusivamente administrativo e usar somente endpoints autenticados para operações e prévias.
- Tornar ambas as superfícies estritamente backend-driven: dados, permissões, estados e transições vêm de APIs autorizadas, nunca de mocks ou decisões locais do browser.

## Capabilities

### New Capabilities
- `gallery-sales/operational-gallery-interface`: operação visual, autorizada e responsiva de clientes, acervos, fotos e galerias derivadas.

### Modified Capabilities
- `client-access/derived-galleries`: a biblioteca e a revisão passam a ter fluxos de interface explícitos para a cliente autorizada.

## Impact

Frontend Next.js, APIs administrativas de leitura/escrita já existentes e complementares, testes de autorização e documentação operacional. Não inclui biometria, checkout, pagamento ou entrega final.
