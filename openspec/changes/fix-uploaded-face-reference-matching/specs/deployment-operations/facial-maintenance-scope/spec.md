# Spec Delta

## ADDED Requirements

### Requirement: Manutenção facial admite somente Compose revisado por hash

O gate de manutenção SHALL admitir mudança exclusivamente em `docker/docker-compose.yml` entre baseline e alvo quando seu blob Git coincidir com o manifesto autorizado. Qualquer outro caminho Docker, ausência de autorização, manifesto inválido ou hash divergente SHALL impedir inventário elegível e release. O inventário SHALL conferir isso em repositório temporário, sem alterar refs ou objetos do checkout ativo.

#### Scenario: Duas variáveis faciais no Compose revisado
- **WHEN** somente o Compose principal mudou em Docker e o manifesto autorizado fixa seu blob exato
- **THEN** a manutenção pode continuar pelos gates existentes, sem aprovação implícita de release

#### Scenario: Docker fora do escopo ou blob divergente
- **WHEN** outro arquivo Docker mudou ou o Compose alvo diverge do hash autorizado
- **THEN** a operação é recusada antes de recriar serviços

#### Scenario: Revalidação durante o build com Compose novo
- **WHEN** o checkout alvo muda somente o Compose revisado enquanto os containers anteriores continuam ativos
- **THEN** a conferência após build resolve em memória o YAML anterior com o mesmo diretório-base e ambiente atual, recusando drift real sem confundi-lo com a alteração intencional do alvo
- **AND** depois da recriação a conferência usa o Compose alvo e não persiste configuração resolvida ou segredos

### Requirement: Manifesto cobre apresentação e mantém autorização separada

O manifesto SHALL fixar os blobs de configuração/comparação facial, apresentação compartilhada, página da galeria e Compose desta correção. A aprovação de preparação SHALL NOT autorizar mutação remota. O runtime SHALL continuar restrito aos três serviços existentes, domínio/porta, schema e gates de ativação; mudança do script de inventário SHALL atualizar seu pin no wrapper versionado antes de qualquer instalação remota autorizada.

#### Scenario: Preparação aceita com publicação pendente
- **WHEN** o proprietário aprova preparar o gate restrito e o CI valida seus contratos
- **THEN** `maintenance_release.authorized` permanece falso e o wrapper instalado no servidor permanece intacto

#### Scenario: Runtime não revisado
- **WHEN** um arquivo coberto diverge do blob do manifesto ou um novo caminho operacional não admitido aparece no diff
- **THEN** a manutenção permanece inelegível
