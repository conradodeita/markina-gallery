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

## 4. Ajuste do tema claro e do editor de cliente

- [x] 4.1 Ajustar os fundos claro e escuro e validar a rolagem do editor no desktop e celular, incluindo conteúdo ampliado e fechamento.

- Edge confirmou os fundos `#fbfaf8` e `#0e0d0b`, com a rolagem contida no diálogo e a posição da página preservada ao fechar, em 1440×900, 1440×590 e 390×844. O formulário simples coube inteiro em 1440×900. Um inventário sintético de 35 itens exigiu rolagem interna e permitiu alcançar todas as ações.

## 5. Vendas e pagamentos

- [x] 5.1 Aplicar o Stitch à consulta financeira com o mesmo resumo, filtros, exportação, pedidos, seleções e histórico.
- [x] 5.2 Exercitar a visualização responsiva, os estados da lista e os contratos existentes com testes dirigidos.

- Edge com respostas sintéticas confirmou a visualização em 1440, 390 e 320 px, sem rolagem horizontal. O navegador aplicou o provedor PIX, baixou e removeu um CSV sintético, abriu um pedido, alternou para o histórico e confirmou o foco da seleção por link direto.
- Vitest passou 76 testes em oito arquivos, incluindo pedidos, filtros, exportação, regras financeiras, edição de cliente e contrato PWA. A checagem da faixa de filtros mede o cabeçalho integrado e verifica sua posição após os indicadores. ESLint, TypeScript e OpenSpec estrito passaram. Build final segue na CI.

## 6. Nova galeria

- [x] 6.1 Adaptar o formulário inicial ao Stitch, preservando os campos e a criação autorizada.
- [x] 6.2 Validar título obrigatório, envio, erro, retorno e transição para Ajustes no desktop e no celular.

- Edge em 1440, 390 e 320 px, com respostas sintéticas, verificou validação nativa sem POST vazio, resposta 422 que mantém o título e a descrição, envio dos três campos, resposta 201 seguida de Ajustes e retorno por Cancelar sem POST. O formulário ocupa 720 px no desktop, cabe no celular e usa os temas claro e escuro.
- Vitest passou 38 testes em cinco arquivos. Os casos específicos cobrem envio único enquanto ocupado, opcionais vazios como `null`, resultado incerto e cancelamento da espera ao sair. TypeScript, ESLint e OpenSpec estrito passaram. A prova de navegador não persistiu dados; o build final segue na CI.

## 7. Notificações

- [x] 7.1 Aplicar o layout Stitch e os filtros de destinatário à configuração autenticada de notificações.
- [x] 7.2 Validar filtro, abertura de evento, prévia, salvamento e conexão indisponível em desktop e celular.

- Edge passou em 1440, 390 e 320 px sem rolagem horizontal. O ensaio alternou destinatários sem perder o rascunho, conferiu a prévia local, validou o `PUT` com a versão atual, verificou WhatsApp conectado e desconectado e abriu o evento correto pelo link direto. As respostas foram simuladas e o ensaio não disparou mensagens.
- Vitest passou 35 testes em cinco arquivos, incluindo configurações, avisos de mídia fria, navegação e PWA. TypeScript, ESLint e OpenSpec estrito passaram.

## 8. Tabelas de preço progressivo

- [x] 8.1 Adaptar o catálogo e o editor conforme Stitch, com contagens reais e operações existentes por tabela.
- [x] 8.2 Validar desktop e celular, faixas em centavos, edição versionada, desativação confirmada e reativação.

- Edge em 1440, 390 e 320 px validou o atalho de criação, foco do editor, envio de faixas contíguas em centavos, versão seguinte após edição, cancelamento de desativação sem solicitação, confirmação de desativação e reativação. O teste interceptou as requisições e não utilizou dados reais. Todas as larguras couberam sem rolagem horizontal.
- TypeScript, ESLint, OpenSpec estrito e os testes de catálogo de preços, regras de precificação, navegação, PWA e layout passaram.

## 9. Configurações

- [x] 9.1 Aplicar a composição Stitch a Configurações e à área de marca, mantendo grupos e fluxos protegidos.
- [x] 9.2 Verificar navegação por seção, persistência de rascunho, prévia e envio sintético em desktop e celular.

- Edge em 1440, 390 e 320 px confirmou sete grupos, rascunho preservado ao recolher, atualização da entrada após salvar, duas prévias da marca-d’água atualizadas, dois PATCHs sintéticos e abertura por link `#whatsapp`, sem rolagem horizontal.
- Vitest passou 80 testes em 12 arquivos. TypeScript, OpenSpec estrito e ESLint passaram, com aviso preexistente de imagem na prévia da entrada.
