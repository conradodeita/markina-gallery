# Spec Delta

## ADDED Requirements

### Requirement: Continuidade da sessão validada na navegação
O frontend SHALL bloquear conteúdo privado até a validação inicial do contexto e repetir esse gate ao mudar de papel. Dentro do contexto já validado, navegação/foco/período SHALL revalidar em segundo plano sem recriar toda a superfície. Expiração ou negação confirmada SHALL retirar conteúdo e seguir recuperação existente. Backend MUST continuar autorizando cada operação; falha de leitura MUST NOT autorizar contexto novo nem repetir ações.

#### Scenario: Navegação com sessão já confirmada
- **WHEN** uma sessão validada navega dentro da administração ou retorna à janela enquanto a revalidação está pendente
- **THEN** não perde componentes/rascunhos por remontagem da proteção nem volta ao gate inicial; a revalidação continua sendo executada

#### Scenario: Novo papel ou expiração
- **WHEN** o papel protegido muda ou uma revalidação confirma 401/403 contextual
- **THEN** a validação anterior não concede acesso ao novo papel, e conteúdo recusado é retirado sem loop de login

### Requirement: Recuperação precisa de avisos temporários
Falha de leitura SHALL ter aviso de leitura sem sugerir compra/envio incerto. Confirmação posterior da sessão SHALL retirar esse aviso. Falha de mutação SHALL preservar orientação para conferir seu resultado, inclusive após recuperar conexão. Cancelamento intencional MUST NOT virar indisponibilidade. Retry SHALL executar somente a leitura da sessão, sem replay de mutação, OTP ou autenticação.

#### Scenario: Leitura falha e recupera no foco
- **WHEN** uma leitura falha por rede/timeout/408/5xx e a revalidação posterior retorna autorização válida
- **THEN** o aviso temporário é retirado, sem repetir a leitura de negócio ou qualquer mutação

#### Scenario: Resultado de ação permanece incerto
- **WHEN** upload/compra/outra mutação falha e a sessão posteriormente é confirmada
- **THEN** a interface informa recuperação da conexão e preserva orientação para conferir a ação anterior, sem afirmar que ela falhou ou foi concluída

#### Scenario: Cancelamento e verificações concorrentes
- **WHEN** uma navegação cancela intencionalmente uma consulta ou há recusa durante outra verificação
- **THEN** cancelamento não gera alerta de conexão e a recusa continua agendando a revalidação deduplicada existente


#### Scenario: Sinal técnico não é ação comercial
- **WHEN** um sinal automático de atividade falha enquanto a sessão é revalidada
- **THEN** a recuperação segue as leituras de conectividade, sem presumir compra/envio incerto nem repetir ações comerciais


#### Scenario: Aviso de ação após reconexão pode ser fechado
- **WHEN** a conexão foi confirmada e o usuário fecha explicitamente a orientação de conferir a ação anterior
- **THEN** somente o aviso é retirado, sem reenviar a ação ou declarar seu resultado confirmado
