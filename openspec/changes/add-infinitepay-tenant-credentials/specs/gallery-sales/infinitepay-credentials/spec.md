# Spec Delta

## Purpose

Permitir ao fotógrafo gerenciar sua credencial InfinitePay no painel existente, protegendo o segredo e conservando o vínculo financeiro entre cada compra e a conta autorizada.

## ADDED Requirements

### Requirement: Cadastro no card existente
O card InfinitePay de Configurações SHALL permitir cadastrar InfiniteTag e API Key, substituir a chave e desconectar com confirmação sensível. O segredo MUST ser uma entrada oculta e transitória, sem preenchimento posterior, persistência no navegador, analytics ou retorno em respostas.

#### Scenario: Cadastro confirmado
- **WHEN** o fotógrafo confirma senha e código locais para sua proposta
- **THEN** a configuração é salva somente na sua conta e a UI mostra InfiniteTag e status sem a chave

#### Scenario: Edição abandonada
- **WHEN** o fotógrafo tenta abandonar uma edição ainda não concluída
- **THEN** a UI alerta sobre alterações não salvas e permite continuar a edição

### Requirement: Compatibilidade com a capacidade da API
O formulário SHALL aceitar entrada/envio de API Key somente quando a API autenticada declarar explicitamente capacidade de armazenamento seguro disponível; capacidade ausente em versão anterior SHALL impedir coleta de segredo.

#### Scenario: API anterior durante atualização
- **WHEN** a API não fornece capacidade explícita de cofre disponível
- **THEN** a UI impede entrada/envio e substituição de API Key, sem afetar operações legadas sem segredo

### Requirement: Autoridade exclusiva da sessão
O backend SHALL revalidar sessão, vínculo ativo e permissão existente em toda operação. Tenant, e-mail, referência de credencial ou desafio fornecidos pelo cliente MUST NOT substituir essa autoridade. Falha de autorização SHALL recusar sem expor ou consumir recursos estrangeiros.

#### Scenario: Tentativas entre contas
- **WHEN** A fornece identificadores ou desafio de B em leitura, alteração ou desconexão
- **THEN** nenhum segredo ou configuração de B é lido, alterado ou excluído

#### Scenario: Sessão inadequada
- **WHEN** a chamada está sem sessão, usa sessão de cliente, vínculo revogado ou origem inválida
- **THEN** a operação é recusada antes da alteração

### Requirement: Credencial cifrada e vinculada ao escopo
O armazenamento dedicado SHALL conter somente ciphertext autenticado, nonce, identificador da chave e metadados mínimos por tenant/ambiente/versão. A chave mestra MUST permanecer externa. Envelope transplantado, adulterado ou sem chave autorizada SHALL falhar sem fallback e sem segredo em resposta, erro ou auditoria.

#### Scenario: Adulteração e chave ausente
- **WHEN** ciphertext, tenant, versão ou ambiente divergem, ou a chave mestra não está disponível
- **THEN** o backend recusa descriptografia, cadastro ou uso financeiro e informa somente indisponibilidade

### Requirement: Estado não presume validação remota
O painel SHALL distinguir chave cadastrada de validação remota, rejeição comprovada e indisponibilidade de validação. Armazenar ou decifrar uma chave MUST NOT marcá-la validada. Configurar credencial MUST NOT criar compra, reserva, cobrança ou consulta externa inventada.

#### Scenario: Provedor sem validação não financeira documentada
- **WHEN** o cadastro local termina e não existe método documentado de validar a chave sem cobrança
- **THEN** a UI mostra credencial cadastrada e validação remota indisponível
- **AND** nenhuma requisição financeira é emitida

### Requirement: Compra conserva versão financeira
Cada compra nova SHALL congelar a referência de credencial e InfiniteTag da própria conta na mesma transação da reserva. Substituição SHALL preservar a versão necessária a compras existentes. Consulta/retorno MUST usar o snapshot próprio, com integridade composta de tenant, sem credencial de outra conta.

#### Scenario: Substituição concorrente
- **WHEN** cadastro de uma nova chave concorre com criação de checkout
- **THEN** a compra usa integralmente a configuração anterior ou a nova, nunca uma combinação de ambas
- **AND** pagamentos antigos continuam verificáveis com sua versão anterior

### Requirement: Desconexão e legado conservadores
Desconexão SHALL exigir confirmação e ausência de compra financeira não resolvida. Quando permitida, SHALL apagar material secreto gerido e impedir retorno ao binding legado. Compras anteriores à UI SHALL conservar o binding legado exclusivo do tenant. PIX e estados incertos do PR #260 MUST permanecer preservados.

#### Scenario: Compra em andamento
- **WHEN** há compra em criação, aguardando pagamento, verificação, exceção ou hold
- **THEN** desconexão é recusada com orientação de conciliação, mas desabilitar novos cartões continua permitido conforme as regras existentes

#### Scenario: Desconexão sem pendência
- **WHEN** a confirmação ocorre sem transações não resolvidas
- **THEN** o segredo gerido é apagado, novos cartões ficam indisponíveis e o PIX mantém sua configuração
- **AND** nenhuma chave global ou binding antigo é usado como fallback

### Requirement: Rotação e recuperação controladas
O sistema SHALL permitir leitura de versões criptográficas autorizadas e recifragem explícita para a chave ativa, sem exibir plaintext. Backup/restauração SHALL preservar o banco cifrado e as chaves mestras separadamente. Remover uma chave necessária MUST ser impedimento operacional documentado.

#### Scenario: Rotação sem mudança financeira
- **WHEN** envelopes são recifrados com a chave mestra ativa
- **THEN** identidade, tenant, InfiniteTag e referência das compras permanecem idênticos e os valores secretos não são emitidos
