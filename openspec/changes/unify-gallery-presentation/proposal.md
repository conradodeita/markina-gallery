## Why

A prévia do fotógrafo e a galeria da cliente têm estruturas visuais diferentes e a prévia administrativa atual é excessivamente técnica. Isso impede validar a experiência que será efetivamente apresentada à cliente e reduz o protagonismo das fotografias.

## What Changes

- Criar uma composição visual única de galeria, reutilizada pela prévia autenticada do fotógrafo e pela rota da cliente.
- Organizar capa, contexto, navegação por pastas, grade de prévias protegidas, estados vazios e visualizador em uma hierarquia editorial e responsiva.
- Centralizar em Configurações a personalização de marca-d’água e proteção visual, aplicada de forma consistente às prévias protegidas de todas as galerias; manter no editor da galeria somente as decisões de apresentação que pertencem àquela galeria, incluindo a organização das pastas.
- Manter os dados, permissões e ações específicos de cada papel: a cliente recebe somente fotos liberadas e autorizadas; o fotógrafo vê a mesma composição em modo de prévia, sem conceder acesso adicional à cliente.
- Tornar erros de carregamento e ausência de capa/fotos visualmente explícitos e recuperáveis.
- Remediar o retorno visual de homologação com uma composição editorial mais clara para fotógrafo e cliente, reduzindo ruído, uniformizando espaços e priorizando a fotografia.
- Acrescentar dissuasão honesta contra cópia casual nas prévias: impedir arraste, menu de contexto e cópia comum, exibir aviso de conteúdo protegido e manter a marca-d’água incorporada no arquivo servido, sem prometer bloqueio impossível de screenshot pelo sistema operacional.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: a prévia administrativa passa a representar a composição final da galeria.
- `client-access/derived-galleries`: a galeria privada da cliente compartilha a mesma estrutura visual base da prévia.

## Impact

- Frontend Next.js das rotas de prévia administrativa, galeria privada, Configurações e componentes visuais, além dos testes correspondentes.
- Interações de dissuasão no navegador e mensagens acessíveis de proteção, sem alterar a autorização ou expor originais.
- APIs existentes poderão receber somente campos de apresentação indispensáveis e a configuração global de proteção, sem expor originais, dados de terceiros ou conteúdo não autorizado.
- Há somente migration aditiva para guardar a proteção visual global; ela não remove nem modifica dados existentes. Não há alteração de pagamentos, biometria, dados de produção nem integração externa.

## Relação com a change sucessora

A composição compartilhada, a proteção incorporada no arquivo e a comunicação honesta sobre screenshots permanecem válidas. `improve-gallery-and-client-data-lifecycle` amplia essa composição para Galerias públicas autenticadas, privadas e histórico, e define que a privada herda a apresentação efetiva da Galeria pública. A proteção visual continua possuindo fonte global; a Galeria pública consome essa fonte e transmite sua configuração efetiva às derivadas, sem override privado. Este artefato SHALL NOT ser interpretado como limitação da cliente a uma experiência exclusivamente privada.
