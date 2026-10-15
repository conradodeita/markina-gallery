# Avaliação isolada de motores de embedding

## ADDED Requirements

### Requirement: Runtime Gemma integra o ciclo operacional sem ativação implícita

O runtime Gemma SHALL ser provisionado separadamente e iniciado explicitamente pelo profile facial-gemma em homologação autorizada. O deploy SHALL preservar a seleção SFace inicial e SHALL incluir Gemma já ativo entre os escritores pausados antes de migrations, serviços reconstruídos e healthchecks. Retomada SHALL alcançar somente containers Gemma existentes; manutenção destrutiva autorizada SHALL pausar o leitor Gemma ativo e restaurá-lo depois. Rollback para checkout sem o serviço SHALL parar Gemma antes da troca e SHALL NOT restaurar banco automaticamente. Nenhuma dessas rotinas SHALL modificar segredos ou iniciar Gemma pela ativação do profile facial convencional.

#### Scenario: Migration encontra worker Gemma ativo

- **WHEN** um deploy autorizado executa migrations com Gemma ativo no projeto markina-gallery
- **THEN** o worker SHALL ser interrompido e a parada confirmada antes de Alembic; falha de parada SHALL bloquear a migration

#### Scenario: Primeiro deploy ainda não possui worker Gemma

- **WHEN** a homologação recebe o código sem container Gemma previamente iniciado
- **THEN** o deploy convencional SHALL preservar SFace e SHALL NOT iniciar o serviço experimental implicitamente; a inicialização explícita SHALL exigir schema e pesos compatíveis

#### Scenario: Limpeza encontra leitor Gemma

- **WHEN** uma execução destrutiva separadamente autorizada encontra Gemma ativo
- **THEN** a rotina SHALL reconhecer somente o serviço do projeto markina-gallery, pausá-lo antes de excluir dados e restaurá-lo depois, preservando serviços e volumes de terceiros

### Requirement: High-res e monitor preservam o motor atual

Gemma SHALL usar a fonte high-res temporária das fotos aderentes, em job independente, sem alterar estado/métricas SFace nem bloquear geração de prévias. A retenção adicional SHALL ser limitada ao TTL existente; leitores com lease ativo SHALL impedir exclusão concorrente. Fotos cuja fonte expirou SHALL permanecer SFace quando a cobertura Gemma estiver incompleta. Monitor SHALL reconhecer atividade/duração/erros do worker Gemma e incluir seus jobs nos totais faciais, sem dados biométricos em métricas.

#### Scenario: Gemma falha após sucesso SFace

- **WHEN** o job Gemma falha enquanto SFace já concluiu a análise
- **THEN** estado e métricas SFace permanecem e a apresentação continua disponível

#### Scenario: Worker Gemma é observado

- **WHEN** o monitor está habilitado e o worker Gemma executa jobs
- **THEN** heartbeat e duração entram no monitor e na exportação sanitizada; CPU/RAM sem fonte continuam indisponíveis

#### Scenario: Inferência experimental concorre com SFace
- **WHEN** Gemma calcula um crop enquanto SFace processa a mesma fonte
- **THEN** o cálculo Gemma SHALL usar o lease do seu job sem manter lock de PhotoAnalysis, permitindo completar SFace e liberar prévias
- **AND** a persistência Gemma SHALL recusar fonte excluída ou com fingerprint, expiração ou pipeline alterados durante o cálculo
- **AND** o lease padrão Gemma SHALL ser limitado a 900 segundos, preservando o orçamento SFace e a proteção de limpeza por lease ativo

### Requirement: Comparação não altera o motor de produto

O benchmark SHALL executar em harness isolado, preservar o motor atual e manter vetores de candidatos em índices/namespace separados. A execução SHALL NOT alterar configuração, banco, API, worker, embeddings persistidos ou acesso de clientes do produto.

#### Scenario: Candidato experimental é executado

- **WHEN** o harness gera embedding com candidato diferente do atual
- **THEN** os vetores SHALL permanecer isolados e SHALL NOT substituir ou ser consultados pelo índice de produção

### Requirement: Seleção global de engine com fallback integral por galeria

A configuração SHALL ser global e editável somente pelo proprietário autenticado. A interface SHALL oferecer um único seletor entre SFace e Gemma, com SFace como padrão. Ao selecionar Gemma, somente galerias criadas depois da primeira ativação Gemma poderão usar esse engine. Uma galeria SHALL usar Gemma apenas quando todos os ativos elegíveis estiverem completamente indexados e atuais no namespace Gemma; em qualquer pendência, falha, ausência ou divergência, a busca inteira SHALL usar SFace. Cada busca SHALL fixar o engine selecionado no momento da criação. Desligar Gemma SHALL pausar novos jobs sem apagar embeddings existentes.

#### Scenario: Proprietário habilita Gemma

- **WHEN** o proprietário ativa o experimento global do Gemma
- **THEN** o sistema SHALL indexar somente galerias novas elegíveis pelas políticas biométricas vigentes e SHALL manter namespace próprio

#### Scenario: Galeria antiga mantém SFace

- **WHEN** o engine global está em Gemma mas a galeria foi criada antes da ativação inicial
- **THEN** todas as buscas da galeria SHALL continuar usando SFace

#### Scenario: Busca Gemma não está pronta para todos os ativos elegíveis

- **WHEN** a cobertura Gemma está ausente, parcial ou desatualizada
- **THEN** o sistema SHALL executar a busca integral com SFace e SHALL NOT expor resultados parciais Gemma como se fossem completos

#### Scenario: SFace é selecionado

- **WHEN** o proprietário desliga o modo shadow
- **THEN** novos jobs Gemma SHALL parar, o índice SFace SHALL permanecer disponível e dados Gemma SHALL seguir a retenção/exclusão explícita, sem purge implícito

#### Scenario: Ativação não reindexa galerias existentes

- **WHEN** o proprietário seleciona Gemma pela primeira vez
- **THEN** o sistema SHALL registrar o instante de ativação e SHALL enfileirar Gemma somente para fotos de galerias criadas a partir desse instante, ainda que uma reconciliação ou tarefa de backfill SFace posterior encontre fotos antigas

#### Scenario: Runtime experimental não está pronto

- **WHEN** o worker Gemma está ausente, com revisão de pesos divergente ou sem heartbeat recente
- **THEN** a interface SHALL impedir ativação, e SFace SHALL continuar disponível

#### Scenario: Falha de indexação experimental

- **WHEN** enfileirar ou executar um job Gemma falha
- **THEN** o job SFace SHALL permanecer independente, SHALL continuar atendendo clientes e SHALL conservar o erro Gemma sanitizado

### Requirement: Dataset real tem autorização e ground truth documentados

O benchmark real SHALL consumir somente lote fornecido para a execução e SHALL documentar origem, finalidade, autorização humana explícita, anotação, acesso autenticado, criptografia, retenção mínima e exclusão. O relatório SHALL conter agregados sem mídia, embedding ou identificador pessoal.

#### Scenario: Lote ou rótulos não foram fornecidos

- **WHEN** não há lote real anotado com origem e autorização registradas
- **THEN** as métricas reais SHALL permanecer pendentes e nenhuma imagem SHALL ser descoberta ou selecionada automaticamente no sistema

### Requirement: Métricas faciais são calibradas e separadas por candidato

Cada candidato e estratégia SHALL ser avaliado nos mesmos dados e partições, com limiares calibrados em validação e teste separado. O relatório SHALL priorizar falsos positivos, incluir rejeição de desconhecidos e não apresentar similaridade como probabilidade de identidade.

#### Scenario: Modelo multimodal tem boa busca semântica

- **WHEN** o EmbeddingGemma 2 obtém resultado na trilha de busca visual ou texto-imagem
- **THEN** esse resultado SHALL NOT ser tratado como evidência de identidade facial sem métricas faciais comparáveis

### Requirement: Conclusão depende de evidência do corpus real

Recomendação de substituição SHALL depender de resultados reproduzíveis do corpus real autorizado, custo operacional, licenças de cada peso e risco residual. Ausência de evidência SHALL resultar em decisão inconclusiva, mantendo o motor vigente.

#### Scenario: Benchmark incompleto

- **WHEN** corpus, ground truth, licença, grupo de dificuldade ou métrica necessária estiver ausente
- **THEN** o relatório SHALL declarar a limitação e SHALL NOT recomendar substituição baseada em alegação não medida

### Requirement: Ativação Gemma fica restrita a homologação autorizada

A seleção Gemma SHALL permanecer limitada à homologação privada até calibração, licença, capacidade, privacidade, autorização humana por execução e plano de retorno estarem aprovados. Ela SHALL NOT, por si só, autorizar produção. A seleção SHALL NOT alterar os gates de consentimento, política facial, autorização, retenção ou acesso já aplicáveis a cada galeria.

#### Scenario: Homologação não está autorizada

- **WHEN** uma solicitação de busca Gemma ocorre fora da homologação autorizada
- **THEN** o sistema SHALL manter SFace como motor servido
