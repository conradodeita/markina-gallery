# External dependency monitoring Specification

## ADDED Requirements

### Requirement: Limite de PRs ordinários

O projeto SHALL monitorar npm, Python, imagens Docker e GitHub Actions semanalmente, com no máximo seis PRs ordinários abertos simultaneamente: um por entrada de ecossistema/diretório. As verificações SHALL ocorrer em dias distribuídos. PRs SHALL permanecer sob revisão humana, sem automerge.

#### Scenario: Agenda semanal escalonada

- **WHEN** Dependabot verifica versões ordinárias
- **THEN** npm, pip, imagens Docker e GitHub Actions são verificados em dias distintos, sem concentrar todos os jobs na mesma janela

### Requirement: Grupos limitados a famílias compatíveis

Grupos ordinários SHALL reunir somente famílias de dependências explicitamente relacionadas e atualizações patch/minor compatíveis. Atualizações major e dependências críticas ou especializadas SHALL permanecer individuais ou em seu próprio grupo especializado; compartilhar ecossistema não é critério suficiente para agrupar.

#### Scenario: Família incompatível ou major

- **WHEN** uma atualização major ou de banco, autenticação, runtime ou motor especializado não pertence a uma família compatível declarada
- **THEN** a atualização não é agrupada com dependências apenas por compartilhar ecossistema e mantém validação isolada ou agrupamento especializado

### Requirement: Atualizações de segurança separadas

O limite de PRs ordinários MUST NOT bloquear Dependabot security updates, cuja cadência e abertura são geridas separadamente pelo GitHub.

#### Scenario: Atualização de segurança prioritária

- **WHEN** Dependabot identifica uma correção de segurança
- **THEN** sua criação não é limitada pelo teto dos PRs ordinários nem agrupada pelas regras ordinárias

### Requirement: Seleção condicional de CI com agregador obrigatório

O CI SHALL selecionar backend, frontend, runtime Gemma e builds locais de imagens de produto/fotografia pelas áreas dos arquivos alterados. Checks OpenSpec, Gitleaks e políticas de release SHALL continuar executando em todos os PRs. O check obrigatório agregador MUST falhar quando o classificador falhar, quando uma validação necessária não executar ou quando qualquer validação necessária falhar; o check MUST preservar os nomes e a cobertura dos status obrigatórios existentes.

#### Scenario: Alteração isolada de frontend

- **WHEN** somente arquivos do frontend são alterados em um pull request
- **THEN** testes, lint, build e imagem local do frontend executam; backend e motores não afetados podem ser omitidos; OpenSpec, Gitleaks e políticas continuam obrigatórios e o agregador confirma o escopo

#### Scenario: Alteração de manifesto Python compartilhado por imagens

- **WHEN** `requirements.txt` ou `requirements-push.txt` do backend muda
- **THEN** backend, Gemma e builds locais das imagens API, prévia e RAW executam e o agregador exige sucesso de cada validação selecionada

#### Scenario: Falha ou ausência de validação necessária

- **WHEN** o classificador falha, um escopo necessário é marcado como skipped/ausente ou seu job termina em falha
- **THEN** o status obrigatório agregador falha e impede aprovação pela `main`

#### Scenario: Alteração em execução manual ou push protegido

- **WHEN** o workflow executa manualmente ou em push para `develop`/`main`
- **THEN** todos os escopos de validação executam antes dos jobs protegidos já existentes
