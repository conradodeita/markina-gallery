## Purpose

Definir um transporte WhatsApp real, isolado e observável para as comunicações autorizadas da Markina Gallery, preservando segurança, idempotência e independência do provedor concreto.

## ADDED Requirements

### Requirement: Transporte único para comunicações WhatsApp autorizadas

O sistema SHALL encaminhar OTP e mensagens WhatsApp originadas por eventos já especificados por uma porta única de provedor, sem acoplar regras de autenticação, pagamento, galeria ou entrega ao fornecedor concreto.

#### Scenario: OTP usa o canal ativo
- **WHEN** uma pessoa solicita um OTP de cliente válido em um ambiente configurado com transporte real
- **THEN** o sistema enfileira uma única entrega transacional para o telefone informado, com expiração compatível com o desafio e sem expor o código em logs

#### Scenario: Evento do cliente avisa o fotógrafo
- **WHEN** um evento já especificado do cliente exige aviso ao fotógrafo
- **THEN** o sistema entrega a mensagem ao telefone verificado do fotógrafo usando o mesmo canal e preserva a referência auditável ao evento de origem

#### Scenario: Ação do fotógrafo avisa o cliente
- **WHEN** uma ação administrativa já especificada exige mensagem ao cliente
- **THEN** o sistema entrega o template autorizado ao telefone verificado desse cliente sem permitir troca arbitrária de destinatário

#### Scenario: Comunicação não especificada
- **WHEN** não existe evento e template autorizados nas specs do produto
- **THEN** o transporte não cria chat livre, campanha ou mensagem nova apenas porque o provedor suporta essa operação

### Requirement: Identidade remetente pareada e verificável

O sistema SHALL tratar como remetente o número realmente conectado à instância do provedor e SHALL enviar externamente somente quando ele coincidir com o número esperado configurado pelo fotógrafo para o ambiente. A comparação SHALL aceitar como equivalentes somente a forma E.164 brasileira atual e o JID legado do mesmo número que omite exatamente o nono dígito `9` depois do país e DDD, mantendo todos os demais dígitos idênticos; qualquer outra diferença SHALL permanecer bloqueada.

#### Scenario: Fotógrafo configura o número esperado
- **WHEN** o fotógrafo autenticado salva um número internacional válido na configuração WhatsApp
- **THEN** o sistema registra a identidade esperada como pendente e não a considera conectada até confirmá-la por uma sessão pareada do provedor

#### Scenario: Número conectado coincide
- **WHEN** o provedor informa conexão aberta e identidade remetente igual ao número esperado
- **THEN** o painel apresenta o canal como pronto e permite que o worker entregue mensagens autorizadas

#### Scenario: JID brasileiro legado omite o nono dígito
- **WHEN** o número esperado brasileiro contém o nono dígito `9` e o provedor informa o mesmo país, DDD e demais dígitos em um JID legado sem esse único dígito
- **THEN** o sistema considera as duas representações da mesma identidade, preserva as máscaras e permite marcar o canal como pronto

#### Scenario: Diferença não explicada pelo JID brasileiro legado
- **WHEN** país, DDD, posição do dígito ou qualquer outro dígito diverge entre a identidade esperada e a conectada
- **THEN** o sistema não aplica equivalência aproximada e mantém os envios bloqueados

#### Scenario: Número conectado diverge
- **WHEN** a identidade conectada não coincide com o número esperado
- **THEN** o sistema bloqueia novos envios, apresenta diagnóstico sanitizado ao fotógrafo e registra o incidente sem revelar credenciais ou sessão

#### Scenario: Consulta administrativa do canal
- **WHEN** o fotógrafo abre a configuração WhatsApp
- **THEN** o sistema mostra provedor, ambiente, número esperado e conectado mascarados, estado, última verificação e pendências, sem retornar chaves ou material de sessão

### Requirement: Pareamento administrativo protegido

O sistema SHALL permitir que somente o fotógrafo autenticado prepare e acompanhe o pareamento da instância dedicada, mantendo segredos do provedor no servidor e tratando QR ou código de pareamento como material efêmero sensível.

#### Scenario: Início de pareamento
- **WHEN** o fotógrafo solicita conexão para o número esperado e a instância dedicada está fechada
- **THEN** o sistema solicita ao provedor um desafio de pareamento, o apresenta apenas na sessão administrativa autorizada e registra a operação

#### Scenario: Confirmação no telefone
- **WHEN** a pessoa responsável conclui o pareamento no aparelho e o provedor informa conexão aberta
- **THEN** o sistema revalida a identidade conectada antes de marcar o canal como pronto

#### Scenario: Material de pareamento expirado
- **WHEN** um QR ou código de pareamento expira ou a sessão administrativa termina
- **THEN** o sistema deixa de apresentá-lo e exige nova solicitação sem persistir o material em logs ou respostas públicas

### Requirement: Resultado de envio baseado no contrato real do provedor

O sistema SHALL interpretar o corpo da resposta do provedor e SHALL preservar identificador externo e estado aceito quando disponíveis; um HTTP 2xx isolado não prova entrega nem autoriza marcar a comunicação como entregue.

#### Scenario: Provedor aceita e identifica a mensagem
- **WHEN** o provedor responde com estrutura válida, destinatário compatível e identificador externo
- **THEN** o sistema registra a tentativa como aceita e aguarda atualização posterior quando o provedor oferecer estados de entrega

#### Scenario: Resposta bem-sucedida incompleta
- **WHEN** o provedor responde HTTP 2xx sem os campos mínimos esperados ou com destinatário divergente
- **THEN** o sistema registra resultado desconhecido ou falha permanente sanitizada e não o converte em entrega confirmada

#### Scenario: Atualização de entrega
- **WHEN** uma atualização autenticada referencia uma mensagem externa conhecida
- **THEN** o sistema avança monotonicamente seu estado observável sem reexecutar o evento de negócio

### Requirement: Outbox, idempotência e timeout ambíguo

O sistema SHALL persistir uma entrega por evento, destinatário e template autorizados, aplicar tentativas limitadas e impedir reenvio cego quando não for possível saber se o provedor aceitou uma chamada que sofreu timeout.

#### Scenario: Evento repetido
- **WHEN** o mesmo evento é processado novamente
- **THEN** o sistema reutiliza a entrega idempotente existente e não cria uma segunda mensagem

#### Scenario: Falha transitória inequívoca
- **WHEN** o provedor informa falha transitória antes de aceitar a mensagem
- **THEN** o sistema agenda nova tentativa com limite e atraso controlados

#### Scenario: Timeout após envio
- **WHEN** ocorre timeout ou queda de conexão depois que a requisição pode ter sido recebida pelo provedor
- **THEN** o sistema marca a tentativa como ambígua e reconcilia por identificador ou janela operacional antes de permitir reenvio manual ou automático

#### Scenario: OTP expira na fila
- **WHEN** uma entrega de OTP ainda não foi aceita ao expirar o desafio
- **THEN** o sistema encerra a entrega sem enviar o código expirado

### Requirement: Webhooks autenticados e deduplicados

O sistema SHALL aceitar somente eventos necessários de conexão e ciclo de entrega por endpoint autenticado, com deduplicação, limite de tamanho e rejeição neutra de origem inválida.

#### Scenario: Evento válido repetido
- **WHEN** o provedor repete um webhook autenticado já processado
- **THEN** o sistema reconhece a duplicata sem repetir transição, auditoria de negócio ou mensagem

#### Scenario: Evento não autenticado
- **WHEN** um webhook não apresenta a credencial esperada ou excede os limites aceitos
- **THEN** o sistema o rejeita sem modificar conexão ou entrega e registra apenas diagnóstico sanitizado

#### Scenario: Mensagem recebida sem fluxo especificado
- **WHEN** o provedor encaminha conteúdo recebido que não pertence a uma capacidade bidirecional especificada
- **THEN** o sistema não o transforma em chat, comando ou evento de negócio

### Requirement: Isolamento e recuperação do canal

O transporte real SHALL manter instância, dados e sessão próprios do ambiente, sem expor diretamente a API do provedor à internet, e SHALL recuperar a conexão persistida após reinício sem pareamento rotineiro.

#### Scenario: Reinício saudável
- **WHEN** os serviços reiniciam com volumes e credenciais válidos
- **THEN** o sistema recupera a instância, revalida conexão e identidade e retoma somente entregas seguras

#### Scenario: Sessão perdida ou desconectada
- **WHEN** o provedor não recupera a sessão ou informa conexão fechada
- **THEN** o sistema bloqueia novos envios, preserva a outbox e apresenta pendência de reconexão ao fotógrafo

#### Scenario: Homologação pronta para teste real
- **WHEN** a instância exclusiva de homologação está conectada ao número próprio autorizado e os healthchecks estão saudáveis
- **THEN** o sistema permite validar OTP e mensagens já implementadas com dados sintéticos sem reutilizar sessão, chave ou telefone de produção
