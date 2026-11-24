# Tasks

## 1. Diagnóstico somente de leitura

- [x] 1.1 Estender a classificação dos diretórios fixos para produzir o estado agregado existente e as razões allowlisted descritas na spec; emitir os dois campos no `support-inventory` e `restore-support-inventory`, incluí-los na fingerprint e preservar os gates atuais. Evidência: 44 testes focados passaram, incluindo symlink sem dereferência, tipo/owner/grupo/modo, falha sanitizada e fingerprint; Ruff e a política estática do workflow passaram.
- [x] 1.2 Validar a fronteira do workflow e registrar a evidência desta task em `validation.md`: o teste estático confirmou helper pinado, saída sanitizada e resumo protegido; ambos os inventários compartilham o contrato e estados inseguros continuam bloqueando operações. A revisão proporcional ficou registrada: o classificador único substitui duplicação, os gates permanecem e nenhum código adicional foi removido.

## 2. Integração local

- [x] 2.1 Executar testes focados, Ruff, verificações estáticas do workflow, `openspec validate diagnose-support-storage-readiness --strict` e `git diff --check`; revisar o diff contra exposição de dados, regressões e código morto evidente e registrar resultados em `validation.md`. As validações passaram; evidência em `validation.md`.

## 3. Publicação da mudança e diagnóstico remoto

- [ ] 3.1 Após revisão humana dos artefatos, publicar a implementação por PR e obter revisão/merge conforme autorização vigente; exigir CI verde da `main` no SHA exato e registrar os runs em `validation.md`.
- [ ] 3.2 Após a integração, executar somente `support-inventory` read-only pelo fluxo protegido, passar pelos gates de produção exigidos e registrar a razão observada e fingerprint atual; não despachar `prepare-support`, reparar diretório ou reutilizar fingerprint antiga.

## Workflow follow-up

- Revisar e aceitar proposal, spec, design e tasks antes de iniciar implementação.
- Após implementação, CI e revisão final, sincronizar a capability para `openspec/specs/` e arquivar a change conforme o fluxo do projeto.
