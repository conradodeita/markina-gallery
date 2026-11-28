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

## 10. Resumo da Galeria pública

- [x] 10.1 Aplicar o layout Stitch com capa, resumo, pastas, busca de clientes e ações existentes.
- [x] 10.2 Validar desktop e celular, estados da capa e das pastas, busca, navegação e abertura segura da confirmação de exclusão.

- Edge em 1440, 390 e 320 px verificou capa renderizada ou ausente, estado do link protegido, atalhos de edição/prévia/pasta, busca por telefone e inventário de exclusão cancelado sem escrita. As respostas foram sintéticas e a página coube nas três larguras.
- Vitest passou 110 testes em cinco arquivos, incluindo cenários de exclusão simulada e cartões de clientes. TypeScript, ESLint e OpenSpec estrito passaram, com avisos preexistentes no arquivo amplo de testes do editor.

## 11. Pedidos da galeria

- [x] 11.1 Adaptar a consulta ao Stitch com métricas reais, busca, filtros e snapshots.
- [x] 11.2 Conferir desktop e celular, cálculo local de contagens, busca e instruções protegidas.

- Edge em 1440, 390 e 320 px exibiu o total confirmado sem contar cancelados, preservou carrinho reaberto, executou busca por nome com acento e por ID e combinou filtro de situação, sem rolagem horizontal ou nova consulta causada pelos filtros. O snapshot PIX foi visível somente no pedido pendente do ensaio. Todas as requisições do teste foram de leitura sobre respostas sintéticas.
- Vitest passou 28 testes em cinco arquivos. TypeScript, ESLint e OpenSpec estrito passaram.

## 12. Ajustes da galeria

- [x] 12.1 Adaptar a primeira etapa do editor conforme Stitch, preservando trilha, metadados e modos de acesso existentes.
- [x] 12.2 Validar navegação, rascunho, patch de ajuste e avanço em desktop e celular.

- Edge em 1440, 390 e 320 px verificou a etapa ativa e a rota da prévia, cancelou a saída com rascunho e conferiu PATCH sintético. Um HTTP 422 preservou o título; o segundo envio, aceito, avançou para Vendas com os campos e o modo selecionado. As três larguras ficaram sem rolagem horizontal.
- Vitest passou 97 testes em quatro arquivos, incluindo preservação do modo legado. TypeScript e OpenSpec estrito passaram. ESLint manteve quatro avisos preexistentes de imagens em outras etapas do editor.

## 13. Vendas da galeria

- [x] 13.1 Aplicar o layout Stitch aos controles comerciais existentes.
- [x] 13.2 Validar a alternância de preço, simulação, persistência e avanço em desktop e celular.

- Edge em 1440, 390 e 320 px verificou a mudança de preço fixo para progressivo, o vínculo a tabela, o GET da simulação por quantidade, o link de Configurações do PIX, o PUT da regra selecionada e o avanço a Detalhes. As operações foram simuladas e a largura da página coube nos três tamanhos.
- Vitest passou 78 testes em quatro arquivos. TypeScript, OpenSpec estrito e ESLint passaram, com os avisos preexistentes de imagens em outras etapas do editor.

## 14. Detalhes e apresentação

- [x] 14.1 Adaptar a etapa ao Stitch, com capa e tipografia, prévia em destaque e estados do processamento.
- [x] 14.2 Validar desktop e celular, bloqueio de capa ausente e atualização da prévia e do salvamento.

- Edge em 1440 e 390 px confirmou imagem de teste, atualização imediata de posição/tamanho, envio sintético e avanço. Em 320 px a capa ausente desabilitou o salvamento e mostrou instruções. Não houve rolagem horizontal nem upload real.
- Vitest passou 97 testes em quatro arquivos, incluindo fluxo de processamento e foto de capa obrigatória. TypeScript, OpenSpec estrito e ESLint passaram. Os três avisos de imagens do editor pertencem às outras etapas.

## 15. Imagens e pastas

- [x] 15.1 Aplicar a composição Stitch à organização, catálogo e conteúdo da pasta, preservando controles, crédito e upload existentes.
- [x] 15.2 Verificar layout, criação sintética, organização, abertura da pasta e política de mídia indisponível.

- Edge em 1440, 390 e 320 px confirmou organização cronológica, POST sintético com prazo de 30 dias, indicação da taxa retornada e abertura da pasta em arquivo frio, com upload bloqueado e atalho para recuperação em Créditos. Não houve upload, recuperação ou débito real, nem rolagem horizontal.
- Vitest passou 86 testes em cinco arquivos, incluindo pastas, processamento e créditos durante envio. TypeScript, OpenSpec estrito e ESLint passaram, com avisos existentes de imagens.

## 16. Clientes e acesso da galeria

- [x] 16.1 Adaptar a última etapa ao Stitch, mantendo o link e os controles de vínculo autorizados.
- [x] 16.2 Verificar desktop e celular, consulta, busca e vínculo sintéticos e confirmação de desvinculação.

- Edge em 1440, 390 e 320 px verificou estados de link disponível e legado, busca do diretório, vínculo por PUT sintético e abertura da confirmação de desvinculação. Cancelar não enviou DELETE. O link da fixture era sintético e as três larguras ficaram sem rolagem horizontal.
- Vitest passou 88 testes em quatro arquivos. TypeScript, OpenSpec estrito e ESLint passaram, com avisos preexistentes de imagens em outras etapas.

## 17. Detalhe da Galeria privada

- [x] 17.1 Adaptar o detalhe administrativo ao Stitch, mantendo acervo, membros, status e ações existentes.
- [x] 17.2 Validar membros, indicação de estados, atalhos e confirmação cancelável em desktop e celular.

- Edge em 1440, 390 e 320 px verificou membro sintético, referência do acervo público, atalho aos pedidos, âncora de revisão, configuração herdada e cancelamento de bloqueio e exclusão. Não houve mutação e a página coube nos três tamanhos.
- Vitest passou 19 testes em quatro arquivos, incluindo crédito durante envio e confirmação de bloqueio. TypeScript, OpenSpec estrito e ESLint passaram, com os avisos anteriores de imagem do acervo.

## 18. Configuração comercial da Galeria privada

- [x] 18.1 Aplicar o Stitch à consulta autorizada da herança comercial.
- [x] 18.2 Validar em desktop e celular preço fixo/progressivo, ausência de dados e links funcionais.

- Edge validou faixa progressiva e versão em 1440 px, preço fixo em 390 px e resposta indisponível em 320 px. Os links levaram à origem e às Configurações do PIX, com consultas GET sintéticas e sem rolagem horizontal.
- Vitest passou oito testes em três arquivos. TypeScript, ESLint, OpenSpec estrito e a verificação de segredos passaram.

## 19. Prévia administrativa da Galeria pública

- [x] 19.1 Aplicar a apresentação Stitch sem alterar as proteções de mídia e a apresentação compartilhada.
- [x] 19.2 Validar capa, pastas, ampliação, modo fotógrafo e estados de consulta em desktop e celular.

- Edge em 1440 px verificou capa e ampliação com fechamento por Escape; em 390 px, prévia parcial com a foto disponível; em 320 px, falha total e retorno. As respostas foram sintéticas e não houve mutações nem rolagem horizontal.
- Vitest passou 22 testes em três arquivos. ESLint, TypeScript, OpenSpec estrito, diff-check e a verificação de segredos passaram.

## 20. Biblioteca da cliente

- [x] 20.1 Adaptar Suas galerias ao Stitch, mantendo acesso, prazos e histórico da sessão da cliente.
- [x] 20.2 Validar desktop e celular, filtros, caminhos de acesso, consulta vazia e recuperação após falha.

- Edge em 1440 e 390 px verificou filtros, capa, prazo, navegação de carrinho e saída para Compras. Em 320 px, simulou falha e nova tentativa com lista vazia. Usou respostas sintéticas em ambos os temas, sem escrita ou rolagem horizontal.
- Vitest passou 22 testes, incluindo biblioteca, carrinho e contrato PWA. TypeScript, ESLint, OpenSpec estrito, diff-check e a verificação de segredos passaram.

## 21. Galeria da cliente

- [x] 21.1 Aplicar o Stitch à coleção autenticada, preservando todos os fluxos de acesso e seleção existentes.
- [x] 21.2 Validar em desktop e celular acesso, prazo, seleção, ampliação e recuperação de falha em respostas sintéticas.

- Edge em 1440, 390 e 320 px verificou capa, navegação de pastas, seleção e acesso ao carrinho. Em 1440 px, abriu e fechou a prévia protegida; em 390 px, confirmou a solicitação sintética da pasta expirada; em 320 px, recuperou a grade após falha. A interceptação confirmou os POSTs previstos. Houve zero rolagem horizontal.
- Vitest passou 75 testes, incluindo proteção de mídia, isolamento de pastas, busca facial, reabertura e contrato PWA. TypeScript, ESLint, OpenSpec estrito, diff-check e verificação de segredos passaram. Permanecem os avisos de imagem da apresentação compartilhada.

## 22. Minhas compras

- [x] 22.1 Adaptar o histórico ao Stitch mantendo agrupamento, estado financeiro e entrega autorizada.
- [x] 22.2 Validar desktop e celular, pagamento ativo, compra histórica, entrega, prévia e erro de consulta.

- Edge em 1440 e 390 px verificou grupos Mercado Pago e InfinitePay, link autorizado de álbum e ampliação/fechamento por Escape com retorno do foco. Em 320 px, repetiu uma consulta com falha e exibiu o histórico vazio. As respostas foram sintéticas, sem escrita nem rolagem horizontal.
- Vitest passou 29 testes, incluindo entrega, histórico e integração de apresentação Mercado Pago. TypeScript, ESLint, OpenSpec estrito, diff-check e verificação de segredos passaram.

## 23. Conferência de prévias

- [x] 23.1 Adaptar o acesso administrativo por identificador, com o visualizador e as proteções existentes.
- [x] 23.2 Validar desktop e celular, acesso autorizado/negado e prévia disponível/indisponível.

- Edge em 1440 px abriu a prévia no endpoint protegido. Em 390 px, verificou a mensagem de indisponibilidade e repetiu a mesma consulta; em 320 px, negou acesso e não consultou a mídia. Nos três casos, a navegação indicou a rota, sem escrita nem rolagem horizontal.
- Vitest passou sete testes de navegação e PWA. TypeScript, ESLint, OpenSpec estrito, diff-check e verificação de segredos passaram.

## 24. Visualização da foto

- [x] 24.1 Aplicar o Stitch à ampliação da cliente, com foto, posição, navegação, zoom e seleção existentes.
- [x] 24.2 Validar desktop e celular, incluindo mudança de foto, zoom, foco e fechamento, sem acesso ao original.

- Edge em 1440, 390 e 320 px verificou 1 de 2 e 2 de 2, zoom de 150%, foco circular com Tab, retorno por Escape e a URL de prévia autorizada. A interceptação registrou apenas as duas visualizações sintéticas esperadas e não houve rolagem horizontal.
- Vitest passou 77 testes com visualizador, galeria, regiões, busca facial e PWA. TypeScript, ESLint, OpenSpec estrito, diff-check e verificação de segredos passaram. Permanecem os avisos anteriores de imagem.

## 25. Carrinho da cliente

- [x] 25.1 Adaptar revisão, resumo do pedido, meios disponíveis e confirmação de comunicação sem alterar os contratos de cobrança.
- [x] 25.2 Validar desktop e celular com dados sintéticos, incluindo grupo sem cobrança, erro, PIX e caminho Mercado Pago.

- Edge em 1440 px verificou grupo, prévia, total, PIX preparado e atalho Mercado Pago. Em 390 px, validou a cópia com clipboard simulado, a revisão e idempotência no POST interceptado e o retorno de comunicação pendente. Em 320 px, repetiu após 503 e finalizou uma seleção sem cobrança. Não houve rolagem horizontal nem chamadas reais de pagamento.
- Vitest passou 38 testes de carrinho, checkout, prévias e PWA. TypeScript, ESLint, OpenSpec estrito, diff-check e verificação de segredos passaram. Permanecem os avisos anteriores de imagem e limpeza de requisição.

## 26. Entrada e confirmação de acesso

- [x] 26.1 Adaptar a entrada e a confirmação da cliente ao Stitch, mantendo marca, convite, fatores e respostas neutras.
- [x] 26.2 Validar desktop e celular, seleção de papel, falta de convite, OTP inválido, reenvio e retorno autorizado em respostas sintéticas.

- Edge em 1440 px verificou a orientação sem convite, troca para Fotógrafo, campos e marca da fixture. Em 390 px, realizou desafio sintético do convite, erro neutro, reenvio e redirecionamento à biblioteca. Em 320 px, exibiu o aviso da galeria privada antes do OTP, seguiu com convite e abriu a biblioteca. Os POSTs de autenticação foram interceptados, sem envio de código real ou rolagem horizontal.
- O painel editorial usa WebP local de 84.796 bytes, sem metadados, carregado em desktop e ausente das requisições nas duas larguras de celular testadas. Vitest passou 70 testes, incluindo sessão, convite, recuperação e PWA. TypeScript, ESLint, OpenSpec estrito, diff-check e verificação de segredos passaram.
