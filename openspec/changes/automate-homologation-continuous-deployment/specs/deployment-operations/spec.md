## ADDED Requirements

### Requirement: Entrega contínua rastreável em homologação

O sistema SHALL publicar em homologação somente um commit de `develop` cujo workflow de CI tenha concluído com sucesso. A publicação SHALL depender de aprovação do ambiente protegido de homologação e SHALL registrar o SHA exato implantado, sem incluir alterações locais não commitadas.

#### Scenario: Commit integrado aprovado

- **WHEN** um commit é integrado em `develop` e todos os jobs obrigatórios de CI terminam com sucesso
- **THEN** o workflow solicita a aprovação configurada para homologação e publica exatamente aquele SHA após a aprovação

#### Scenario: CI reprovada

- **WHEN** qualquer job obrigatório de CI falha
- **THEN** o workflow não executa nenhuma ação de conexão ou alteração no servidor de homologação

### Requirement: Deploy isolado e reversível da Markina Gallery

O workflow SHALL usar somente secrets protegidos para acesso ao servidor e SHALL interromper a publicação se o checkout remoto não estiver limpo ou se o inventário não confirmar o projeto `markina-gallery`. O deploy SHALL executar apenas migrations aditivas, recriar somente serviços da Markina Gallery necessários à revisão, verificar healthchecks e permitir retorno ao SHA saudável anterior sem alterar ClearBudget, proxy, firewall, DNS, certificados, redes ou volumes de terceiros.

#### Scenario: Publicação saudável

- **WHEN** a aprovação de homologação é concedida e o checkout remoto está limpo
- **THEN** o sistema atualiza o checkout para o SHA aprovado, aplica as migrations, valida os healthchecks externos e registra a revisão saudável anterior e a nova

#### Scenario: Falha durante publicação

- **WHEN** uma migration, serviço ou smoke test falha
- **THEN** o workflow interrompe a publicação, preserva evidências sem revelar secrets e executa somente o rollback da Markina Gallery para a revisão saudável anterior quando isso for seguro

### Requirement: Segredos de entrega fora do repositório

As credenciais de SSH, identificação do host e chaves necessárias para leitura do repositório SHALL permanecer somente em GitHub Environments/Secrets e no servidor, nunca em workflow versionado, logs, arquivos `.env` ou documentação com valores reais.

#### Scenario: Execução do workflow

- **WHEN** o workflow de entrega é iniciado
- **THEN** ele obtém os dados de acesso por secrets mascarados e não imprime seus valores nem cria arquivos persistentes contendo credenciais
