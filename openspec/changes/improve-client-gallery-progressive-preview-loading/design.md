## Context

A apresentação compartilhada de galeria é usada por superfícies de cliente e administrativas. O carregamento progressivo deve ser habilitado apenas nas grades autenticadas da cliente, mantendo intacta a apresentação administrativa e os limites atuais de acesso à mídia.

## Goals / Non-Goals

**Goals:**
- Reduzir a quantidade de prévias solicitadas de imediato ao abrir uma pasta extensa.
- Distribuir solicitações conforme as imagens se aproximam da área visível.
- Preservar visualizador ampliado, seleção, favoritos, filtros e endpoints protegidos existentes.

**Non-Goals:**
- Alterar listagem, ordenação, paginação ou autorização no backend.
- Alterar cache, geração de miniaturas, armazenamento ou configuração do servidor.
- Controlar um número exato de downloads simultâneos; essa abordagem deixa a antecipação próxima da viewport sob controle do navegador.

## Decisions

- Usar os atributos nativos de carregamento tardio e decodificação assíncrona nas imagens de grade das superfícies de cliente. O navegador pode buscar imagens um pouco antes de entrarem na viewport, reduzindo lacunas visuais durante a rolagem sem solicitar toda a pasta na abertura.
- Ativar esse comportamento por configuração explícita nos adaptadores de cliente, em vez de torná-lo padrão no componente compartilhado. Isso evita mudar o carregamento nas telas administrativas e em outros usos da apresentação.
- Manter os mesmos elementos de imagem e URLs protegidas já usados pela grade. O visualizador ampliado continua usando o fluxo existente para solicitar a foto selecionada; nenhuma URL pública ou nova permissão será introduzida.
- Cobrir a configuração e as superfícies de cliente com testes frontend que verifiquem o carregamento tardio na grade do cliente e a ausência dessa configuração nos usos administrativos.

## Risks / Trade-offs

- [O carregamento nativo é heurístico e varia entre navegadores] → validar o contrato observável por atributos e a experiência em viewport/rolagem; não prometer uma quantidade fixa de imagens pré-carregadas.
- [Uma imagem pode ainda não estar pronta no instante em que entra na viewport] → manter os estados visuais de carregamento e erro existentes e permitir que o navegador a carregue quando se aproximar.
- [A apresentação é compartilhada por superfícies distintas] → habilitar o modo explicitamente apenas nos adaptadores autenticados da cliente e proteger essa distinção com testes.


## Adaptação à árvore em produção

A base `aa7119c` unificou as superfícies autenticadas na rota `/public-galleries/[galleryId]`; a rota `/gallery/[galleryId]` apenas redireciona links legados. Nesta base, usar `deferGridImages`, já existente no componente, e habilitá-lo na rota canônica. Não criar um segundo prop equivalente nem reintroduzir a antiga página privada. A evidência e o diff devem usar a árvore ativa como referência.
