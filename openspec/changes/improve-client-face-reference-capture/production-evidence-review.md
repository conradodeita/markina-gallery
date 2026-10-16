# Evidências pendentes para liberação

## Estado confirmado pelo proprietário

Em 2026-10-16, o proprietário informou que a aprovação documentada da base legal/consentimento e o conjunto autorizado para medir precisão ainda precisam ser definidos. A autorização para preparar e corrigir o fluxo técnico está vigente; não equivale à existência desses registros. `production-gates.json` SHALL continuar com `release_ready=false`.

## Escopo já aprovado do produto

- Busca na mesma galeria previamente autorizada por sessão/OTP e vínculo; resultados apenas reordenam o acervo autorizado.
- Upload voluntário com consentimento específico versionado, referência temporária e alternativa de seleção manual.
- Câmera com captura guiada obrigatória, sem liveness ou terceiro novo; SFace e índice existentes preservados.
- A decisão `simplify-mobile-gallery-face-search` substituiu a exigência de prova administrativa prévia por checkbox único de autodeclaração de responsável e consentimento para novas referências infantis. Não reintroduzir a exigência supersedida. A aprovação jurídica/operacional de produção continua pendente.

## Pacote revisável e critério de conclusão

| Gate | Registro necessário | Evidência que permite concluir |
| --- | --- | --- |
| Base legal | Controlador, finalidade/necessidade, titulares abrangidos, base legal escolhida pelo responsável jurídico, aviso/RIPD versionados, operadores, direitos e retenção | Referência opaca do registro restrito, responsável pela aprovação, versão, data e escopo de produção; não inserir nomes de titulares ou documentos no Git |
| Consentimento infantil | Revisão do texto e checkbox vigentes, forma de registro/versionamento, revogação, melhor interesse e alternativa manual | Aprovação jurídica/humana do fluxo aprovado; não presumir representação a partir de foto, OTP ou autorização de deploy |
| Calibração/equidade | Origem/finalidade/autorização do corpus, pares anotados correspondentes/não correspondentes e critérios de amostragem/grupos definidos antes do ensaio | Relatório agregado conforme `docs/CALIBRACAO-E-EQUIDADE-FACIAL.md`, com modelo/limiar exatos e revisão humana; sem fotos, embeddings, scores individuais ou atributos inferidos nos artefatos |
| Capacidade ARM | Destino isolado e orçamento aprovados, corpus permitido, concorrência e duração conforme runbook | Relatório de p50/p95, throughput, fila, CPU, RAM e impacto na aplicação/terceiros; snapshot de memória livre não substitui carga |
| Recuperação | Destino isolado, controle de acesso/rede, backup restrito e procedimento de exclusão do ensaio | Restore verificado, integridade/schema e tempo registrados; hash/TOC do backup isoladamente não comprovam restauração |
| Aprovação operacional | SHA final, inventário/fingerprint atual, domínio/bind, serviços, saúde, impacto e rollback | Gates anteriores aprovados e aprovação única do job mutável no environment `production` |

## Preparação técnica já disponível

O inventário corrigido foi executado somente em leitura em 2026-10-16, com alvo `57bbc7c528c4542815b5ecc3b94be78eaf15a4ba`: os três serviços correspondem à configuração resolvida e estão saudáveis; HTTPS `/healthz`, `/api/health` e `/` retornou 200. Nginx Markina publica somente `127.0.0.1:8080`; API 8000/web 3000 são internos. Fingerprint dessa execução: `141aa2f1f90286bc915ec6a5eed6b94b71e8a91f819846840901341bdf5987ec`.

Esse inventário comprova o cálculo corrigido; não autoriza release de outro SHA nem aprova gates humanos. O CI e o wrapper restrito ainda devem provar o preflight automático da correção. Nenhum serviço, banco, `.env` ou recurso de terceiro foi alterado nesse diagnóstico.
