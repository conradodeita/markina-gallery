## Why

A prévia do fotógrafo e a galeria da cliente têm estruturas visuais diferentes e a prévia administrativa atual é excessivamente técnica. Isso impede validar a experiência que será efetivamente apresentada à cliente e reduz o protagonismo das fotografias.

## What Changes

- Criar uma composição visual única de galeria, reutilizada pela prévia autenticada do fotógrafo e pela rota da cliente.
- Organizar capa, contexto, navegação por pastas, grade de prévias protegidas, estados vazios e visualizador em uma hierarquia editorial e responsiva.
- Centralizar em Configurações a personalização de marca-d’água e proteção visual, aplicada de forma consistente às prévias protegidas de todas as galerias; manter no editor da galeria somente as decisões de apresentação que pertencem àquela galeria, incluindo a organização das pastas.
- Manter os dados, permissões e ações específicos de cada papel: a cliente recebe somente fotos liberadas e autorizadas; o fotógrafo vê a mesma composição em modo de prévia, sem conceder acesso adicional à cliente.
- Tornar erros de carregamento e ausência de capa/fotos visualmente explícitos e recuperáveis.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: a prévia administrativa passa a representar a composição final da galeria.
- `client-access/derived-galleries`: a galeria privada da cliente compartilha a mesma estrutura visual base da prévia.

## Impact

- Frontend Next.js das rotas de prévia administrativa, galeria privada, Configurações e componentes visuais, além dos testes correspondentes.
- APIs existentes poderão receber somente campos de apresentação indispensáveis e a configuração global de proteção, sem expor originais, dados de terceiros ou conteúdo não autorizado.
- Há somente migration aditiva para guardar a proteção visual global; ela não remove nem modifica dados existentes. Não há alteração de pagamentos, biometria, dados de produção nem integração externa.
