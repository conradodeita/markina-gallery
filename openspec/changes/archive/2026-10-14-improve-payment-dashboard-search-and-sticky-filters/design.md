# Design

## Context

Veja `proposal.md` e `specs/gallery-sales/operational-gallery-interface/spec.md`. A tela financeira já usa `GET /admin/payment-communications?query=...`, mas a consulta textual compara apenas nomes e o formulário está depois de seções extensas. A API autenticada `GET /admin/clients` já pesquisa nome/WhatsApp e retorna um diretório paginado. A navegação administrativa permanece sticky; sua altura muda quando os controles passam a duas linhas em larguras móveis.

## Goals / Non-Goals

**Goals:**

- Completar o filtro existente com telefone e sugestões acessíveis, permitindo escolher uma identidade exata.
- Manter busca livre por partes de nome ou telefone e preservar os demais filtros e a paginação.
- Deixar o filtro compacto acessível abaixo da navegação durante a revisão do painel.

**Non-Goals:**

- Criar uma segunda caixa de busca, alterar as regras financeiras, mostrar telefones nas sugestões, adicionar migration ou mudar outros painéis.

## Decisions

- **Sugestões pela API administrativa de clientes.** Consultar `/api/admin/clients?query=<texto>&limit=8` somente após dois caracteres, com debounce e cancelamento da requisição anterior. A API já exige autenticação, pesquisa por nome e telefone normalizado e ordena resultados por nome. A lista de sugestões apresenta nomes; nenhum endpoint público novo será criado.
- **Identidade exata após escolher sugestão.** Acrescentar `client_id` opcional à consulta financeira. O backend o aplica às consultas de pedidos e seleções antes de calcular agregados e paginação. Se o fotógrafo editar o texto depois da escolha, limpar a identidade selecionada e voltar à busca parcial.
- **Busca textual compatível.** O parâmetro `query` continua aceitando texto parcial. O backend compara nome atual/snapshot e dígitos do telefone cadastrado/snapshot depois de normalizar a entrada, sem serializar telefones adicionais na resposta financeira. Cursor e filtros secundários permanecem válidos.
- **Uma barra compacta antes do painel.** Reorganizar o filtro atual para ficar imediatamente após a introdução e antes dos indicadores, reaberturas, seleções abertas e pedidos. O campo Cliente/telefone fica disponível na faixa compacta; os controles de galeria, estado e período permanecem no expansor existente.
- **Posição sticky sob a navegação.** Usar `position: sticky` com fundo opaco e elevação de camada inferior à navegação. A faixa fica dentro de um contêiner que cobre todo o painel para continuar sticky durante toda a rolagem. Medir a altura renderizada do cabeçalho administrativo com `ResizeObserver` e atualizar o deslocamento da faixa para acompanhar quebras de linha e mudanças responsivas. Em telas pequenas, manter a faixa compacta sem prender o expansor aberto cobrindo a área útil.
- **Acessibilidade do autocomplete.** Implementar semântica de combobox/listbox, navegação por teclado, indicação de opção ativa, seleção por Enter/clique e fechamento por Escape. Anúncios de carregamento/vazio devem ser acessíveis.

## Risks / Trade-offs

- [A API de sugestões tem paginação e limite] → Consultas curtas e limitadas a oito opções; o filtro textual do backend continua disponível mesmo sem sugestão.
- [A altura do cabeçalho varia em telas pequenas] → Definir e validar deslocamento por breakpoint e viewport, evitando sobreposição e manter o expansor avançado fora do estado sticky aberto.
- [Clientes podem compartilhar nomes parecidos] → Uma sugestão selecionada envia `client_id` e limita a identidade exata; busca parcial continua intencionalmente mostrando correspondências múltiplas.

## Migration Plan

Não há mudança de schema. Publicar frontend e API como parte do release normal; versão anterior continua compatível pois `client_id` é opcional. Reverter o código remove autocomplete, parâmetro opcional e CSS sticky, sem alterar dados.
