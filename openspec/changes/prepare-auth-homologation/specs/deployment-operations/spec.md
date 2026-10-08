## ADDED Requirements

### Requirement: Gate de homologação da autenticação

O sistema SHALL ter um procedimento de homologação para a autenticação que exija inventário somente-leitura, isolamento da Markina Gallery, configuração externa de segredos, aplicação explícita de migrations e smoke tests antes de receber tráfego de teste.

#### Scenario: Plano de impacto zero aprovado

- **WHEN** o operador concluir o inventário do servidor de homologação
- **THEN** ele apresenta ao proprietário os recursos existentes, a porta e o subdomínio propostos, o escopo limitado à Markina Gallery e aguarda aprovação explícita antes de alterar o ambiente

#### Scenario: Preparação de banco e segredos

- **WHEN** a homologação for aprovada
- **THEN** o operador cria recursos exclusivos da Markina Gallery, mantém segredos fora do Git, aplica a migration Alembic de forma explícita e não expõe PostgreSQL nem Redis publicamente

#### Scenario: Entrada HTTPS compartilhada e isolada

- **WHEN** o Proxy Manager for necessário para expor a homologação
- **THEN** o operador conecta somente o nginx da Markina à rede de entrada autorizada com alias exclusivo, cria somente um host novo e certificado para o subdomínio de homologação, e não altera recursos existentes de outros projetos

#### Scenario: Verificação e rollback da autenticação

- **WHEN** a versão de homologação estiver disponível
- **THEN** o operador executa healthchecks e smoke tests de autenticação, registra o resultado e consegue retornar somente a Markina Gallery à versão anterior saudável
