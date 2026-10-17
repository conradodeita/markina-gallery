# Validação

## Verificação local

- `python scripts/test_readonly_homolog_inventory_policy.py`: 7 testes aprovados.
- `C:\Program Files\Git\bin\bash.exe -n scripts/inventory-homolog-readonly.sh`: aprovado.
- `openspec validate reveal-homolog-sha-on-inventory-mismatch --strict`: válido.
- `git diff --check`: aprovado.

## Evidência operacional prévia

- Workflow [39028067492](https://github.com/conradodeita/markina-gallery/actions/runs/39028067492), esperado `71be3b29659143293351968e15fb4886c2d72bf0`: bloqueou antes de qualquer consulta porque o `HEAD` remoto divergiu.
- Workflow [39028890305](https://github.com/conradodeita/markina-gallery/actions/runs/39028890305), esperado `60df317fa29aa4ae0ab3e0dd770e2e313bba8fba`: também bloqueou antes de qualquer consulta por divergência.
- Ambos os workflows encerraram sem comandos Docker, consulta ao banco ou alteração no servidor. A saída atual não revela a revisão observada; este é o problema coberto por esta change.

## Pendente

- CI e revisão do PR para `main`.
- Após integração, repetir o inventário read-only para capturar a revisão observada e reconciliar o estado antes de qualquer deploy da aplicação.
