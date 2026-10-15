# Spec Delta

## Purpose

Permitir que o aviso WhatsApp de fotos disponíveis leve a cliente à compra autenticada no subdomínio do fotógrafo correto, mantendo o link externo do álbum de arquivos somente no botão “Fotos disponíveis” daquela compra.

## ADDED Requirements

### Requirement: Link interno do pedido no aviso WhatsApp

O aviso WhatsApp de fotos disponíveis SHALL oferecer a variável `{{link_compras}}`, renderizada como URL HTTPS canônica do subdomínio do fotógrafo e ancorada na compra da cliente correspondente. A variável SHALL ser específica ao evento de entrega; `{{pedido}}` SHALL continuar identificando o pedido e o URL externo do álbum SHALL NOT ser incluído.

#### Scenario: Template de entrega usa o destino interno
- **WHEN** o fotógrafo inclui `{{link_compras}}` no texto de fotos disponíveis e o aviso elegível é processado
- **THEN** a mensagem enviada contém o link HTTPS daquele fotógrafo para `/library/purchases#order-{UUID}` e mantém `{{pedido}}` como referência curta do pedido

#### Scenario: Template legado não inclui a nova variável
- **WHEN** o evento mantém texto configurado sem `{{link_compras}}`
- **THEN** o envio segue o texto configurado e os controles existentes, sem inserir o link externo do álbum

#### Scenario: Fotógrafo único sem hostname cadastrado
- **WHEN** há exatamente um tenant ativo sem hostname persistido e a aplicação possui origem pública HTTPS configurada
- **THEN** o sistema usa essa origem exata como hostname canônico para gerar o link e resolver o acesso à compra

#### Scenario: Vários fotógrafos exigem hostnames explícitos
- **WHEN** há mais de um tenant ativo e algum tenant ainda não possui hostname canônico cadastrado
- **THEN** o sistema não infere a origem do Host recebido, não gera link de compra para esse tenant e rejeita autenticação dele em host não registrado

#### Scenario: Host associado a tenant inativo
- **WHEN** o host da origem pública está registrado em tenant inativo enquanto outro tenant está ativo sem hostname
- **THEN** o sistema não reaproveita esse host para resolver o tenant ativo

#### Scenario: Destino canônico ausente ou inválido
- **WHEN** não há origem pública confiável nem hostname HTTPS canônico associado ao pedido
- **THEN** o sistema não inventa origem a partir de `Host`, não envia link de outro fotógrafo e registra falha operacional sanitizada da notificação

### Requirement: Aviso respeita a propriedade do pedido

O sistema SHALL criar e processar o aviso somente para a cliente proprietária do pedido dentro do tenant resolvido para o subdomínio, mantendo os gates de pagamento confirmado, link vigente, revisão, consentimento do canal e deduplicação existentes.

#### Scenario: Pedido de outro fotógrafo
- **WHEN** um aviso, retry ou reenvio aponta para pedido cuja propriedade não corresponde ao tenant do evento
- **THEN** o sistema cancela o processamento sem enviar mensagem, expor o pedido ou revelar dados de outro fotógrafo

#### Scenario: Revisão do pedido continua válida
- **WHEN** o worker processa mensagem de um pedido do tenant correto com pagamento confirmado, álbum vigente e revisão atual
- **THEN** entrega o aviso ao contato autorizado da cliente usando o mesmo subdomínio vinculado ao evento
