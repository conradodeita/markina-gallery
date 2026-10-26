# Tasks

## 1. Contrato e persistência

- [x] 1.1 Ampliar constraints das três tabelas com migration aditiva `0090`, preservando linhas existentes e bloqueando downgrade inseguro.
- [x] 1.2 Atualizar modelos, endpoints Pydantic e validação de domínio para 10–100%; manter defaults existentes.

## 2. Interface e documentação

- [x] 2.1 Ampliar slider administrativo até 100%, mantendo passos de 5 e exposição separada.
- [x] 2.2 Atualizar documentação funcional e verificar código afetado por referências obsoletas ao limite 75; remover apenas referências relacionadas ao limite, preservando defaults 50/75.

## 3. Validação e fechamento

- [x] 3.1 Atualizar regressões para o limite 100%, limites inválidos, migration e resultado da mistura em 100%. Os arquivos foram revisados; execução separada registrada em 3.2.
- [ ] 3.2 Completar os testes focados e obter CI verde. Evidência local: frontend 9/9, backend 24 aprovados, migration 3/3, ESLint, TypeScript e Ruff aprovados; nove cenários de API não iniciaram por ausência local do pacote `mercadopago`, então a validação completa depende do CI.
- [x] 3.3 Revisar diff, validar OpenSpec em modo estrito e fazer `git diff --check`; release operacional segue o preflight aprovado.
