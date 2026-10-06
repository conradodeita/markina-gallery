## ADDED Requirements

### Requirement: Inventário manual e somente leitura da homologação

O projeto SHALL fornecer em `main` um workflow manual dedicado a inventariar a homologação sem compartilhar o caminho de execução destrutivo de manutenção.

#### Scenario: Invocação controlada

- **WHEN** um operador inicia o workflow manual a partir de `main`
- **THEN** o workflow SHALL exigir o SHA completo esperado da versão implantada, usar o ambiente protegido `homolog`, permissões mínimas e validação estrita da chave SSH do host
- **AND** SHALL interromper antes de coletar dados se o HEAD implantado em `/opt/markina-gallery` não corresponder ao SHA informado

#### Scenario: Escopo isolado da Markina Gallery

- **WHEN** o inventário é executado no servidor
- **THEN** SHALL usar somente `/opt/markina-gallery`, `docker/docker-compose.yml`, o arquivo de ambiente homolog e o projeto Compose `markina-gallery`
- **AND** SHALL validar que somente nginx publica porta e que volumes consultados são volumes nomeados exclusivos do projeto, sem referências externas
- **AND** SHALL informar versão implantada, serviços e estado de saúde, portas publicadas, domínio público configurado, revisão Alembic, contagens agregadas de dados e mídia, estado agregado das filas, health endpoints e capacidade do disco
- **AND** SHALL criar e remover exatamente um container transitório de consulta com `--rm --no-deps`, dentro do projeto Compose `markina-gallery`

#### Scenario: Minimização de dados

- **WHEN** o resultado do inventário é apresentado nos logs do Actions
- **THEN** SHALL omitir PII, segredos, caminhos/nome/conteúdo de arquivos e payloads de jobs
- **AND** SHALL apresentar somente contagens agregadas necessárias à avaliação operacional

#### Scenario: Sem efeitos de deploy ou manutenção

- **WHEN** o inventário é executado
- **THEN** SHALL NOT executar deploy, migration, backup, stop, restart, remoção persistente, limpeza ou prune
- **AND** SHALL NOT alterar recursos de outros projetos
- **AND** SHALL limitar consultas de aplicação a um único container transitório de consulta com `--rm --no-deps`, dentro do projeto Compose `markina-gallery`
- **AND** SHALL manter a operação destrutiva de manutenção fora deste workflow
