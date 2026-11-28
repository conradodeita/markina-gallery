# Tasks

## 1. Visão Geral do fotógrafo

- [x] 1.1 Reconstruir a composição Dourado Claro em `/admin`, incluindo navegação lateral e cabeçalho, preservando dados autenticados, carteira, ações e atalhos existentes.
- [ ] 1.2 Exercitar as respostas do backend, carteira, navegação e resoluções de celular e desktop. Comparar com a tela de referência, revisar o escopo, executar testes direcionados, lint, checagem de tipos e build aplicáveis e registrar a demonstração.

### Evidência de validação local

- A comparação com a imagem e o HTML da tela Dourado Claro confirmou barra lateral de 264 px, cabeçalho de 64 px, ações à direita do hero no desktop, indicadores em 3+2 com ícones, três etapas de publicação e galerias em duas colunas. Galerias mostram «Sem capa» porque o resumo não inclui esse campo. Carteira, seleções e avisos seguem os dados e estados da aplicação.
- Edge automatizado no servidor de desenvolvimento com respostas sintéticas: 1280 px em 3+2, 390 px e 320 px em uma coluna, sem rolagem horizontal. Menu recolhível, foco visível, atalho para o conteúdo, tema claro/escuro, conta e a requisição do filtro de Galerias foram verificados. Os glifos de importação, vendas, prática e tema foram renderizados pela fonte local.
- No ambiente local autenticado com backend e dados de teste, a coordenação confirmou HTTP 200, título, saldo de 24 créditos e ausência de rolagem horizontal em 1440 px e 390 px.
- Vitest passou 20 testes de Visão Geral, navegação, onboarding e componentes. Os testes de carteira exercitam carregamento independente, saldo finito/ilimitado, histórico vazio, movimentação e erro.
- TypeScript e OpenSpec estrito passaram. O ESLint retornou zero erros e manteve o aviso preexistente de `<img>` na lista de Galerias.
- A revisão removeu grades globais exclusivas da Visão Geral que ficaram sem consumidores. O build final segue como verificação de CI e a tarefa continua aberta até essa evidência.

### Roteiro da demonstração

1. Entrar como fotógrafo de teste e abrir a Visão Geral. Conferir barra lateral, indicadores, ritual e galerias recentes.
2. Acionar a busca e digitar um termo no filtro da lista de Galerias. Voltar à Visão Geral e alternar entre os temas.
3. Conferir saldo e movimentações. Reduzir a janela para celular, abrir o menu e navegar pelo teclado.

## 2. Galerias

- [x] 2.1 Adaptar a lista autenticada conforme o Stitch, com busca real, capas autorizadas, estados de carregamento/vazio/erro, alternância de apresentação e atalhos existentes.
- [x] 2.2 Verificar contratos e renderização no desktop e celular, incluindo capa, abertura da galeria e rótulos coerentes com a resposta.

- Com backend local e sessão de teste da conta A, a resposta exibiu três registros e a fonte «Piloto abstrato A». Uma busca inexistente mostrou o estado vazio e a busca «Piloto» restaurou o cartão. A tela coube em 1440 px e 390 px.
- No Edge com respostas sintéticas, a lista coube em 1280, 390 e 320 px e exibiu capa quando fornecida, marcador sem capa e os dois modos de apresentação. O link abriu o detalhe da galeria e manteve o atalho existente de edição. Mudanças rápidas de consulta descartam a resposta de solicitações canceladas.

## 3. Clientes

- [x] 3.1 Adaptar o diretório autenticado conforme o Stitch, com resumo da lista, busca, linhas responsivas e formulários protegidos existentes.
- [x] 3.2 Verificar contratos e renderização no desktop e celular, incluindo paginação, estados do diretório, cadastro e edição.

- Com o backend local autenticado, a conta de teste A exibiu três clientes e a B não exibiu resultados. O diretório coube no desktop e em 390 px. A busca inexistente apresentou o estado vazio e Editar abriu, em 390 px, o diálogo da cliente «Sintética A0» com o nome retornado.
- Com respostas sintéticas, Edge passou em 1280, 390 e 320 px, incluindo paginação por cursor, busca, CTA até o formulário e abertura do editor. O cadastro e as operações autorizadas de edição/exclusão continuam cobertos pelos testes do diretório.

### Verificações compartilhadas

- Vitest passou 60 testes direcionados em oito arquivos. TypeScript, ESLint e OpenSpec estrito passaram. Os estilos substituídos sem consumidores foram retirados.
- A regressão do instalador PWA foi corrigida preservando uma única instância na raiz e o contrato de registro do service worker. O ensaio no Edge simulou a disponibilidade do instalador e confirmou que o botão continuou único ao navegar entre Clientes e Galerias.
- Build e suíte completa seguem na CI da PR.
