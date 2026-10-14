## ADDED Requirements

### Requirement: Prévias carregáveis no histórico de compras

O sistema SHALL apresentar miniaturas e ampliação das prévias protegidas dos itens de compras da cliente autenticada, usando rotas de mídia autorizadas e mantendo a grade de duas colunas no mobile e quatro no desktop. A expiração de seleção SHALL NOT impedir o acesso a prévias históricas ainda retidas e autorizadas. O sistema SHALL NOT usar originais, prévias administrativas ou acesso anônimo como alternativa de carregamento.

#### Scenario: Cliente abre compra confirmada
- **WHEN** a cliente abre as fotos de um pedido próprio confirmado cuja prévia está disponível
- **THEN** a miniatura e a ampliação carregam a imagem protegida correspondente, sem navegar para uma página HTML em lugar da mídia

#### Scenario: Compra com comunicação ainda em revisão
- **WHEN** a cliente abre uma compra com pagamento comunicado e prévia operacional disponível
- **THEN** a mídia é exibida pelo acesso autorizado existente sem apresentar o pedido como confirmado

#### Scenario: Histórico conservado após expiração
- **WHEN** a seleção expirou e a cliente consulta um item histórico retido e autorizado
- **THEN** a prévia histórica continua acessível sem reabrir seleção nem permitir recompra indevida

#### Scenario: Mídia indisponível ou acesso negado
- **WHEN** não existe prévia válida, o arquivo falha ao carregar ou a sessão não possui autorização
- **THEN** a interface apresenta estado curto de indisponibilidade ou acesso requerido, sem imagem quebrada sem tratamento, sem substituir por original e sem revelar mídia de terceiros

### Requirement: Prazo restante de seleção explícito e contextual

O sistema SHALL apresentar data/hora limite e tempo restante de seleção a partir da data efetiva autoritativa do backend. A cliente SHALL vê-los na galeria de seleção e na jornada correspondente da biblioteca quando houver prazo efetivo de seleção, mesmo sem fotos no carrinho. O rótulo SHALL distinguir o prazo para novas seleções do estado de compras congeladas ou confirmadas. O sistema SHALL conservar a regra existente de criação/herança da data da privada e SHALL NOT reiniciar, estender ou inventar prazo no navegador.

#### Scenario: Prazo vigente
- **WHEN** existe data efetiva futura para a seleção autorizada
- **THEN** a interface mostra texto curto com dias/horas/minutos restantes e data/hora limite, sem exigir recarregar a página para atualizar a contagem

#### Scenario: Vencimento com página aberta
- **WHEN** a contagem alcança a data limite
- **THEN** o estado deixa de anunciar tempo disponível, não mostra números negativos e usa a validação autoritativa existente para bloquear seleção/checkout e oferecer reabertura

#### Scenario: Compras preservadas
- **WHEN** a cliente possui pedido comunicado ou confirmado e a seleção expira
- **THEN** a compra permanece em seu estado financeiro e o texto de prazo não sugere que a compra ou o pagamento expira

#### Scenario: Data ausente ou prazo padrão ainda não materializado
- **WHEN** não há data absoluta efetiva e existe apenas uma duração padrão configurada na pública
- **THEN** a interface não fabrica uma contagem regressiva nem uma data nova; distingue configuração padrão de prazo já iniciado

#### Scenario: Prazo administrativo alterado ou reabertura aprovada
- **WHEN** a cliente recebe do backend uma nova data efetiva autorizada
- **THEN** a contagem passa a usar essa data, sem reutilizar um vencimento local anterior
