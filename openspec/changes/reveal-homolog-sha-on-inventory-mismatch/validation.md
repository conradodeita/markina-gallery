# Validação

## Verificação local

- `python scripts/test_readonly_homolog_inventory_policy.py`: 7 testes aprovados.
- `C:\Program Files\Git\bin\bash.exe -n scripts/inventory-homolog-readonly.sh`: aprovado.
- `openspec validate reveal-homolog-sha-on-inventory-mismatch --strict`: válido.
- `git diff --check`: aprovado.

## Evidência operacional prévia

- Workflow [39028067492](https://github.com/conradodeita/markina-gallery/actions/runs/39028067492), esperado `71be3b29659143293351968e15fb4886c2d72bf0`: bloqueou antes de qualquer consulta porque o `HEAD` remoto divergiu.
- Workflow [39028890305](https://github.com/conradodeita/markina-gallery/actions/runs/39028890305), esperado `60df317fa29aa4ae0ab3e0dd770e2e313bba8fba`: também bloqueou antes de qualquer consulta por divergência.
- Ambos os workflows encerraram sem comandos Docker, consulta ao banco ou alteração no servidor. A saída anterior não revelava a revisão observada; este é o problema coberto por esta change.

## Integração e inventário após o merge

- PR #208 foi integrado em `main` no commit `57f5a951f9f2991f9ea1cd83af1e65db168789ec` depois do CI `39033921405` passar.
- Workflow `39036156815`, com SHA esperado `71be3b29659143293351968e15fb4886c2d72bf0`, revelou `0779b3e4400f8511980c2d18e79ef8eea586a341` e encerrou antes de consultas.
- Workflow somente leitura `39036197944`, com SHA esperado igual ao observado, concluiu: projeto `markina-gallery`, domínio `markina.pickyourpic.com.br`, entrada `127.0.0.1:8080`, serviços existentes saudáveis, revisão Alembic `20261016_0082`, filesystem do projeto 64% usado e endpoints `/healthz` e `/api/health` em HTTP 200. Foram observados um container antigo de migration parado e dois workers órfãos; nenhum foi removido.
- A análise das linhas confirmou `main` 43 commits à frente de `develop`; publicar o `develop` atual regrediria a versão observada e colidiria com a revisão Alembic `20261016_0082`. A proposta de reconciliação foi aberta antes de qualquer alteração de código: `reconcile-homolog-release-lineage`.
- O deploy da aplicação ainda não foi executado: o workflow `39032173810` passou nos testes, mas `deploy-homolog` foi rejeitado pela proteção porque `develop` não está protegida. Nenhuma alteração remota ocorreu.

## Pendente

- Reconciliar as linhas e a migration no PR operacional antes de reexecutar a publicação da aplicação.
