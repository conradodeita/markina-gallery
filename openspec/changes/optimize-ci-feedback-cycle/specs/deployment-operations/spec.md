# Spec Delta

## ADDED Requirements

### Requirement: Fast feedback local por paths alterados
O projeto SHALL oferecer uma única entrada local que identifica paths alterados relativos a uma base e ao worktree, executa lint e contratos rápidos explicitamente conhecidos e informa os gates completos ainda obrigatórios no CI. A seleção local SHALL NOT inferir omissões de testes de produto a partir de um mapa de impacto incompleto.

#### Scenario: Alteração backend sem mapa de impacto
- **WHEN** um path de runtime backend é alterado
- **THEN** a entrada local pode executar o lint rápido e SHALL informar que a suíte backend completa continua obrigatória no CI

#### Scenario: Ferramenta read-only isolada
- **WHEN** somente a ferramenta de feedback da CI e seu teste são alterados
- **THEN** a entrada local executa os contratos e lint dessa ferramenta sem iniciar a suíte backend de produto

#### Scenario: Path desconhecido
- **WHEN** um path não possui regra de seleção
- **THEN** a entrada local mantém os gates completos como obrigatórios e não declara validação integral

### Requirement: CI não publica ou opera em homologação removida
O projeto SHALL manter somente desenvolvimento local, GitHub Actions e produção como alvos operacionais. Workflows SHALL NOT publicar, inventariar ou executar manutenção remota em homologação. Um nome histórico em um caminho de configuração já usado pela produção não constitui outro ambiente e não será renomeado por esta mudança. A publicação em produção SHALL continuar vinculada aos gates existentes e à aprovação humana.

#### Scenario: Execução de CI
- **WHEN** um workflow é executado por pull request, push ou operação manual
- **THEN** nenhum job usa um environment `homolog`, secrets SSH de homologação ou executa deploy, inventário ou manutenção remota desse ambiente
- **AND** os IDs dos checks obrigatórios existentes SHALL permanecer estáveis

#### Scenario: Release de produção
- **WHEN** uma release é elegível para produção
- **THEN** os gates e a aprovação humana existentes permanecem obrigatórios, sem publicar automaticamente a partir de `develop`

### Requirement: Seleção conservadora de validações em pull requests
A CI SHALL selecionar validações de PR por caminhos explicitamente allowlisted e SHALL executar cobertura completa para caminhos críticos ou desconhecidos. Pushes protegidos e operações manuais SHALL manter a validação completa.

#### Scenario: Alteração isolada de ferramenta de CI
- **WHEN** um PR altera somente uma ferramenta explicitamente isolada e allowlisted
- **THEN** a CI executa seus contratos e qualidade aplicáveis, mantém o check obrigatório `backend` e pode omitir somente a suíte de produto sem relação com a ferramenta

#### Scenario: Caminho crítico, misto ou desconhecido
- **WHEN** o diff contém autenticação, autorização, isolamento, pagamento, biometria, privacidade, migration, storage, exclusão de dados, segurança, infraestrutura, contrato compartilhado ou caminho sem regra explícita
- **THEN** a CI exige todas as validações aplicáveis ao risco, sem omitir a suíte correspondente

#### Scenario: Push protegido ou operação manual
- **WHEN** o evento é push protegido ou `workflow_dispatch`
- **THEN** a CI executa todos os escopos e testes obrigatórios

### Requirement: Distribuição backend por duração sem omitir módulos
A CI SHALL distribuir módulos inteiros por duração histórica, com fallback determinístico para módulos novos, e SHALL exigir que a união dos shards seja exatamente a coleção completa, sem sobreposição.

#### Scenario: Balanceamento por duração disponível
- **WHEN** existem pesos válidos para módulos coletados
- **THEN** o planner distribui módulos pela carga estimada, preserva a ordem de cada módulo e produz o mesmo plano para a mesma coleção e pesos

#### Scenario: Peso ausente ou alterado
- **WHEN** um módulo não possui duração histórica ou a coleção mudou
- **THEN** o planner usa o fallback de peso documentado e o agregador ainda exige cobertura integral da coleção atual

### Requirement: Cancelamento de CI limitado a pull requests
A CI SHALL agrupar execuções pelo número do PR e cancelar somente uma execução anterior daquele PR. Runs de push e dispatch SHALL ter grupos únicos e não ser cancelados por novas execuções.

#### Scenario: Novo commit no mesmo pull request
- **WHEN** uma nova execução de CI é iniciada para o mesmo PR
- **THEN** a execução obsoleta desse PR pode ser cancelada e a nova execução assume a validação corrente

#### Scenario: Release ou dispatch protegido
- **WHEN** uma execução começa por push protegido ou `workflow_dispatch`
- **THEN** ela mantém um grupo independente e não é cancelada por outro push, release ou dispatch

## MODIFIED Requirements

### Requirement: Release API/web promove o artifact ARM64 do mesmo run CI
A CI SHALL exportar somente a imagem base do container API ativo por um comando read-only restrito que confira o ID retornado pelo inventário; a exportação SHALL NOT incluir volumes, ambiente ou arquivos montados do container. Em runner ARM64, a CI SHALL construir `api` sobre esse ID-base e copiar exclusivamente `backend/app`, preservando runtime facial e dependências instaladas; SHALL construir `web` pelo Dockerfile aprovado. Produção do artifact pode correr em paralelo com a matriz de testes, mas sua promoção SHALL depender dos gates completos, do SHA exato elegível em `main` e da aprovação humana `production`. A publicação SHALL baixar somente os artifacts Actions do mesmo run, verificar hashes, manifesto, SHA, ID-base, IDs de imagem e arquitetura, e transferir o bundle candidato por chave SSH com forced command limitado a upload. O release SHALL falhar fechado se imagem-base/artifact, digest, arquitetura, SHA ou chave restrita estiver ausente ou divergente.

#### Scenario: Artifact de produção aprovado
- **WHEN** o classificador marca escopo app, a imagem API base exportada corresponde ao ID inventariado, os gates completos do push para `main` terminam com sucesso e a aprovação `production` é concedida
- **THEN** o release baixa os artifacts imutáveis desse mesmo run/SHA, confere seus digests e o ID-base, e transfere o bundle candidato restrito antes de consumir as imagens com o fingerprint aprovado

#### Scenario: Artifact de PR ou run/SHA/base divergente
- **WHEN** o evento é PR, artifacts não pertencem ao run atual, seu SHA/hash/manifesto ou ID-base não corresponde ao inventário, ou não há key de upload restrita
- **THEN** nenhum bundle é transferido nem serviço é recriado

### Requirement: Promoção de imagens não recompila no host
Após revalidar o fingerprint e preservar as imagens anteriores, o release SHALL confirmar que o ID-base API do bundle é o ID inventariado, carregar as imagens API/web e provar IDs, plataforma `linux/arm64` e revisão de origem antes da recriação. O release comum SHALL NOT executar `compose build`; SHALL continuar sem migrations, limitado a `api` e `web`, com smoke tests e rollback aprovado existentes.

#### Scenario: Imagens correspondem ao artifact
- **WHEN** o bundle do SHA alvo passa suas verificações e ambas as imagens são `linux/arm64`
- **THEN** somente `api` e `web` são recriadas com os IDs carregados e sem migrations

#### Scenario: Bundle inválido
- **WHEN** imagem, ID, arquitetura, label, hash, fingerprint ou alvo diverge
- **THEN** o release falha antes de carregar o payload inválido ou recriar containers, preservando as imagens de rollback

### Requirement: Ambientes definidos por variáveis separadas
O projeto SHALL documentar desenvolvimento local, CI efêmera e produção como seus alvos operacionais. Segredos de produção SHALL permanecer em configuração externa segura; CI SHALL usar somente dados e credenciais sintéticos. Nenhum ambiente operacional ou procedimento remoto de homologação SHALL ser requerido. Caminhos históricos já consumidos por um release protegido de produção ficam sob o contrato existente e fora desta change.

#### Scenario: Documentação de variáveis
- **WHEN** as variáveis de desenvolvimento, CI ou produção são documentadas
- **THEN** `.env.example` descreve somente os nomes necessários sem valores reais e não aponta para arquivos de homologação

#### Scenario: Configuração de desenvolvimento e CI
- **WHEN** um desenvolvedor ou workflow prepara validações
- **THEN** as variáveis documentadas não incluem secrets de produção nem configuram um destino de homologação

### Requirement: Documentação de desenvolvimento, deploy e rollback
O projeto SHALL documentar desenvolvimento, CI, deploy protegido direto em produção, decisões técnicas e checklist de rollback, sem procedimentos para homologação.

#### Scenario: Consulta de procedimentos
- **WHEN** o operador prepara uma validação ou release
- **THEN** README, DEPLOY.md, documentação OpenSpec e checklist de rollback orientam o procedimento direto em produção e a preservação dos dados existentes

## REMOVED Requirements

### Requirement: Gate de homologação da autenticação
Removido pela decisão explícita do proprietário de encerrar o ambiente operacional de homologação. Validações automatizadas permanecem em CI com dados sintéticos; produção conserva seus gates próprios.

### Requirement: Limpezas controladas e delimitadas dos dados de teste de homologação
Removido porque o workflow e o ambiente de homologação foram encerrados. Nenhum novo procedimento de limpeza remota será executado.

### Requirement: Inventário manual e somente leitura da homologação
Removido porque o alvo operacional deixou de existir no fluxo do projeto. O workflow dedicado e sua conexão SSH não serão mantidos.
