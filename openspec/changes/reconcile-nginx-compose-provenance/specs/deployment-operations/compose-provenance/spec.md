# Spec Delta

## Purpose

Garantir origem persistente e verificável da configuração Compose do ingresso da Markina Gallery, preservando o runtime existente durante correções de proveniência e oferecendo recuperação delimitada ao serviço autorizado.

## ADDED Requirements

### Requirement: Fontes operacionais persistentes
O sistema SHALL conservar fontes verificáveis e duráveis da configuração do Nginx ativo. Fonte ausente ou aposentada MUST bloquear aprovação até reconciliação comprovada, sem ignorar a fonte ou reativar serviços aposentados.

#### Scenario: Fonte histórica ausente
- **WHEN** os metadados do Nginx referenciam uma fonte removida
- **THEN** o inventário identifica o bloqueio e exige reconciliação de proveniência antes de emitir aprovação
- **AND** nenhum serviço RAW/Gemma é restaurado ou ativado

### Requirement: Equivalência comprovada antes da publicação
O candidato SHALL preservar a configuração operacional efetiva do Nginx, inclusive imagem imutável, arquivos carregados, redes, políticas e montagens. Divergência não resolvida ou validação Compose incompleta MUST impedir publicação.

#### Scenario: Comparação encontra diferença
- **WHEN** o hash ou uma propriedade efetiva do candidato difere do runtime sem justificativa revisada
- **THEN** a operação permanece bloqueada e relata somente categorias e hashes seguros

#### Scenario: Modelo incompleto
- **WHEN** um overlay contém serviço aposentado incompleto ou exige desabilitar consistência para ser resolvido
- **THEN** esse modelo não pode ser aprovado para publicação

### Requirement: Atualização isolada e aprovada
A publicação SHALL exigir plano específico, aprovação humana, fingerprint revalidado e execução exclusiva limitada ao Nginx da Markina. Outros containers, portas, proxy externo, dados, schema, segredos e gates financeiros MUST permanecer preservados.

#### Scenario: Inventário diverge ou falta aprovação
- **WHEN** o snapshot mudou ou não existe aprovação específica do plano atual
- **THEN** a operação aborta antes de qualquer escrita ou parada

#### Scenario: Publicação validada
- **WHEN** a atualização autorizada termina
- **THEN** o Nginx usa fontes persistentes, mantém saúde e HTTPS e os demais containers preservam suas identidades e configurações

### Requirement: Recuperação independente de fontes ausentes
A operação SHALL preparar e verificar backup protegido da configuração efetiva e imagem anterior antes da mutação. A recuperação MUST funcionar sem arquivo aposentado e sem restaurar banco, remover histórico ou alterar recursos de outros projetos.

#### Scenario: Falha após atualização do Nginx
- **WHEN** configuração, saúde ou HTTPS falha
- **THEN** o procedimento recupera somente o Nginx anterior com os artefatos verificados e confirma novamente o ingresso
