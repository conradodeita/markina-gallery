# Tasks

## 1. Especificar o diagnóstico

- [x] 1.1 Revisar proposta, design e delta spec; autorização do proprietário para reconciliar registrada em 17/10/2026.

## 2. Implementar com guarda fail-closed

- [x] 2.1 Informar somente SHA esperado e observado em divergência, mantendo falha antes de qualquer consulta remota.
- [x] 2.2 Adicionar regressão que verifica os hashes impressos, erro não zero e nenhuma chamada Docker em caso de divergência.
- [x] 2.3 Executar teste de política, `bash -n` e `openspec validate --strict`; registrar evidência verificável em `validation.md`.

## 3. Integrar e usar o diagnóstico

- [x] 3.1 Abrir PR #208 para `main` e integrar após CI verde e autorização explícita do proprietário; não publicar aplicação. Evidência: merge `57f5a951` após CI `39033921405` verde.
- [x] 3.2 Executar o inventário com o SHA confirmado, registrar divergência sem consultas quando necessário e reconciliar o plano operacional antes do deploy. Evidência: workflow `39036156815` bloqueou sem consultas (`71be3b2` esperado, `0779b3e` observado); workflow `39036197944`, esperado `0779b3e`, concluiu inventário somente leitura. A reconciliação está especificada em `openspec/changes/reconcile-homolog-release-lineage/`.
