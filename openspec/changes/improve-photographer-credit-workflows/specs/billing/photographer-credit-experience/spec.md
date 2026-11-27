# Spec Delta

## Purpose

Esta capability define como fotógrafos aprovados acompanham créditos, encontram pacotes disponíveis e como o proprietário localiza a carteira de cada fotógrafo.

## ADDED Requirements

### Requirement: Acompanhamento da carteira durante o envio

O fluxo de envio SHALL apresentar saldo e estados de crédito usando respostas confirmadas pelo servidor, sem calcular débito financeiro no navegador.

#### Scenario: Início de envio em carteira finita

- **WHEN** um fotógrafo ativo inicia o envio de conteúdo com carteira finita
- **THEN** a tela mostra um contador compacto de créditos disponíveis junto ao progresso do envio e identifica separadamente as reservas informadas pelo servidor

#### Scenario: Resultado confirmado por arquivo

- **WHEN** o servidor confirma o consumo ou a liberação da operação de um arquivo
- **THEN** a tela atualiza o estado daquele arquivo e os totais da carteira a partir da resposta ou de uma nova leitura autorizada

#### Scenario: Resultado de upload ainda incerto

- **WHEN** a resposta não permite determinar se a operação foi confirmada ou liberada
- **THEN** a tela informa que o resultado está pendente de reconciliação e não afirma que o crédito foi consumido nem devolvido

#### Scenario: Carteira ilimitada do proprietário

- **WHEN** o proprietário usa o fluxo de envio
- **THEN** a tela representa a carteira como ilimitada e não exibe consumo finito fictício

### Requirement: Perfil do fotógrafo pesquisável pelo proprietário

O cadastro automatizado SHALL associar ao tenant o nome informado pelo fotógrafo e o e-mail administrativo após verificar o e-mail e definir senha; a busca do proprietário SHALL localizar o tenant por ambos quando houver nome persistido.

#### Scenario: Cadastro de novo fotógrafo

- **WHEN** um fotógrafo conclui o cadastro automatizado após verificar o e-mail e definir senha
- **THEN** o perfil ativado preserva o nome do fotógrafo e o e-mail associados à conta
- **AND** uma conta legada sem nome informado permanece sem nome, sem inferência ou backfill

#### Scenario: Busca por nome ou e-mail

- **WHEN** o proprietário digita parte do nome do fotógrafo ou do e-mail administrativo
- **THEN** sugestões correspondentes aparecem sem exigir botão separado de busca

### Requirement: Pesquisa de carteira autorizada

A pesquisa de fotógrafos e a abertura dos detalhes da carteira SHALL estar disponíveis somente ao proprietário autorizado.

#### Scenario: Seleção de sugestão pelo proprietário

- **WHEN** o proprietário seleciona uma sugestão
- **THEN** a tela abre os dados existentes de saldo e histórico da carteira daquele tenant

#### Scenario: Tentativa por outro papel

- **WHEN** um fotógrafo, cliente ou operador técnico consulta a pesquisa global
- **THEN** o servidor nega a consulta sem revelar a lista de tenants

### Requirement: Consulta explícita e ordenação de fotógrafos

A interface do proprietário SHALL iniciar sem filtro selecionado e sem lista de fotógrafos. SHALL oferecer Todos, Ordem alfabética e Mais recentes, com busca combinável por nome persistido e e-mail administrativo, paginação no servidor e seleção que abre a carteira correta. A implementação MUST usar somente dados já persistidos, sem inferir nomes nem fazer backfill.

#### Scenario: Estado inicial e limpeza

- **WHEN** a página é aberta ou a pessoa aciona Limpar
- **THEN** não há opção selecionada, busca, sugestões ou carteira selecionada; nenhuma listagem global é consultada antes da ação de busca ou filtro

#### Scenario: Todos e paginação

- **WHEN** o proprietário escolhe Todos
- **THEN** a lista exibe o conjunto consultável de tenants em páginas de até 20 itens, com ordem estável por UUID e indicação de mais resultados; o servidor não carrega o ledger de cada sugestão

#### Scenario: Busca por nome ou e-mail

- **WHEN** o proprietário digita parte do nome informado no cadastro ou do e-mail administrativo
- **THEN** o endpoint owner-only retorna sugestões correspondentes com identidade mínima e sem carteira/ledger por item
- **AND** uma conta sem nome continua encontrável por e-mail

#### Scenario: Ordem alfabética

- **WHEN** o proprietário escolhe Ordem alfabética
- **THEN** o servidor ordena pelo nome persistido e usa o e-mail administrativo como fallback somente quando ele identifica um único administrador ativo
- **AND** identidade ambígua sem nome fica ao final e UUID desempata sem ordenar por e-mail oculto

#### Scenario: Mais recentes e busca combinada

- **WHEN** o proprietário escolhe Mais recentes e opcionalmente digita um trecho do nome ou do e-mail
- **THEN** o servidor ordena os tenants correspondentes pela data de criação decrescente, com UUID para desempate; mudança de consulta reinicia a paginação e ignora respostas anteriores

#### Scenario: Autorização da listagem

- **WHEN** fotógrafo, cliente ou operador técnico tenta consultar Todos ou alguma ordenação
- **THEN** o servidor nega a consulta global sem revelar itens

### Requirement: Catálogo de pacotes para fotógrafos aprovados

Somente um fotógrafo autenticado, aprovado e ativo SHALL visualizar os pacotes ativos configurados pelo proprietário para compra.

#### Scenario: Catálogo logo abaixo da carteira

- **WHEN** um fotógrafo autenticado e ativo abre a área de créditos
- **THEN** a carteira aparece primeiro e o catálogo dos pacotes ativos retornados pelo servidor aparece logo abaixo dela

#### Scenario: Nenhum pacote ativo

- **WHEN** não há pacotes ativos disponíveis
- **THEN** a tela informa que não há pacotes disponíveis sem criar uma oferta padrão

#### Scenario: Conta não ativada

- **WHEN** uma candidatura está pendente, rejeitada ou não provisionada
- **THEN** a pessoa não acessa o catálogo nem inicia compra de créditos

### Requirement: Cards de pacote elegantes e dinâmicos

Os cards SHALL apresentar os dados comerciais do pacote retornados pelo servidor em uma interface mobile-first, elegante, responsiva e alinhada ao sistema visual da plataforma.

#### Scenario: Conteúdo do card

- **WHEN** um pacote ativo é exibido
- **THEN** seu card mostra nome, descrição disponível, quantidade de créditos e preço/moeda definidos pelo servidor, sem inventar desconto, preço ou vantagem promocional

#### Scenario: Estado interativo do card

- **WHEN** a pessoa navega por toque, teclado ou ponteiro e seleciona um pacote
- **THEN** o card apresenta estados de foco, seleção, carregamento e indisponibilidade que distinguem a ação atual sem esconder dados essenciais

#### Scenario: Movimento reduzido

- **WHEN** a preferência do dispositivo reduz movimento
- **THEN** transições decorativas dos cards respeitam essa preferência sem impedir seleção ou leitura

### Requirement: Compra iniciada pelo pacote selecionado

A seleção de pacote SHALL abrir o checkout transparente Mercado Pago dentro da plataforma, usando somente a conta configurada pelo proprietário para receber fotografias. O servidor SHALL identificar o tenant comprador pela sessão e o recebedor pela identidade global do proprietário.

#### Scenario: Iniciar compra pelo card ou botão

- **WHEN** o fotógrafo clica no card ou no botão de compra de um pacote ativo
- **THEN** a aplicação abre o checkout transparente existente dentro da plataforma e envia somente o identificador do pacote, sem tratar preço, quantidade, comprador ou recebedor informados pelo navegador como autoridade

#### Scenario: Mercado Pago como único provedor padrão

- **WHEN** a conta Mercado Pago configurada pelo proprietário está ativa e disponível
- **THEN** Mercado Pago é o único provedor habilitado por padrão para comprar créditos e o PIX interno do sistema não é oferecido

#### Scenario: Comunicação do pagamento ao fotógrafo

- **WHEN** o fotógrafo consulta o catálogo de créditos
- **THEN** o texto SHALL informar o pagamento pelo Mercado Pago na plataforma e SHALL NOT explicar que o PIX interno não participa da compra; essa revisão de texto não modifica os provedores ou meios de pagamento autorizados

#### Scenario: Conta recebedora indisponível

- **WHEN** a conta Mercado Pago do proprietário está ausente, desabilitada ou indisponível
- **THEN** a compra não é enviada a outra conta nem substituída pelo PIX interno e a tela informa indisponibilidade

#### Scenario: Confirmação financeira

- **WHEN** o pagamento permanece pendente, falha ou é confirmado
- **THEN** a interface apresenta o estado retornado pela compra e só mostra créditos disponíveis depois da confirmação autoritativa prevista no fluxo Mercado Pago


### Requirement: Histórico de consumo agrupado por pasta

O histórico do fotógrafo e a visão autorizada do proprietário SHALL apresentar uma linha por pasta para os consumos confirmados de uploads, com referência da pasta, data e hora do último envio confirmado, quantidade de fotos cobradas e total de créditos consumidos. O ledger individual MUST permanecer preservado. Compras, concessões, revogações e estornos SHALL continuar individualizados.

#### Scenario: Pasta com muitos uploads e novos envios

- **WHEN** uma pasta possui mais consumos que o limite de movimentos recentes ou recebe novos uploads
- **THEN** o servidor calcula seu resumo sobre todos os consumos confirmados dessa pasta antes de paginar os resumos e atualiza a mesma linha, sem total parcial baseado apenas nos últimos30lançamentos

#### Scenario: Resumo habitual com rastreabilidade interna

- **WHEN** a pessoa abre o histórico
- **THEN** cada resumo mostra nome da pasta, galeria, referência da pasta, data/hora do último envio, quantidade de fotos cobradas e débito total; a interface habitual SHALL NOT exibir expansão ou listagem por foto, e os registros individuais SHALL permanecer preservados internamente para investigação autorizada

#### Scenario: Retry, reserva liberada e capa

- **WHEN** há retries, reindexações, reservas liberadas ou capas
- **THEN** somente lançamentos confirmados de upload_consumption integram a quantidade e o débito do resumo; não há segundo consumo nem quantidade fictícia

#### Scenario: Nome alterado ou pasta removida

- **WHEN** uma pasta é renomeada ou removida após consumos registrados com proveniência
- **THEN** sua identidade e totais permanecem únicos e auditáveis, usando o nome atual enquanto existir e os metadados preservados do evento após remoção; o histórico não concede acesso a mídia removida

#### Scenario: Legado sem vínculo comprovável

- **WHEN** um consumo anterior não possui snapshot e já não tem vínculo real com a pasta
- **THEN** o movimento permanece individualizado internamente e a interface informa a existência de consumos anteriores sem pasta identificável, sem expor cada operação, sem inferência por nome/chave de arquivo e sem agrupamento artificial de origens desconhecidas

#### Scenario: Isolamento e paginação

- **WHEN** um fotógrafo consulta histórico ou detalhes de pasta de outro tenant, ou alguém sem papel de proprietário consulta a visão global
- **THEN** a API nega sem revelar movimentos; consultas permitidas usam limite validado, paginação server-side, ordem estável e private,no-store, sem enviar todos os movimentos individuais ao carregar o resumo
