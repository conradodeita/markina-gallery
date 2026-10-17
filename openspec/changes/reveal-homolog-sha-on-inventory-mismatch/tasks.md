# Tasks

## 1. Especificar o diagnóstico

- [x] 1.1 Revisar proposta, design e delta spec; autorização do proprietário para reconciliar registrada em 17/10/2026.

## 2. Implementar com guarda fail-closed

- [x] 2.1 Informar somente SHA esperado e observado em divergência, mantendo falha antes de qualquer consulta remota.
- [x] 2.2 Adicionar regressão que verifica os hashes impressos, erro não zero e nenhuma chamada Docker em caso de divergência.
- [x] 2.3 Executar teste de política, `bash -n` e `openspec validate --strict`; registrar evidência verificável em `validation.md`.

## 3. Integrar e usar o diagnóstico

- [ ] 3.1 Abrir PR para `main` e integrar somente após CI verde e revisão humana; não publicar aplicação.
- [ ] 3.2 Executar o inventário com o SHA previamente confirmado, registrar qualquer divergência sem consultar serviços e reconciliar o plano operacional antes do deploy da change de produto.
