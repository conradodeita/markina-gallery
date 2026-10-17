# Tasks

## 1. Documentar e reconciliar a base

- [x] 1.1 Registrar SHA observado, revisão Alembic e política atual do ambiente, sem expor segredos ou dados identificáveis. Evidência: inventário `39036197944`; revisão `0779b3e`, Alembic `20261016_0082`, homolog restrita a branches protegidas e reviewer obrigatório.
- [ ] 1.2 Integrar `main` em `develop` por PR, preservando a change de produto e resolvendo conflitos com base nos contratos e no código atual.

## 2. Corrigir o grafo de migrations

- [ ] 2.1 Renumerar a migration de escopo privado como revisão única imediatamente após `20261016_0082`.
- [ ] 2.2 Atualizar regressões para migrar de `20261016_0082` à nova head e verificar constraints/colunas.
- [ ] 2.3 Executar os testes focados e validação OpenSpec estrita; registrar hashes e resultados verificáveis.

## 3. Publicar com escopo controlado

- [x] 3.1 Proteger `develop` com os mesmos checks requeridos em `main`, sem force-push/deleção e com enforcement ativo; isso torna a branch elegível sob a política existente `protected_branches=true`. Reviewer obrigatório do ambiente `homolog` permanece ativo. Nenhuma regra de produção foi modificada.
- [ ] 3.2 Confirmar inventário e plano de impacto zero com o alvo reconciliado antes de aprovar o job de deploy.
- [ ] 3.3 Após o deploy, confirmar SHA, revisão Alembic, health checks e saúde dos serviços do projeto `markina-gallery`.
