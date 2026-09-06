## ADDED Requirements

### Requirement: Derivação somente pela seleção consciente

O sistema SHALL manter a busca facial independente da derivação comercial. Uma consulta, candidata ou feedback facial SHALL NOT criar privada; a primeira seleção consciente, manual ou originada do bloco filtrado, SHALL criar ou reutilizar a única privada operacional de `Galeria pública + cliente` pelo resolvedor transacional vigente.

#### Scenario: Busca sem seleção

- **WHEN** a cliente conclui uma ou várias buscas e não seleciona foto
- **THEN** nenhuma privada, associação, pedido ou histórico comercial novo é criado

#### Scenario: Seleções de pessoas diferentes

- **WHEN** a cliente seleciona fotos encontradas por referências diferentes na mesma Galeria pública
- **THEN** todas entram na mesma privada e no mesmo estado individual de seleção, sem duplicar foto, galeria ou total

### Requirement: Privacidade entre membros preservada

O filtro facial, suas referências, consentimentos, resultados, feedbacks e estados SHALL pertencer à cliente autenticada e SHALL NOT ser visível a outros membros da mesma privada. O acervo comum e as seleções individuais continuam seguindo os contratos existentes.

#### Scenario: Dois responsáveis procuram a mesma criança

- **WHEN** duas clientes vinculadas pesquisam ou selecionam a mesma foto
- **THEN** cada uma possui resultado, consentimento, seleção, valor e histórico independentes, embora a foto referencie a mesma mídia autorizada

### Requirement: Acesso autenticado informado ao fotógrafo

Ao concluir um OTP em contexto de galeria, o sistema SHALL reutilizar o cadastro único pelo telefone normalizado, vincular o acesso conforme o link e registrar uma notificação administrativa idempotente para o fotógrafo com cliente, Galeria pública e horário. A notificação SHALL NOT conter OTP, SHALL NOT duplicar o cadastro e SHALL NOT exigir aprovação do fotógrafo para concluir o acesso já autorizado.

#### Scenario: Cliente preexistente conclui o login

- **WHEN** uma cliente já cadastrada conclui o OTP de um link válido de galeria
- **THEN** o sistema reutiliza o mesmo cadastro, conclui o vínculo e cria uma única notificação administrativa daquele acesso sem registrar novamente nome ou telefone

#### Scenario: Repetição técnica da confirmação

- **WHEN** o mesmo desafio consumido é reenviado ou uma transação é repetida
- **THEN** a chave idempotente impede notificação duplicada e nenhum OTP aparece em payload, auditoria ou interface administrativa
