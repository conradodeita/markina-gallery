## ADDED Requirements

### Requirement: Configuração independente e segura por fotógrafo
O sistema SHALL associar cada integração Orders à conta autenticada do fotógrafo e verificar a conta recebedora pelo provedor. Credenciais SHALL permanecer em envelopes cifrados dedicados e nunca aparecer em logs, respostas públicas ou snapshots comerciais. Configuração SHALL exigir senha/OTP/sessão/origem/versão e não aceitar tenant do navegador como autorização.

#### Scenario: Configuração de outra conta
- **WHEN** fotógrafo ou cliente tenta ler/alterar a configuração de outro tenant
- **THEN** o servidor recusa sem divulgar credenciais ou situação financeira alheia

#### Scenario: Troca ou revogação de credenciais
- **WHEN** uma configuração muda ou deixa de ser autorizada pelo provedor
- **THEN** novas cobranças usam somente uma versão própria validada e tentativas anteriores mantêm vínculo com a versão recebedora original

#### Scenario: Fotógrafo configura a própria integração pela UI
- **WHEN** o fotógrafo acessa Meios de pagamento
- **THEN** encontra card responsivo com flags independentes, estado da própria conta, dicas associadas a cada campo, referências oficiais e URL completa de webhook copiável, sem exibir segredos salvos ou dados de outro fotógrafo

### Requirement: Orders com valor e material imutáveis
O sistema SHALL criar ordens exclusivamente por POST /v1/orders com type online, modo automatic, valores calculados no servidor, referência única e X-Idempotency-Key durável. Tokens de cartão SHALL ser coletados por componente oficial, usados uma vez e nunca persistidos. Pedidos PIX e históricos legados SHALL manter suas próprias referências.

#### Scenario: Alteração do carrinho
- **WHEN** o cliente altera fotos após preparar ou enviar uma tentativa
- **THEN** fotos/total daquela tentativa permanecem imutáveis e nova cobrança exige nova revisão e reconciliação/cancelamento da tentativa potencialmente ativa

#### Scenario: Duplo clique e resposta perdida
- **WHEN** há chamadas concorrentes, repetição ou timeout na criação
- **THEN** somente uma emissão é admitida e resultado incerto exige consulta autoritativa, sem reenvio cego ou liberação para cobrança duplicada

#### Scenario: Nova tentativa após recusa
- **WHEN** a API confirma falha terminal sem pagamento e o cliente tenta novamente
- **THEN** a seleção é preservada/restaurada e nova tentativa usa UUID, token e snapshot novos

### Requirement: Estado financeiro confirmado no servidor
O sistema SHALL preservar estados de order e transação separadamente. Aprovação SHALL exigir confirmação Orders consistente com conta, referência, total e método. Estados desconhecidos SHALL permanecer em verificação. Reembolso integral, parcial e contestação SHALL ser representados conforme confirmação do provedor, sem atribuir fotos arbitrariamente a um reembolso parcial.

#### Scenario: Frontend apresenta sucesso
- **WHEN** o navegador informa que o componente terminou
- **THEN** nenhum pedido é confirmado sem evidência autoritativa do servidor

#### Scenario: Notificação atrasada
- **WHEN** chega atualização pendente anterior a uma aprovação
- **THEN** a compra não é rebaixada nem perde sua confirmação

#### Scenario: Estorno ou reembolso
- **WHEN** a consulta confirma refunded, partially_refunded ou charged_back
- **THEN** a situação financeira e a liberação de entrega refletem o evento, preservando snapshots e histórico

#### Scenario: Aprovação tardia após retorno ao carrinho
- **WHEN** tentativa anterior é aprovada após mudança de seleção
- **THEN** somente as fotos e o total congelados nessa tentativa são confirmados e sobreposição financeira gera revisão explícita

### Requirement: Inbox autenticada e idempotente
O sistema SHALL validar HMAC oficial do tópico order, conta e ID antes de persistir inbox mínima durável e responder sucesso. Processamento SHALL consultar Orders, respeitar locks, deduplicar entregas e suportar backoff/reinício sem perder atualizações posteriores da mesma order.

#### Scenario: Assinatura inválida ou tenant incorreto
- **WHEN** uma notificação falha na validação de assinatura/conta/ID
- **THEN** nenhum evento financeiro ou pedido é alterado

#### Scenario: Duplicação, ordem e falha temporária
- **WHEN** notificações duplicadas/fora de ordem ou falhas transitórias ocorrem
- **THEN** a inbox mantém rastreabilidade e converge ao estado autoritativo sem confirmar ou cobrar em duplicidade

#### Scenario: Ausência de callback depois de estado final
- **WHEN** uma compra enviada já foi confirmada, recusada ou cancelada e não recebe callback posterior
- **THEN** a reconciliação periódica continua consultando a tentativa, permitindo detectar estorno ou aprovação tardia sem emitir nova cobrança

#### Scenario: Notificação após rotação da mesma conta
- **WHEN** a nova versão validada de credenciais do mesmo recebedor e tenant recebe uma atualização de compra anterior
- **THEN** a consulta autenticada pode atualizar a compra original sem alterar sua versão recebedora, mantendo recusa para conta ou tenant diferentes

### Requirement: Checkout integrado e projeções coerentes
O sistema SHALL oferecer tela própria responsiva com resumo, total, escolha de método habilitado, estados compreensíveis, tokenização oficial, prevenção de reenvio e retorno seguro. Compras, Vendas e pagamentos, filtros e CSV SHALL distinguir pedido, provedor, método e situação financeira sem permitir confirmação manual de Mercado Pago.

#### Scenario: Dois provedores habilitados
- **WHEN** PIX manual e Mercado Pago estão disponíveis
- **THEN** ambos podem ser escolhidos e seus estados/identificadores/recebedores não se misturam

#### Scenario: Identificação visual do meio de pagamento
- **WHEN** o cliente escolhe entre PIX do sistema e Mercado Pago ou escolhe o método dentro do checkout
- **THEN** encontra miniaturas dos respectivos símbolos ao lado de nomes e explicações, sem depender apenas da imagem, preservando proporções, contraste, responsividade e caminhos de pagamento existentes

#### Scenario: Retomar compra ou checkout abandonado
- **WHEN** cliente retorna depois de sair
- **THEN** pode retomar a tentativa própria e encontra estado consistente, sem interpretar abandono como pagamento pendente confirmado nem alterar seleção de outra compra

#### Scenario: Confirmação recuperada pela consulta automática
- **WHEN** a resposta do envio se perde e a consulta automática recupera um estado diferente
- **THEN** a tela e a contagem do carrinho são atualizadas a partir do servidor, sem exigir novo envio ou recarregar a página

#### Scenario: Pagamento externo em desenvolvimento
- **WHEN** testes tentam processar com uma conta real sem autorização operacional
- **THEN** o servidor impede a emissão e mantém a seleção

### Requirement: Histórico e lifecycle financeiro preservados
O sistema SHALL incluir tentativas Orders no inventário comercial protegido da cliente e classificar as novas tabelas no inventário operacional. Reset integral SHALL recusar perda de qualquer tentativa enviada ou inbox financeira existente. O CSV padrão SHALL conservar quatro colunas; detalhes de provedor/estados SHALL exigir opção explícita.

#### Scenario: Exclusão ou reset com referências Orders
- **WHEN** há tentativa vinculada à cliente ou evidência financeira remota em um reset
- **THEN** a operação apresenta o bloqueio antes da exclusão, mantendo IDs, snapshots e rastreabilidade

#### Scenario: Reset proprietário com conta Mercado Pago
- **WHEN** a homologação executa o reset proprietário com configurações Orders e somente tentativas locais não enviadas
- **THEN** preserva integralmente conta/credenciais/preferências do proprietário e classifica as tentativas locais como operacionais

#### Scenario: Reset proprietário com evidência enviada em qualquer tenant
- **WHEN** existe tentativa Orders enviada ou inbox financeira de qualquer fotógrafo
- **THEN** inventário e execução do reset proprietário recusam a operação antes de excluir registros ou mídia

#### Scenario: Consumidor do CSV anterior
- **WHEN** exporta sem solicitar detalhes financeiros
- **THEN** recebe o contrato anterior de quatro colunas sob os filtros aplicados

### Requirement: Ensaio operacional restrito ao proprietário
Fora de desenvolvimento/teste, o sistema SHALL restringir contas de teste aos pares tenant/cliente permitidos pelo servidor. Configuração inválida SHALL negar emissão. Carrinho e envio SHALL aplicar a restrição sem aceitar autorização do navegador. Tentativas enviadas SHALL continuar conciliáveis e canceláveis; o meio restrito SHALL NOT ser contado como meio geral para publicar galerias pagas.

#### Scenario: Credenciais de teste em instalação operacional
- **WHEN** o fotógrafo habilita uma conta de teste e somente seu cliente está permitido
- **THEN** somente esse par autenticado pode preparar/enviar Orders e os demais clientes mantêm os meios anteriores

#### Scenario: Permissão retirada após preparação
- **WHEN** o par deixa de estar permitido antes do envio
- **THEN** nenhum POST financeiro é emitido e o carrinho permanece preservado

#### Scenario: Permissão retirada após envio
- **WHEN** existe tentativa enviada antes da retirada do par
- **THEN** a consulta, inbox e cancelamento continuam disponíveis sem permitir nova cobrança

#### Scenario: Política ausente ou inválida
- **WHEN** a instalação operacional não possui configuração válida para o cliente autenticado
- **THEN** Mercado Pago de teste fica indisponível e acesso direto ao endpoint não contorna a restrição

#### Scenario: Aprovação simulada no ambiente operacional
- **WHEN** a conta de teste confirma uma compra do proprietário
- **THEN** Compras e Vendas e pagamentos identificam o teste, os indicadores de receita/vendas reais e o CSV financeiro padrão não incorporam essa simulação, e o CSV detalhado preserva evidência explicitamente identificada como teste

### Requirement: Worker financeiro com cofre seguro
O worker financeiro SHALL receber o cofre seguro do servidor para processar inbox e reconciliação independentemente do navegador, mantendo a vinculação cifrada por tenant e versão da conta.

#### Scenario: Navegador do cliente fechado
- **WHEN** uma notificação válida chega ou uma consulta agendada vence sem cliente conectado
- **THEN** o worker pode consultar Orders com a credencial da respectiva conta, sem expor o cofre ao frontend, migrate ou serviços não consumidores

