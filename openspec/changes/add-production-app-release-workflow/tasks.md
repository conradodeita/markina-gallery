# Tasks

## 1. Separação das políticas de release

- [x] 1.1 Adaptar a verificação facial ao marcador `facial-last-healthy.sha` para permitir avanço do checkout por releases app sem alterar os arquivos faciais dedicados; preservar pins faciais exatos e verificar com regressão do release facial e evidência do run #38976692654. Evidência local: o teste Bash `scripts/test_deploy_prod_facial_services.sh` aceitou baseline ancestral e recusou SHA inválido; `python scripts/test_prod_facial_release_gates.py` aprovou 6 testes; CI #38976692654 documenta o último release saudável em `f2ac110`.
- [x] 1.2 Criar manifesto e verificador do escopo da publicação API/web para a estatística; verificar que caminhos, blobs, migration, Docker/Compose, Monitor, runtime facial dedicado e workers fora do escopo são recusados. Evidência local: `python scripts/test_prod_app_release_scope.py` (3 testes aprovados), incluindo paths Docker, migration, worker, Monitor, runtime facial e blob divergente.

## 2. Inventário e release API/web

- [x] 2.1 Implementar inventário somente-leitura para host, checkout, versão, schema, serviços, configuração Compose efetiva, portas e endpoints; verificar minimização de dados e fingerprint reproduzível. Evidência local: `bash scripts/test_deploy_prod_app_services.sh` exercitou saída de host/domínio/porta/schema, endpoints HTTPS e fingerprint com fixtures; comprovou ausência de build/recriação/tag de imagens no inventário.
- [x] 2.2 Implementar publicação e rollback aprovados de `api` e `web` com `--no-deps`, sem migration, preservando imagens/SHA e falhando fechado em fingerprint divergente; verificar todos os comandos por testes simulados. Evidência local: o mesmo teste simulou Compose/Docker/Git/curl, confirmou build/recriação somente de API/web, recusa antes de tocar imagem quando o fingerprint diverge e rollback com `--no-build --no-deps` somente dos dois serviços.
- [x] 2.3 Expandir o wrapper restrito para aceitar apenas o comando app com SHA completo e blob Git fixado; verificar rejeição de comandos arbitrários, stdin, scripts e modos mutáveis. Evidência local: `python scripts/test_production_release_workflow_policy.py` passou e verificou regex estrita, hashes Git dos dois scripts, modo inventory fixo e ausência de execução de stdin/release no wrapper.

## 3. Integração CI e documentação

- [x] 3.1 Classificar alterações em app, facial, misto ou sem release; verificar que app usa apenas o fluxo API/web, facial mantém o fluxo existente e misturas falham fechadas. Evidência local: `python scripts/test_classify_prod_release.py` (4 testes aprovados).
- [ ] 3.2 Integrar jobs de preflight e release protegidos ao CI, condicionados a CI verde e ao classificador; verificar que app não dispara o job facial e que nenhum job de produção roda em PR.
- [x] 3.3 Documentar alvo, manifesto Compose, porta/domínio, interrupção possível, wrapper e rollback em português; verificar os comandos documentados contra os testes de política. Evidência local: `docs/DEPLOY-PROD-APP.md`, conferido pela política do workflow e sintaxe YAML aprovada.
- [ ] 3.4 Executar validações de script, políticas, OpenSpec estrito, CI completo do PR e revisão do diff; registrar SHAs e resultados sem marcar release como publicado.

## 4. Gates operacionais humanos

- [ ] 4.1 Após aprovação da implementação, atualizar o wrapper root-owned por procedimento operacional autorizado e conferir owner, modo e blob instalado; registrar bloqueio caso não haja acesso/autorização específica.
- [ ] 4.2 Executar inventário somente-leitura no SHA integrado, apresentar fingerprint, impacto e rollback e aguardar aprovação humana protegida para esse inventário exato.
- [ ] 4.3 Após aprovação, acompanhar release e smoke tests; registrar SHA, revisão do banco e estado de saúde ou executar apenas rollback inventariado e aprovado.

## Workflow follow-up

- Arquivar a change e sincronizar a spec principal somente após revisão humana e evidência de release ou após registrar claramente o bloqueio operacional restante.

## Evidência e bloqueios em 2026-10-17

- PR #202, SHA atual `b77fcd07f5d703fddd3b69fcc6acdbe458b4ec8e`, estava atrás da `main` `f89f2e3`. CI #38989166580 passou frontend, OpenSpec e Gitleaks; `homolog-inventory-policy` falhou porque o pin facial não contemplava o runtime compartilhado alterado pela Estatística; backend ainda estava em execução no último snapshot.
- O release saudável de produção confirmado continua em `f2ac110fb648e0158d1896923ade0661b006a276`. A `main` contém mudanças faciais posteriores ainda não presentes nesse baseline, incluindo `backend/app/facial/reference.py` e `frontend/app/public-galleries/facial-search-panel.tsx`. O verificador app compara o candidato com o checkout ativo e as recusa; não publicar esses blobs pelo fluxo API/web.
- A política local do workflow API/web passou; o verificador executado contra `origin/main` desde `f2ac110` recusou como esperado (`arquivo_fora_do_escopo`) por esses runtimes faciais dedicados. Essa recusa precede qualquer build, container ou aprovação de produção.
- A cópia root-owned `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper` ainda precisa receber e ter conferido o comando/app blob antes de inventário remoto. Nenhuma ação remota ou alteração de produção foi executada nesta implementação.
- O script inclui fingerprint, backup de imagens e release API/web; o inventário/rollback aprovado ainda não está implementado nem validado, portanto a task 2.2 permanece aberta.
