# Tasks

## 1. Resolver os pins de segurança

- [x] 1.1 Atualizar somente `aiohttp`, `multidict`, `urllib3` e o pin incompatível `yarl` conforme o design. Evidência: `backend/requirements-push.txt` agora fixa `aiohttp==3.14.4`, `multidict==6.9.1`, `urllib3==2.8.0` e `yarl==1.25.1`; os demais pins não mudaram.
- [x] 1.2 Confirmar instalação resolvida e `pip check` no conjunto compartilhado, preservando os demais pins. Evidência: `py -3.13 -m pip install --dry-run --ignore-installed -r backend/requirements.txt -r backend/face-requirements.txt -r backend/benchmark-requirements.txt` resolveu o conjunto; instalação isolada equivalente concluiu e `pip check` retornou “No broken requirements found”.

## 2. Validar runtimes consumidores

- [x] 2.1 Executar testes backend e validar builds/checks da API, Gemma, face e workers que instalam `requirements.txt`. Evidência inicial: CI #39422192774 passou nos testes integrais do backend, build+inferência sintética offline do Gemma e builds isolados de API, ajuste de prévias e RAW. A instalação do backend incluiu `face-requirements.txt`; o Dockerfile.gemma também instalou os requisitos faciais e preparou os mesmos ativos SFace. Validação complementar: CI do SHA final do PR deve construir `Dockerfile.face` em amd64 e arm64, conforme `facial-assets/model-manifest.json`; builds são isolados, sem publicação ou serviços.
- [x] 2.3 Construir isoladamente `Dockerfile.face` para amd64 e arm64 no CI hospedado, verificando instalação dos pins corrigidos e preparo dos assets faciais sem publicar imagem nem iniciar serviços. Evidência: CI #39432122436, SHA `0330eff8e1233109fbeb80da807601c1c1beb787`; os dois builds completaram no job `runtime-images` sem publicar imagens ou iniciar serviços.
- [x] 2.2 Registrar falhas externas de runner separadas de incompatibilidade e confirmar que nenhum job de deploy/publicação foi executado. Evidência: o candidato antigo #253 falhou por conflito real `aiohttp 3.14.4` × `yarl 1.24.5`; #251 teve OOM no build de modelos em runner; o candidato #254 resolveu as dependências e passou. No CI #39422192774, `deploy-homolog`, `release-scope`, preflights e releases de produção foram `skipped`; nenhuma execução acessou Oracle.

## 3. Preparar PR sem integrar

- [x] 3.1 Revisar diff e validar OpenSpec; criar commit e PR direcionados à `main`. Evidência: commit inicial `8b380fb3bf1e6a9c3b846840e21ba967642f2151`, PR #254 para `main`; validação OpenSpec estrita passou.
- [x] 3.2 Confirmar checks do PR, os 14 alertas associados e os limites de produção/Oracle antes do relatório final. Evidência: CI #39422192774 passou em todos os checks obrigatórios no SHA `8b380fb3bf1e6a9c3b846840e21ba967642f2151`; os 14 alertas permanecem abertos até merge em `main`. PR sem automerge, sem deploy e sem acesso/modificação à Oracle.
- [x] 3.3 Confirmar que o PR continua atualizado com `main`, que os checks obrigatórios e builds faciais passam no SHA final, e que a análise de escopo pós-merge exclui deploy, preflight operacional e release. Evidência: PR #254 alinhado à `main` `f15425dd479c579540752d01737240f3568ef308`; CI #39432122436 passou no SHA `0330eff8e1233109fbeb80da807601c1c1beb787`. `classify_prod_release.py` retornou `release_scope=none`; no CI, `deploy-homolog`, `release-scope`, preflights e releases foram `skipped`.
