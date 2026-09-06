## Purpose

Definir avisos transacionais seguros e idempotentes relacionados ao resultado de uma busca facial, sem transportar referência, biometria ou identidade inferida pelo canal de mensagens.

## ADDED Requirements

### Requirement: Conclusão notificada sem biometria

Quando uma consulta válida termina pronta, sem candidatos ou em falha terminal recuperável pela cliente, o sistema SHALL mostrar o resultado na interface e enfileirar uma notificação transacional pelo canal configurado. O payload SHALL conter somente identificadores opacos de deduplicação, texto neutro e link sujeito à autenticação normal, sem imagem, embedding, similaridade, quantidade de correspondências, nome inferido ou link que conceda novo acesso.

#### Scenario: Cliente saiu da tela

- **WHEN** a consulta termina depois que a cliente fechou ou abandonou a tela
- **THEN** a outbox mantém e entrega uma única notificação neutra de conclusão sem depender da sessão de UI ativa

#### Scenario: WhatsApp disponível

- **WHEN** uma busca válida termina sem candidatos e a política transacional permite o canal
- **THEN** a outbox recebe uma única mensagem sanitizada para a cliente, sem bloquear a conclusão da busca

#### Scenario: Resultados prontos

- **WHEN** uma busca válida termina com candidatas autorizadas
- **THEN** a outbox recebe uma única mensagem de busca concluída sem informar identidade, quantidade ou score

#### Scenario: Canal indisponível

- **WHEN** o canal não está configurado ou falha
- **THEN** a interface continua mostrando o resultado correto e a falha de mensagem pode ser retomada sem repetir busca ou tratamento biométrico

### Requirement: Deduplicação e cancelamento

A notificação SHALL usar chave idempotente por consulta e tipo de resultado. Revogar, cancelar ou excluir a consulta antes do envio SHALL cancelar mensagens pendentes; reprocessamento técnico SHALL NOT duplicar o contato.

#### Scenario: Callback ou job repetido

- **WHEN** a mesma conclusão é processada mais de uma vez
- **THEN** no máximo uma notificação é enviada para aquela consulta

### Requirement: Acesso de cliente visível ao fotógrafo

Cada login OTP concluído em contexto de galeria SHALL criar uma notificação administrativa idempotente para o fotógrafo, contendo somente cliente, Galeria pública e horário. Essa notificação SHALL NOT incluir OTP, referência facial, embedding ou inferência e SHALL NOT bloquear o redirecionamento da cliente.

#### Scenario: Cliente entra pela Galeria pública

- **WHEN** a cliente conclui o OTP de um link válido e é redirecionada para a Galeria pública
- **THEN** o fotógrafo recebe uma única notificação de acesso na interface administrativa, sem necessidade de aprovar o login
