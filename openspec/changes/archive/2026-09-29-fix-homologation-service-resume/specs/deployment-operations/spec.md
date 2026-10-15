## MODIFIED Requirements

### Requirement: Docker Compose com serviços isolados e healthchecks
O projeto SHALL entregar um Docker Compose com serviços `nginx`, `web` (Next.js), `api` (FastAPI), `db` (PostgreSQL), `redis` e `worker`, cada um com healthcheck. Serviços de aplicação SHALL poder ser retomados individualmente sem iniciar implicitamente serviços one-shot de migration. Migration SHALL permanecer uma operação explícita, executada separadamente e somente após verificação da revisão de destino.

#### Scenario: Ambiente local
- **WHEN** o operador executa o Compose do ambiente local
- **THEN** todos os serviços sobem e os healthchecks respondem com sucesso

#### Scenario: Retomada sem migration
- **WHEN** o operador retoma contêineres existentes da aplicação após uma parada controlada
- **THEN** somente os serviços da aplicação solicitados são iniciados, o serviço one-shot `migrate` não é iniciado e o schema ativo permanece inalterado

#### Scenario: Migration explicitamente solicitada
- **WHEN** o operador executa uma liberação autorizada que exige migration
- **THEN** o fluxo verifica a revisão corrente, executa Alembic de forma explícita com a imagem correspondente ao SHA alvo e só então inicia binários compatíveis

#### Scenario: Healthcheck da retomada falha
- **WHEN** qualquer serviço retomado não fica saudável ou os endpoints de saúde local/público falham
- **THEN** o procedimento registra a falha, mantém a migration fora do fluxo de retomada e solicita diagnóstico sem alterar banco, mídia ou serviços vizinhos
