# External dependency monitoring Specification

## Purpose

Definir inventário contínuo, identificação de candidatos e revisão segura de dependências externas, com evidência de origem, sem confundir metadados de versão com runtime de produção.

## ADDED Requirements

### Requirement: Inventário versionado com proveniência e uso

O projeto SHALL manter um inventário atualizável de componentes externos relevantes, incluindo versão ou constraint declarada, fonte, função, superfície efetivamente usada, criticidade, licença/ativação, risco de compatibilidade e evidência do runtime. Componentes usados diretamente, transitivamente relevantes, opcionais, experimentais e apenas instalados SHALL ser diferenciados. Ausência de verificação de ambiente SHALL ser registrada como não confirmada.

#### Scenario: Serviço especializado presente

- **WHEN** um serviço/modelo especializado tem container ou worker implantado
- **THEN** o inventário SHALL diferenciar container existente, processo saudável, pesos carregados, jobs/vetores processados e engine selecionada, cada qual associado à data/fonte da evidência

#### Scenario: Tag de imagem mutável

- **WHEN** uma imagem Docker usa tag mutável ou não tem digest
- **THEN** a tag SHALL ser apresentada como declaração e não como prova da imagem/digest ou runtime efetivos

### Requirement: Atualizações ordinárias sem merge automático

O projeto SHALL monitorar npm, Python, imagens Docker e GitHub Actions em intervalos semanais agrupados e limitados, mantendo PR de atualização sob revisão humana. Automerge SHALL ser desabilitado. Dependências sem pin e tags/imagens móveis SHALL ficar visíveis para fixação e risco de reprodutibilidade.

#### Scenario: Candidato de versão ordinário

- **WHEN** Dependabot detecta nova versão elegível
- **THEN** ele SHALL abrir no máximo os PRs limitados/configurados e agrupados, sem atualizar produção nem fazer merge

### Requirement: Segurança com cadência própria

O projeto SHALL distinguir Dependabot security alerts/security updates das verificações semanais de versão. Alertas ausentes, serviço de alertas desabilitado ou falta de permissão SHALL ser estados diferentes; indisponibilidade não SHALL ser reportada como ausência de vulnerabilidade.

#### Scenario: Alerta de segurança

- **WHEN** GitHub informa alerta de dependência vulnerável
- **THEN** o relatório SHALL incluir pacote/ecossistema, severidade, intervalo afetado, versão corrigida quando fornecida, origem e validação requerida, sem aplicar a correção automaticamente

### Requirement: Relatório semanal consolidado com estado observável

O projeto SHALL gerar no GitHub Actions um resumo semanal das PRs Dependabot abertas e dos alertas legíveis. O resumo SHALL informar instante da verificação, endpoints/fontes, contagens, versões candidatas, benefício, riscos, prioridade e recomendação. Lista vazia só SHALL significar ausência de itens retornados pela fonte consultada; falha, permissão insuficiente e fonte não confirmada SHALL ser apresentados em estados distintos. Uma execução sem novidade SHALL não criar PR, issue, comentário ou notificação.

#### Scenario: Consulta sem itens

- **WHEN** endpoints de PRs e alertas respondem com sucesso e retornam lista vazia
- **THEN** o workflow SHALL registrar uma verificação bem-sucedida sem atualização observável e sem notificação externa

#### Scenario: Consulta indisponível

- **WHEN** uma fonte necessária falha, retorna resposta inválida ou paginação não pode ser completada
- **THEN** o workflow SHALL falhar ou identificar a fonte como não confirmada e SHALL NOT afirmar que não existem atualizações/alertas

### Requirement: Componentes especializados exigem avaliação humana

O monitor SHALL classificar modelos/pesos de IA, motores faciais e fotográficos, integrações críticas e dependências com mudança incompatível como revisão especializada. Ele SHALL NOT criar PR de atualização de modelo/peso nem ativar/reindexar componentes especializados automaticamente.

#### Scenario: Modelo experimental publicado

- **WHEN** um runtime/modelo experimental existe no código ou foi observado no ambiente
- **THEN** o inventário SHALL registrar revisão e licença upstream, contexto de implantação e se houve inferência/índice, e SHALL recomendar avaliação humana antes de propor atualização

### Requirement: Monitoramento sem efeito operacional

Os workflows de inventário/avaliação SHALL usar GitHub-hosted runners e permissões somente de leitura, não SHALL conectar à Oracle nem invocar workflows de deploy, Docker, migrations, APIs com efeito de escrita ou ferramentas de merge.

#### Scenario: Avaliação agendada

- **WHEN** a agenda semanal executa
- **THEN** SHALL produzir apenas resumo/artefato de evidência no GitHub Actions e terminar sem alterar branches, PRs, ambientes ou dados de produção
