# Tasks

## 1. Contrato e persistência

- [x] 1.1 Ampliar constraints das três tabelas com migration aditiva `0090`, preservando linhas existentes e bloqueando downgrade inseguro.
- [x] 1.2 Atualizar modelos, endpoints Pydantic e validação de domínio para 10–100%; manter defaults existentes.

## 2. Interface e documentação

- [x] 2.1 Ampliar slider administrativo até 100%, mantendo passos de 5 e exposição separada.
- [x] 2.2 Atualizar documentação funcional e verificar código afetado por referências obsoletas ao limite 75; remover apenas referências relacionadas ao limite, preservando defaults 50/75.

## 3. Validação e fechamento

- [x] 3.1 Atualizar regressões para o limite 100%, limites inválidos, migration e resultado da mistura em 100%. Os arquivos foram revisados; execução separada registrada em 3.2.
- [x] 3.2 Completar os testes focados e obter CI verde. Evidência: CI #40362799810 no SHA `165d84e0ea5e35ca7f55f0f47207d17d4fcf6105`; backend (`pytest` e regressões PostgreSQL), frontend, OpenSpec, Gitleaks, classificação de escopo, builds/smokes de runtime e política de inventário de homologação passaram. Localmente, frontend 9/9, migration 3/3, ESLint, TypeScript e Ruff passaram; nove cenários da API não iniciaram por ausência local de `mercadopago`.
- [x] 3.3 Revisar diff, validar OpenSpec em modo estrito e fazer `git diff --check`.
- [ ] 3.4 Publicar a migration `0090` e o código por um fluxo suportado, com inventário e preflight atualizados. **Bloqueada:** o classificador atual trata migrations como `protected`, o release API/web proíbe migrations e o manifesto ainda espera schema `20261022_0087`; a última versão operacional informada pelo proprietário é `20261025_0089`. Não há preflight aprovado nem fluxo de migration autorizado registrado para esta change.
