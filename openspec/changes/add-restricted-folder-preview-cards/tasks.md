# Tasks

## 1. Prévia administrativa restrita

- [x] 1.1 Acrescentar `preview_url` protegida ou `null` à listagem de pastas restritas, sempre de foto da própria pasta com derivado pronto; validar com teste de API para pasta vazia e pasta com foto processada.

## 2. Cards e identificação

- [x] 2.1 Mostrar cards de pastas restritas com prévia/placeholder, nome, contagem e estado; usar a capa para abrir/recolher sem escrita e validar teste de interação e fallback.
- [x] 2.2 Identificar as listas como `Pastas Públicas` no resumo e `Pastas restritas ao cliente` no Acervo; validar testes de renderização e ausência de mudança na lista pública.

## 3. Busca de clientes

- [x] 3.1 Adicionar busca por nome/telefone no Resumo da galeria, filtrando apenas os cards vinculados e mostrando estado vazio recuperável; validar teste de interação sem chamadas de escrita.
- [x] 3.2 Corrigir a busca geral de galerias para incluir clientes com vínculo atual sem derivada, preservando a busca legada; validar teste de API para nome/telefone de cliente canônica.

## 4. Integração

- [x] 4.1 Executar regressão frontend/backend aplicável, lint, typecheck, build Next, OpenSpec estrito e revisão do diff; registrar resultados e qualquer limitação sem declarar validação não feita.
- [ ] 4.2 Executar build de imagens Docker do projeto quando o daemon Linux estiver disponível; registrar resultado, sem alterar infraestrutura compartilhada para contornar a indisponibilidade.
- [ ] 4.3 Preparar PR focado e validar CI; publicar em homologação somente com autorização específica e sincronizar/arquivar OpenSpec após revisão humana, registrando evidências.

## Evidências e continuidade

- O Actions do PR #110 terminou verde, inclusive deploy em homologação; `https://markina-homolog.duckdns.org/healthz` e `/api/health` responderam 200 na investigação desta change. A alteração presente ainda não foi publicada.
- A prévia convencional, o ajuste opcional e a indexação facial de novas fotos usam a configuração efetiva da pasta. `inherit` recupera o padrão da galeria para ajuste; `custom` substitui os valores e `off` desliga. A permissão facial local permanece subordinada aos gates de ambiente/rollout. Esta change altera só a apresentação administrativa das pastas.
- 1.1: `python -m pytest backend/tests/test_derived_galleries.py -q -k restricted_folder_upload_uses_one_jpeg_pipeline_for_two_clients --tb=short` passou (1 teste): listagem vazia devolve `preview_url: null`; após gerar derivados, devolve URL administrativa protegida da foto da própria pasta. O runner local emitiu somente aviso de limpeza temporária do pytest após exit 0; nenhuma limpeza manual foi feita.
- A busca geral de `parent-galleries/overview` ainda usa `DerivedGallery.client_id` para corresponder nome/telefone, mas os vínculos novos vivem em `ParentGalleryRegistration`; o texto atual da página geral promete uma busca que pode falhar para clientes atuais. O usuário pediu busca também dentro do resumo da galeria; as duas funções são complementares.
- 2.1: `npx vitest run app/admin/galleries/client-gallery-card.test.tsx --maxWorkers=1` passou (3 testes). O novo teste abre a primeira pasta clicando na imagem administrativa protegida, confirma a segunda fechada, recolhe e abre o fallback sem imagem; nenhuma chamada de escrita ocorre.
- 2.2: `npx vitest run app/admin/galleries/client-gallery-card.test.tsx app/admin/galleries/gallery-editor.test.tsx --maxWorkers=1` passou (56 testes). O resumo mantém a lista comum e o link existente sob `Pastas Públicas`; o Acervo mostra `Pastas restritas ao cliente`. O jsdom registrou aviso conhecido de navegação para outro Document em teste existente, sem falha.
- 3.1: `npx vitest run app/admin/galleries/gallery-editor.test.tsx --maxWorkers=1` passou (54 testes). O teste filtra duas clientes por nome sem acento e telefone com espaço, mostra vazio, limpa e confirma que houve só as duas consultas iniciais GET do resumo/pastas.
- 3.2: `python -m pytest backend/tests/test_derived_galleries.py -q -k gallery_overview_finds_client_with_canonical_registration --tb=short` passou (1 teste): nome e telefone da cliente canônica retornam apenas sua galeria sem criar derivada. A consulta legada por derivada permanece no código.
- 4.1: `npx vitest run --maxWorkers=1` passou (50 arquivos, 349 testes); após ajuste de texto e mock, os 69 testes focais de Galerias passaram. Três testes de API dos caminhos alterados, Ruff, `npx tsc --noEmit`, `npm run build` e `openspec validate --strict --all` passaram (69 itens). `npm run lint` terminou com 0 erros e 37 avisos. `git diff --check` passou e o diff contém só API/listagem/busca administrativa, testes, CSS e OpenSpec desta change. Nenhuma validação visual autenticada ou deploy desta change foi declarada.
- 4.2 bloqueada pelo ambiente local: `docker info` não conecta a `npipe:////./pipe/dockerDesktopLinuxEngine`; nenhuma imagem foi construída e nenhum recurso compartilhado foi alterado. O próximo executor deve executar o build Docker do projeto quando o daemon estiver disponível, ou usar a evidência do pipeline de deploy autorizado se for suficiente para revisão.
