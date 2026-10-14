# Validação — cards de foto do editor administrativo

## Diagnóstico

- A imagem fornecida mostra a etapa Imagens do editor da galeria pública, dentro da segunda pasta, e não a apresentação de fotos da cliente. O elemento afetado é `.folder-photo-grid` em `gallery-editor.tsx`.
- Reprodução local com a página real e APIs/imagens sintéticas interceptadas. Antes da correção, em 320, 360 e 390 px o documento tinha scroll horizontal e dois cards com nomes longos possuíam `scrollWidth > clientWidth`. Em 390 px, a imagem do segundo card interceptou o clique de ampliação do primeiro. O nome longo também impedia usar o botão Fechar da prévia ampliada em 320 px.
- Causa: o grid interno do artigo tinha coluna implícita de mínimo automático; o nome sem espaços definia uma largura intrínseca maior que o card. O botão e a imagem a 100% acompanhavam essa coluna alargada. O grid externo usava mínimo rígido de 145 px mesmo quando o espaço disponível era inferior.

## Alteração

- CSS restrito à grade administrativa: mínimo responsivo da coluna externa, coluna interna `minmax(0,1fr)`, quebra de nomes/status, botão e imagem limitados à largura do card. Nome do diálogo de ampliação também quebra linha. A API, dados, arquivo da foto, enquadramento e ações não foram modificados.
- Script `frontend/scripts/folder-photo-visual-qa.cjs` cria duas pastas e três imagens sintéticas (retrato, paisagem e quadrada), visita a página real e verifica limites medidos em DOM, troca de pasta, seleção e ampliação. Intercepta todas as APIs; métodos de mutação retornam 405. Os arquivos visuais ficam em `%TEMP%/pick-your-pic-folder-photo-qa` ou no diretório especificado por `FOLDER_QA_OUTPUT`.

## Evidência após correção

- Edge headless: 320, 360, 390, 768 e 1440 px × temas claro e escuro. Em todas as dez combinações: documento sem overflow; três cards inteiramente dentro da grade; imagem, nome e controles contidos; seleção, ampliação e botão Fechar funcionais; zero chamadas de mutação; zero erros de página. Resultado em `%TEMP%/pick-your-pic-folder-photo-after/results.json` e capturas correspondentes. Captura de 390 px inspecionada.
- 52 testes existentes do editor passaram. `npm run lint` passou sem erros, com 28 avisos preexistentes em arquivos sem alteração. Build Next.js com TypeScript passou, 22 rotas estáticas geradas. `openspec validate fix-admin-folder-photo-overflow --strict --no-interactive` e `git diff --check` passaram.
- Na preparação da branch `feature/fix-admin-folder-photo-overflow`, os 52 testes do editor, lint (0 erros/28 avisos), build/TypeScript e validação OpenSpec estrita passaram novamente. O arquivo `results.json` do QA sintético anterior contém dez cenários sem overflow.

## Integração e escopo

- Nenhuma foto, banco ou sessão real de homologação foi acessada. Não há alteração de backend, migration, segredo ou infraestrutura.
- Alterações preexistentes em outras changes, `backend/app/facial/purge.py` e `.codex-tmp` permanecem preservadas.
- Revisão final: um arquivo CSS de produção alterado, um script QA sintético e os artefatos OpenSpec desta change; nenhum arquivo de aplicação adicional.
- O envio da branch desta correção não executa deploy; a integração e qualquer publicação em homologação/produção seguem os gates operacionais do projeto. O aceite anterior para integrar o PR #99 referia-se àquela mudança e não a esta.
