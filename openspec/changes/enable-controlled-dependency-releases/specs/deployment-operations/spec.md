# Spec Delta

## ADDED Requirements

### Requirement: Dependências possuem impacto por artefato
O planejamento SHALL identificar serviços e imagens afetados pelos manifests, includes Python, contextos de build e Dockerfiles versionados. Alterações protegidas SHALL exigir homologação. Dependências SHALL possuir classe própria sem iniciar deploy no merge.

#### Scenario: Dependências frontend e Python acumuladas
- **WHEN** o SHA contém alterações em ambos os conjuntos de manifests
- **THEN** o relatório identifica web e cada imagem Python consumidora sem conceder autorização operacional

#### Scenario: Worker ou imagem especializada
- **WHEN** o delta altera Dockerfile, modelos, worker especializado ou sua configuração
- **THEN** os consumidores são identificados e a publicação permanece bloqueada por homologação específica

### Requirement: Web isolado admite dependências Python pendentes
O web-only SHALL admitir manifests Python pendentes no mesmo SHA somente com contexto resolvido exclusivo de frontend, Dockerfile e regras de exclusão aprovados, árvore versionada sem links externos e ausência de alteração protegida de API/Compose. A identidade da API e o snapshot não-web SHALL permanecer independentes do SHA web.

#### Scenario: Atualização web em SHA misto
- **WHEN** só os manifests Python diferem no backend e o build web usa exclusivamente frontend
- **THEN** a validação admite web-only, exibe a proveniência do contexto e mantém o runtime Python pendente

#### Scenario: Contexto adicional ou alteração de API
- **WHEN** há contexto externo, build args não aprovados, symlink, Dockerfile divergente ou alteração de código backend
- **THEN** o procedimento falha explicitamente antes de build ou escrita

### Requirement: Plano operacional exige inventário e cobertura
O plano SHALL exigir inventário atual com SHA, serviços ativos, IDs/digests, arquitetura e saúde; SHALL excluir opcionais inativos e bloquear consumidores ativos sem executor e rollback aprovados. Imagens anteriores exatas, saúde, aprovação e ausência de migration SHALL ser condições de execução.

#### Scenario: Inventário ausente ou worker não coberto
- **WHEN** não há evidência atual ou um consumidor ativo não é atendido pelo procedimento
- **THEN** o plano informa o bloqueio e não fornece autorização de release

### Requirement: Inventário manual de produção permanece restrito
O coletor SHALL usar exclusivamente acesso SSH já autorizado, limitar consultas ao projeto e metadados de pacotes aprovados e não conter comandos de publicação. Falha de autenticação, permissão ou metadado ausente SHALL ser exibida sem contorno ou escrita preparatória na Oracle.

#### Scenario: Consulta manual autorizada
- **WHEN** o operador solicita inventário pelo SSH já autorizado
- **THEN** o coletor consulta identidades/arquiteturas/versões sem ler segredos, dados de clientes ou alterar serviços
