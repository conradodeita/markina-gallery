# Spec Delta

## Purpose

Permitir pagamentos por cartão de crédito na conta InfinitePay do fotógrafo proprietário da compra, com confirmação verificável, isolamento entre contas e coexistência com o PIX manual existente.

## ADDED Requirements

### Requirement: Configuração InfinitePay própria do fotógrafo

O sistema SHALL resolver a configuração InfinitePay pela conta ativa da sessão administrativa. InfiniteTag, versão e estado SHALL pertencer a essa conta. Conta nova SHALL começar sem integração utilizável, sem herdar recebedor de outra conta. Identificador fornecido pelo browser MUST NOT substituir o contexto autorizado.

#### Scenario: Contas independentes
- **WHEN** fotógrafos A e B consultam e alteram suas configurações
- **THEN** cada operação alcança somente a configuração da conta autenticada
- **AND** configurar A não habilita cartão nem modifica o PIX de B

#### Scenario: Conta sem configuração
- **WHEN** a cliente de B abre uma compra e somente A possui InfinitePay configurada
- **THEN** o cartão permanece indisponível para B, sem usar a InfiniteTag de A

### Requirement: Credencial InfinitePay em cofre por fotógrafo

A integração SHALL resolver a API Key por UUID de tenant através de binding de segredo server-side, com aliases únicos e ambiente de credencial compatível. A chave MUST NOT ser persistida em tabela de negócio, mostrada a clientes/fotógrafos, registrada em logs ou incluída em payloads. Somente o serviço API que chama a InfinitePay SHALL receber o segredo. Checkout SHALL permanecer indisponível quando o binding estiver ausente ou inválido.

#### Scenario: Checkout autenticado
- **WHEN** uma conta ativa possui binding próprio e chave configurada no ambiente do servidor
- **THEN** `/links` e `/payment_check` enviam `X-Api-Key` apenas à origem oficial da InfinitePay
- **AND** nenhuma chamada usa a chave ou InfiniteTag de outro tenant

#### Scenario: Binding ausente ou inválido
- **WHEN** o fotógrafo não possui chave ou o binding não corresponde ao ambiente atual
- **THEN** novas emissões de cartão são recusadas antes da reserva e nenhuma chamada externa é feita
- **AND** PIX manual continua disponível conforme sua própria configuração

### Requirement: Alteração do recebedor protegida

Criar, substituir, ativar ou remover configuração SHALL exigir reautenticação e confirmação sensível vinculadas à sessão, conta e proposta, com expiração, limite de tentativas e auditoria minimizada. O sistema MUST NOT solicitar senha, OTP de acesso à InfinitePay ou dados de cartão. InfiniteTag informada SHALL ser identificada como dado declarado, sem afirmar titularidade comprovada só por seu formato.

#### Scenario: Alteração confirmada
- **WHEN** o fotógrafo conclui os fatores locais para a proposta exata
- **THEN** uma nova versão é gravada somente em sua conta
- **AND** cobranças já emitidas conservam o recebedor anterior

#### Scenario: Desafio de outra conta ou proposta alterada
- **WHEN** a confirmação usa desafio estrangeiro, expirado ou conteúdo diferente
- **THEN** a configuração vigente é preservada sem aplicar a alteração

### Requirement: Ativação declarada e confirmação por consulta autoritativa

O cartão SHALL exigir autodeclaração sensível do fotógrafo sobre a conta e os meios habilitados. Essa declaração MUST NOT provar titularidade. A confirmação SHALL depender de `payment_check` correlacionado à conta, compra, transação e valor; dados do navegador MUST NOT confirmar pagamento. Webhook SHALL permanecer indisponível até haver contrato de assinatura documentado.

#### Scenario: Retorno sem consulta autoritativa
- **WHEN** a cliente retorna com identificadores, mas o servidor não consegue confirmar `paid`, método e valor via `payment_check`
- **THEN** a compra não é confirmada nem liberada e permanece aguardando verificação

#### Scenario: Webhook sem assinatura documentada
- **WHEN** o contrato de assinatura do webhook não foi documentado
- **THEN** o fluxo inicial confirma pelo retorno do checkout e `payment_check`, e não expõe um endpoint de webhook financeiro

### Requirement: InfinitePay exclusivamente para cartão de crédito

O fluxo InfinitePay SHALL oferecer somente crédito em checkout hospedado e validar `credit_card` na confirmação. Um retorno PIX SHALL ficar em exceção, sem confirmar a compra nem iniciar cobrança automática. PIX SHALL continuar no fluxo manual. A change MUST NOT habilitar PIX no link InfinitePay enquanto o domínio aceitar somente cartão.

#### Scenario: Opção externa validada
- **WHEN** a cliente escolhe cartão em uma conta habilitada
- **THEN** o checkout externo permite crédito e não oferece PIX
- **AND** PAN, CVV e validade não passam pelo Pick-your-Pic

#### Scenario: Link de pagamento único
- **WHEN** o backend cria um checkout InfinitePay
- **THEN** define `payment_methods_enabled=["credit_card"]` e `single_payment=true` com a autenticação documentada

#### Scenario: Método divergente
- **WHEN** a consulta autoritativa informa `pix` para uma tentativa de cartão
- **THEN** o sistema registra exceção operacional, conserva a evidência e não libera entrega nem cobra novamente

### Requirement: Configuração individual da conta Checkout Integrado

Cada fotógrafo SHALL usar sua própria InfiniteTag e manter cartão ligado e PIX desligado na conta InfinitePay. Antes de liberar recebimento real, SHALL verificar em checkout hospedado, sem pagar, que o link não oferece PIX. A configuração da conta MUST NOT substituir essa verificação.

#### Scenario: Cada fotógrafo configura sua própria conta
- **WHEN** o fotógrafo configura o recebimento InfinitePay no PickYourPic
- **THEN** as chamadas futuras usam somente a InfiniteTag configurada para seu tenant, e a orientação informa que ele deve habilitar o Checkout Integrado e cartão em sua conta própria e desligar PIX nela

#### Scenario: Link hospedado ainda não verificado
- **WHEN** ainda não foi verificado que um link da conta com PIX desligado oferece somente cartão
- **THEN** o PickYourPic mantém o cartão indisponível para clientes e não habilita cobranças reais com base apenas na seleção da conta

### Requirement: Coexistência independente com PIX manual

A revisão SHALL oferecer os meios utilizáveis da conta proprietária. PIX SHALL continuar usando seu recebedor, snapshot e confirmação manual atuais. Cartão SHALL depender somente da configuração e dos gates próprios. Compra sem exigência de pagamento SHALL continuar sem gerar cobrança externa. Cartão indisponível MUST NOT impedir um PIX válido.

#### Scenario: PIX de A preservado
- **WHEN** A configura, altera ou desabilita InfinitePay
- **THEN** a chave, versão, instruções e confirmações de seu PIX permanecem operáveis
- **AND** pedidos antigos e configurações de B não são reescritos

#### Scenario: PIX ausente e cartão utilizável
- **WHEN** a conta possui cartão habilitado e PIX não configurado
- **THEN** a cliente pode escolher cartão sem configurar ou simular PIX

#### Scenario: Seleção sem pagamento obrigatório
- **WHEN** a cliente finaliza uma galeria que não exige pagamento
- **THEN** o fluxo existente conclui a seleção sem receita e sem chamada à InfinitePay

### Requirement: Habilitação explícita de cartão por fotógrafo

Cada fotógrafo SHALL poder habilitar cartão sob confirmação sensível e versionada. Novos checkouts SHALL exigir configuração pronta e `card_enabled=true`, inicialmente falso. Desabilitar MUST NOT cancelar, ocultar ou liberar reservas de links já emitidos que ainda possam ser pagos.

#### Scenario: Cartão desabilitado
- **WHEN** o fotógrafo desabilita cartão em Configurações
- **THEN** o cartão deixa de ser oferecido para novas compras desse fotógrafo
- **AND** PIX manual e compras sem pagamento continuam funcionando

#### Scenario: Link existente após desativar novos checkouts
- **WHEN** o fotógrafo desabilita cartão enquanto há uma compra pendente com link emitido
- **THEN** o link continua acessível em Compras até confirmação ou conciliação
- **AND** as fotos continuam reservadas enquanto o link puder ser pago

#### Scenario: Reativação protegida
- **WHEN** o fotógrafo habilita novamente cartão com configuração InfinitePay ativa
- **THEN** a alteração exige reautenticação/confirmação local e novas compras podem oferecer cartão
- **AND** a configuração PIX permanece inalterada

### Requirement: Compra de cartão imutável e restrita ao proprietário

Antes de emitir cobrança, o sistema SHALL validar autorização, prazo, elegibilidade e revisão no servidor e congelar conta, cliente, recebedor/versionamento, composição, valores em centavos e condições comerciais. Uma compra MUST NOT combinar fotógrafos. Fotos com cobrança externa ainda pagável SHALL ficar protegidas contra outra cobrança, sem perda do restante do carrinho.

#### Scenario: Carrinho de outra conta
- **WHEN** a preparação contém pedido, configuração ou item pertencente a outro fotógrafo
- **THEN** a operação é recusada antes de gravação parcial ou chamada externa

#### Scenario: Carrinho mudou em outra aba
- **WHEN** a revisão enviada não corresponde à seleção ou cotação vigente
- **THEN** a cliente precisa conferir a revisão atualizada antes de emitir a cobrança

#### Scenario: Cobrança emitida e configuração alterada
- **WHEN** o fotógrafo substitui a InfiniteTag após criar o link
- **THEN** a compra antiga permanece vinculada ao snapshot anterior e novas compras usam a versão vigente

### Requirement: Emissão idempotente e recuperação conservadora

Repetição ou concorrência SHALL reutilizar a mesma tentativa para a mesma compra. Timeout após possível aceitação externa SHALL produzir estado de verificação, sem criar outro link cegamente. O sistema SHALL permitir retomar compras pendentes. Cancelar localmente ou mudar para PIX MUST NOT liberar fotos enquanto o link antigo ainda puder receber pagamento.

#### Scenario: Clique repetido
- **WHEN** a cliente repete a solicitação de cartão para a mesma revisão
- **THEN** recebe a tentativa existente e não uma segunda cobrança

#### Scenario: Resposta perdida
- **WHEN** a chamada pode ter sido aceita e a resposta não chega
- **THEN** a compra fica aguardando verificação com orientação recuperável, sem confirmação ou retry cego

#### Scenario: Link utilizável não retornado
- **WHEN** a API não devolve um URL de checkout utilizável
- **THEN** o sistema informa que não abriu o checkout, conserva a compra reservada e não inicia outra emissão enquanto o resultado remoto permanecer incerto
- **AND** a cliente não é informada que houve pagamento

#### Scenario: Retomada após comprovação de que o link não foi criado
- **WHEN** a InfinitePay confirma que o checkout não foi criado e a tentativa assume `failed_before_issue`
- **THEN** o sistema restaura no carrinho os mesmos itens comerciais elegíveis e permite à cliente iniciar uma nova tentativa de cartão
- **AND** não mantém a interface presa à tentativa encerrada nem duplica pedido ou seleção
- **AND** essa retomada MUST NOT ser oferecida para `verification_required`, timeout, resposta inválida ou outro resultado incerto

#### Scenario: Troca de meio após emissão
- **WHEN** a cliente tenta pagar por PIX fotos de uma cobrança de cartão ainda pagável
- **THEN** o sistema explica o impedimento e oferece retomada ou conciliação da compra existente

### Requirement: Diagnóstico mínimo de respostas de emissão

O sistema SHALL persistir na tentativa uma categoria técnica normalizada para falhas de transporte e respostas HTTP/JSON/URL da criação de checkout, sem persistir corpo bruto, cabeçalhos, credenciais ou dados pessoais. Essas categorias são observabilidade, MUST NOT ser tratadas como prova de que a InfinitePay não criou uma cobrança e MUST NOT liberar reserva ou permitir nova cobrança por si só.

#### Scenario: Resposta HTTP rejeitada
- **WHEN** a API de criação responde com status HTTP não-2xx
- **THEN** a tentativa conserva estado incerto e registra o código HTTP de forma limitada
- **AND** não armazena o corpo da resposta

#### Scenario: Resposta sem URL utilizável
- **WHEN** a API responde sem campo `url`, com JSON inválido ou com URL fora dos destinos permitidos
- **THEN** a tentativa conserva estado incerto e registra somente a categoria correspondente
- **AND** mantém os itens reservados até reconciliação autoritativa

### Requirement: Confirmação autoritativa da transação

O backend SHALL consultar o provedor em conexão autenticada por TLS e conferir sucesso, pagamento, conta, compra, transação, método e valor-base esperado. Semântica de taxas SHALL seguir contrato verificado, sem tratar taxas como receita de fotos. Query string, comprovante, HTTP 2xx isolado ou webhook recebido MUST NOT confirmar pagamento por si só.

#### Scenario: Crédito aprovado e compatível
- **WHEN** a verificação autoritativa comprova pagamento por crédito da conta, compra e valor corretos
- **THEN** todos os pedidos da compra passam a confirmados na mesma transação
- **AND** a transação externa fica vinculada uma única vez à compra

#### Scenario: Conta, identificador ou valor incompatível
- **WHEN** a evidência não corresponde à compra congelada ou já pertence a outra compra
- **THEN** o sistema recusa a confirmação e conserva uma exceção auditável sem liberar fotos

#### Scenario: Cliente retorna pela página de sucesso
- **WHEN** o browser fornece identificadores de transação no retorno
- **THEN** o sistema inicia verificação no servidor e mostra estado pendente até obter evidência válida

### Requirement: Eventos duráveis e repetidos sem efeitos duplicados

Notificações autenticadas e solicitações de verificação SHALL ser persistidas de forma durável, limitadas e deduplicadas antes do processamento. Workers SHALL revalidar conta e compra antes dos efeitos. Replays, ordem divergente ou falha de transporte MUST NOT repetir receita, confirmação ou aviso. URLs externas fornecidas em eventos MUST NOT originar requisições arbitrárias.

#### Scenario: Webhook repetido
- **WHEN** o mesmo evento válido é recebido duas vezes
- **THEN** há um único efeito financeiro e no máximo um evento lógico de confirmação

#### Scenario: Conta suspensa durante processamento
- **WHEN** a conta perde autorização antes do efeito
- **THEN** o pagamento não é aplicado naquela execução e a evidência durável é preservada para tratamento autorizado

### Requirement: Histórico financeiro e entrega coerentes

Histórico, estatísticas e notificações SHALL identificar o meio efetivo sem somar agregado e pedidos como receitas distintas. Correção financeira autorizada SHALL preservar transação/snapshots, suspender entrega e avisos pendentes conforme o contrato atual. Replay de aprovação anterior MUST NOT desfazer uma correção. Reembolso financeiro MUST NOT ser executado por esta integração.

#### Scenario: Confirmação consolidada
- **WHEN** uma compra de cartão contém pedidos de duas galerias do mesmo fotógrafo
- **THEN** a receita considera uma vez o total comercial e os pedidos mantêm origem e entrega próprias
- **AND** cada canal habilitado recebe no máximo um aviso lógico de confirmação da compra

#### Scenario: Correção após aprovação
- **WHEN** o fotógrafo autorizado corrige uma confirmação com motivo e referência à transação
- **THEN** a entrega é suspensa, a evidência é preservada e eventos antigos não reconfirmam automaticamente a compra

### Requirement: Dados mínimos e isolamento de ambiente

A integração SHALL transmitir apenas identificação opaca e descrição comercial neutra necessária à cobrança. Fotos, biometria, nomes de crianças, links de acesso e contatos opcionais MUST NOT compor o payload por padrão. Segredos técnicos SHALL permanecer fora de tabelas comuns, frontend e logs; contas/URLs de teste SHALL ficar separadas da operação real.

#### Scenario: Cobrança de fotografias escolares
- **WHEN** o servidor monta os itens de uma compra
- **THEN** a descrição identifica apenas quantidade/serviço e valores, sem imagens, pessoas ou nomes de arquivos identificáveis

#### Scenario: Credencial exigida posteriormente pelo provedor
- **WHEN** o contrato oficial passa a exigir segredo
- **THEN** a integração fica pendente até haver armazenamento seguro e configuração operacional autorizados

### Requirement: Liberação com evidência verificável

O sistema SHALL ativar recebimento real somente após testes sintéticos de isolamento/concorrência, validação do contrato externo, revisão humana e liberação autorizada. A aceitação SHALL identificar versão, schema, conta e ambiente. Uma preparação documental ou suite sintética MUST NOT ser descrita como cartão implementado ou pagamento real validado.

#### Scenario: Preparação local concluída
- **WHEN** specs, modelos ou mocks estão aprovados e o contrato externo continua incompleto
- **THEN** o relatório identifica as evidências locais e os gates pendentes sem habilitar cobranças reais

### Requirement: Compatibilidade com limpeza restrita de homologação

O inventário fechado da limpeza exclusiva de homologação SHALL classificar `infinitepay_settings` como configuração preservada do fotógrafo. Compras de cartão, tentativas, recibos e correções SHALL ser classificadas junto às tabelas operacionais de compra e SHALL ser removidas em ordem de dependência, antes do cliente, somente pela limpeza homologada explicitamente autorizada. A limpeza de homologação MUST NOT tocar nenhum recurso operacional ou banco de produção.

#### Scenario: Limpeza sintética da conta de homologação
- **WHEN** o operador autorizado executa a limpeza restrita com configuração e registros de compra de cartão sintéticos
- **THEN** a configuração InfinitePay permanece e registros de cartão/PIX ligados aos dados operacionais removidos desaparecem sem órfãos
- **AND** as tabelas desconhecidas continuam bloqueando a limpeza
