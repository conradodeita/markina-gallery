# Spec Delta

## ADDED Requirements

### Requirement: Composição do arquivo frio ocorre antes do claim e é restrita ao tenant selecionado

A composição do piloto SHALL permanecer inativa por padrão e SHALL exigir uma configuração explícita cujo vínculo de storage identifique o tenant autorizado antes de descobrir ou reivindicar operações. No piloto, somente o tenant do proprietário pode ser selecionado; jobs de outros tenants não podem ser reivindicados ou executados por esse adapter.

#### Scenario: Worker sem gate ou vínculo válido

- **WHEN** o gate está ausente/desligado, o vínculo de storage está ausente/inválido ou seu tenant diverge do tenant selecionado
- **THEN** o worker não descobre nem reivindica operações, não altera jobs/leases e não faz chamadas ao transporte externo

#### Scenario: Fila contém operação do piloto e de outro tenant

- **WHEN** o worker está explicitamente configurado para o tenant do proprietário e há jobs elegíveis desse tenant e de outro tenant
- **THEN** reivindica somente um job do tenant selecionado e preserva os jobs do outro tenant sem alteração

#### Scenario: Lease global ativo pertence a outro tenant

- **WHEN** o coordenador global contém um lease vigente ou retomável de tenant fora do escopo selecionado
- **THEN** o worker não retoma esse lease, não o libera nem o reatribui, não chama o transporte externo e preserva o estado para o fluxo autorizado daquele tenant

### Requirement: Credenciais de mídia permanecem separadas das credenciais de backup

A composição operacional SHALL resolver o vínculo de identidade, credencial e raiz de mídia por uma fronteira própria, sem usar a factory ou o contexto de credenciais do backup global como atalho. A autorização externa, o root e os limites do provider SHALL ser comprovados pelo gate operacional aplicável antes do ensaio real.

#### Scenario: Configuração do backup existe sem vínculo de mídia

- **WHEN** há credenciais/configuração válidas para o backup global, mas não existe vínculo próprio de mídia para o tenant selecionado
- **THEN** a composição de mídia permanece fechada antes de descobrir ou reivindicar jobs e não inicia chamada externa

#### Scenario: Falta prova operacional do vínculo Drive

- **WHEN** a aplicação possui uma configuração sintaticamente válida, mas identidade, acesso à raiz ou limites ainda não foram aprovados no gate operacional
- **THEN** a aplicação não habilita o adapter Drive real nem libera o ensaio de arquivo/recuperação

### Requirement: Storage volátil não pode ativar o runtime de arquivo frio

O ponto de entrada sem argumento do worker SHALL permanecer fechado até existir vínculo operacional durável aprovado. Storage e binding sintéticos MUST NOT ser registrados ou selecionados pelo loop. A composição sintética SHALL ocorrer somente por injeção direta de harness local com sessão e raízes descartáveis; em production o dispatcher SHALL recusar antes de banco/claim/limpeza local.

#### Scenario: Adapter real é apresentado com marca sintética

- **WHEN** um storage volátil ou adapter externo é apresentado à configuração, mesmo com tenant/root declarados compatíveis
- **THEN** a configuração e a execução configurada recusam antes de acessar banco ou transporte, inclusive com gate ligado e ambiente production

#### Scenario: Injeção direta de fixture preserva compatibilidade

- **WHEN** um teste consumidor chama explicitamente o dispatcher com seu storage injetado
- **THEN** o dispatcher mantém a injeção direta local; ela não configura nem abre o loop e é recusada em production
