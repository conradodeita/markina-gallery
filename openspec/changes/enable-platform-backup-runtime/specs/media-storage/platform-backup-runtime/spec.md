# Spec Delta

## ADDED Requirements

### Requirement: Configuração e chave do backup operacional

O chamador de backup SHALL usar uma chave operacional própria e um vínculo protegido a uma única pasta autorizada na conta Workspace escolhida. SHALL existir uma cópia offline da chave autenticada para recuperação sob custódia do proprietário.

#### Scenario: Configuração ou credencial incompatível

- **WHEN** a chave, instalação, origem, destino, escopo ou permissão divergir da configuração revisada
- **THEN** o chamador MUST abortar sem copiar o banco e registrar um código técnico sem expor credenciais

### Requirement: Execução interna agendada e manual

O chamador SHALL produzir o backup diário global e permitir acionamento manual pelo operador usando o mesmo lock e os mesmos controles, sempre dentro do escopo do projeto.

#### Scenario: Repetição da cópia diária

- **WHEN** a execução for repetida ou acionada manualmente para o mesmo ponto diário
- **THEN** o chamador SHALL reconciliar ou retomar o mesmo artefato e preservar cópias anteriores

### Requirement: Verificação pós envio e restauração distinta

O chamador SHALL enviar só o arquivo cifrado e verificar tamanho, SHA-256, autenticação do pacote e contexto antes de registrar cópia conferida. O registro de recuperação comprovada SHALL exigir restauração isolada independente.

#### Scenario: O destino confirma envio sem prova de recuperação

- **WHEN** o arquivo for aceito pelo Google sem um restore comprovado
- **THEN** a rotina MUST manter separados os estados de envio, leitura conferida e restauração comprovada

### Requirement: Ativação isolada e reversível

Instalar e ativar o agendamento SHALL exigir inventário, prova sintética e aprovação específica. MUST NOT recriar serviços de aplicação ou modificar backup e agendamento de terceiros.

#### Scenario: Necessidade de interromper rotina

- **WHEN** o operador desativar o agendamento
- **THEN** a rotina SHALL deixar de iniciar execuções novas e preservar os artefatos já gerados e o catálogo
