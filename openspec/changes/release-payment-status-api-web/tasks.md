## 1. Preparação e integração

- [x] 1.1 Conferir inventário somente-leitura e relação entre runtime e main; registrar imagens, configuração e revisão do banco sem segredos. Evidência: inventário SSH e hashes em `validation.md`; revisão SQL read-only 0081 e configurações efetivas iguais ao runtime.
- [x] 1.2 Reconciliar a versão instalada com a melhoria de pagamentos em branch isolada; revisar diff contra produção e validar contratos afetados. Evidência: commit 71be3b2 preservado como ancestral; diff de runtime limitado ao painel financeiro; PR #190 passou CI completo, 88 testes direcionados de backend, 3 regressões do painel e 524 testes frontend.
- [x] 1.3 Documentar runbook com comandos restritos, guardas, verificações e rollback pelas imagens reais. Evidência: `docs/RELEASE-PAYMENT-STATUS-API-WEB.md`, blocos Bash validados por `bash -n`, hashes efetivos dos serviços conferidos sem revelar variáveis.
- [x] 1.4 Publicar PR, obter CI verde e integrar à main conforme autorização de push/merge existente. Evidência: PR #190 mergeado em `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`; backend, frontend, gemma-runtime, OpenSpec, gitleaks e inventário passaram; homolog foi ignorado.

## 2. Publicação

- [x] 2.1 Apresentar inventário final e plano do SHA integrado, com impacto e recuperação, e obter aprovação específica antes da mutação. Evidência: aceite humano do SHA `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47` e fingerprint `314cf6232ca534fb24c5a26744b2a4b9e76017d1f37557fc57a224a5da295965`; o fingerprint foi reconferido imediatamente antes da troca.
- [x] 2.2 Executar release aprovado, conferir serviços/saúde/HTTPS e registrar evidência; validar o comportamento autenticado quando houver sessão autorizada disponível. Evidência: API/web saudáveis, artefatos e `APP_VERSION` no SHA alvo, nginx Markina sem recriação, endpoints HTTPS 200 e endpoint administrativo anônimo 403, banco `20261014_0081` inalterado, demais containers Markina preservados e imagens/registros do release anotados em `validation.md` e no diretório remoto `deploy-state`. Nenhuma sessão autenticada foi fornecida; inspeção visual autenticada não foi executada.
