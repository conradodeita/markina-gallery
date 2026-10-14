# Tasks

## 1. Exclusividade da pasta

- [x] 1.1 Impedir novos grants adicionais a pastas restritas no backend, preservando grants legados e revogação explícita; validar testes de API para nova pasta, repetição idempotente e pasta compartilhada legada.
- [x] 1.2 Remover a ação “Adicionar cliente” do Acervo sem ocultar os destinatários legados; validar testes do card e conferir que a UI não chama o endpoint de grant.

## 2. Abertura e conferência

- [x] 2.1 Abrir o processamento junto com a pasta no Acervo, sem mudar a etapa Imagens; validar testes de mount, ausência de mutação ao abrir e cancelamento de polling ao fechar.
- [x] 2.2 Permitir ampliação acessível da foto do Acervo e das imagens antes/depois, reutilizando o padrão administrativo protegido; validar botão, Escape, foco e URLs sem original em testes frontend.

## 3. Envio de fotos

- [x] 3.1 Adicionar progresso real de bytes e espera por capacidade ao utilitário de upload, preservando o transporte atual sem callback; validar sucesso, 503/retentativa e erro em testes sintéticos.
- [x] 3.2 Iniciar envio ao selecionar arquivos no Acervo, mostrar progresso e estados do lote, e permitir retentativa explícita só das falhas; validar ausência do botão “Enviar fotos”, prevenção de duplicatas/concorrência e testes frontend.

## 4. Integração

- [ ] 4.1 Executar testes direcionados e regressão aplicável, lint/typecheck, builds e OpenSpec estrito; revisar diff de segurança/escopo e registrar evidência sem declarar homologação não executada.
- [ ] 4.2 Preparar PR focado e validar CI; publicar somente após autorização específica com inventário e healthchecks, e arquivar/sincronizar OpenSpec somente após revisão humana.

## Evidências e continuidade

- Investigação inicial: o Acervo monta o painel apenas na pasta aberta, porém ele começa recolhido; o upload atual é sequencial por submit e `fetch`, sem progresso de bytes. A etapa Imagens já oferece ampliação administrativa. O endpoint de grant aceita outras clientes; a criação pelo card já faz o primeiro grant. A spec consolidada ainda permite várias clientes, por isso esta change altera `client-access/folder-audiences` e preserva pastas compartilhadas legadas.
- O proprietário confirmou que cada pasta criada no Acervo deve ser exclusiva de uma cliente, inclusive na API. Melhorias visuais e upload foram autorizados para implementação em desenvolvimento. Nenhum dado real será convertido, revogado ou removido.
- 1.1: `python -m pytest backend/tests/test_derived_galleries.py -q -k 'client_selection_uses_canonical_gallery_without_derivation or restricted_folder_upload_uses_one_jpeg_pipeline_for_two_clients' --tb=short` passou (2 testes). A pasta nova recusa segunda cliente (409) e aceita repetição do grant original; o teste de pasta legada com duas clientes mantém ambas vendo o mesmo derivado e recusa terceira. O runner local emitiu apenas aviso de limpeza do diretório temporário do pytest no encerramento, após exit 0; nenhuma limpeza manual foi executada.
- 1.2: `npm test -- --run app/admin/galleries/client-gallery-card.test.tsx` passou (1 teste). O card mostra destinatárias de uma pasta legada, permite revogação explícita e não renderiza nem chama atribuição adicional.
- 2.1: `npx vitest run app/admin/galleries/folder-processing-panel.test.tsx app/admin/galleries/client-gallery-card.test.tsx --maxWorkers=1` passou (6 testes). No Acervo, o painel monta expandido sem segunda seta nem PATCH; a etapa Imagens conserva a abertura manual. O desmontar aborta a consulta e o teste existente confirma fim do polling ao recolher.
- 2.2: a mesma regressão focal passou com 7 testes depois de incluir ampliação. Foto do Acervo e versões antes/depois usam somente endpoints administrativos de prévia; o diálogo fecha por botão ou Escape e devolve foco ao acionador.
- 3.1: `npx vitest run app/upload-jpeg.test.ts --maxWorkers=1` passou (4 testes). Chamadas antigas permanecem em `fetch`; a variante com callback usa progresso real de bytes e retenta o mesmo PUT após 503, propagando erro sem sucesso falso.
- 3.2: `npx vitest run app/admin/galleries/client-gallery-card.test.tsx --maxWorkers=1` passou (2 testes). A seleção inicia upload sem submit, exibe 50% dos bytes do arquivo em curso, mantém contagem após falha, retenta só o arquivo falho e reutiliza sua chave estável. O input e a abertura/recolhimento do Acervo são desabilitados durante o lote; a guarda síncrona impede segundo início concorrente.
- Integração até aqui: `npx vitest run --maxWorkers=1` passou (50 arquivos, 347 testes) após reconciliar um teste legado que esperava compartilhamento; `npm run build` passou com TypeScript e rotas Next; `npm run lint` terminou com 0 erros e 37 avisos, sem falha; `npx tsc --noEmit`, `python -m ruff check backend/app backend/tests`, três testes de API direcionados e `openspec validate --strict --all` passaram (68 itens). O ajuste final de foco do diálogo foi coberto por 8 testes focais. `git diff --check` passou. Docker Desktop local não expõe o daemon Linux (`npipe:////./pipe/dockerDesktopLinuxEngine` ausente), logo build de imagem Docker não foi executado e a tarefa 4.1 permanece pendente; não há tentativa de alterar a infraestrutura compartilhada. Nenhum teste autenticado em homologação foi declarado.
