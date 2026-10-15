# Tasks

## 1. Extração robusta da referência

- [x] 1.1 Atualizar o caminho de consulta para normalizar a orientação e detectar/alinha o rosto em resolução adequada sob limites de bytes, pixels, passes e latência, preservando YuNet + SFace, versão, dimensão e contrato do índice; verificar provider/worker no CI do GitHub, sem executar testes localmente. Evidência: CI GitHub #38815751058 no SHA `9891afb06f74722fd3aaabcd50b09fa4905164b1` passou backend/Ruff e suíte pytest (1.632 passaram, 23 ignorados), após corrigir a expectativa de forma do array NumPy para EXIF 6; nenhum teste local executado.
- [x] 1.2 Retornar estados sanitizados distintos para ausência de rosto, múltiplos rostos e qualidade insuficiente, mantendo a comparação e a retenção atuais; verificar contratos e ausência de biometria/PII nos diagnósticos pelo CI do GitHub. Evidência: CI #38815751058 passou suíte backend e lint no SHA `9891afb`; sem novos campos de biometria/PII nos diagnósticos.
- [x] 1.3 Atualizar documentação OpenSpec e notas operacionais com limites da consulta, custos de CPU, rollback sem migration e ausência de melhora alegada sem ground truth; verificar coerência com os artefatos da change. Evidência: CI #38815751058 passou validação OpenSpec estrita; limites e rollback estão descritos em `design.md` e nas delta specs.

## 2. Orientação de captura para a cliente

- [x] 2.1 Preservar upload de fotos antigas e exigir captura guiada explícita quando a cliente escolher a câmera, exibindo enquadramento e instruções de pose, luz e estabilidade; a validação técnica do servidor deve ocorrer antes da comparação, com orientação de nova tentativa; verificar lint, testes e build executados pelo GitHub CI. Evidência: CI #38815751058 passou frontend (ESLint, Vitest e build), backend pytest e OpenSpec no SHA `9891afb`; captura de câmera segue obrigatoriamente pelo fluxo guiado.
- [ ] 2.2 Apresentar orientação específica para referência inadequada sem afirmar que a pessoa não existe na galeria; verificar fluxos de upload e câmera no CI e aceite visual do proprietário após publicação, sem teste local.

## 3. Publicação automática protegida pelo GitHub

- [ ] 3.1 Ajustar a automação para iniciar o job de produção após merge em `main` e CI verde, exigir o environment protegido `production` antes de mutações e falhar fechado em validação ou aprovação ausente; verificar políticas do workflow pelo GitHub CI.
- [ ] 3.2 Preparar preflight somente leitura que confira SHA, inventário de produção, portas/subdomínio, serviços e isolamento de terceiros; executar somente serviços Pick-your-Pic necessários conforme plano aprovado e documentar rollback; verificar automação e runbook no GitHub CI sem ler ou alterar secrets.
- [ ] 3.3 Confirmar no GitHub que branch, environment/revisores e segredos de deploy já configurados atendem ao workflow, sem imprimir ou modificar valores; registrar bloqueio se configuração da conta exigir ação do proprietário.

## 4. CI e validação de produção

- [x] 4.1 Abrir PR com somente arquivos desta change, aguardar lint, suítes, build, OpenSpec e varredura de segredos do GitHub; não executar testes localmente nem contornar job vermelho. Evidência: PR #192, SHA `9891afb06f74722fd3aaabcd50b09fa4905164b1`, CI #38815751058 totalmente verde, inclusive Gitleaks; nenhum teste local executado.
- [ ] 4.2 Após merge e disparo automático, apresentar inventário atualizado e plano de impacto zero, aguardar a aprovação do environment `production`, e registrar SHA, serviços, healthchecks e resultado do deploy; nenhuma mutação remota antes desses gates.
- [ ] 4.3 Após o deploy aprovado, o proprietário validar rapidamente com sessão autenticada upload e captura guiada, incluindo uma referência de qualidade difícil e uma imagem de busca negativa; registrar estados, sucesso/zero resultados e orientação exibida, sem colocar imagens, embeddings ou scores no Git.
- [ ] 4.4 Revisar os resultados operacionais, corrigir regressões com nova execução do CI GitHub e só considerar a change concluída após aceite humano e evidência verificável; manter pendentes os critérios de acurácia que dependam de corpus anotado.

## Bloqueios de configuração externos

- Leitura inicial de metadados GitHub em 2026-10-15: repositório `conradodeita/markina-gallery`, branch padrão `main`, sem environment `production` e sem secrets de repositório para deploy. Em seguida, foi criado o environment `production` com revisor obrigatório `conradodeita`, branch permitida somente `main` e bypass administrativo desativado; a lista de secrets desse environment continua vazia. Existem também `homolog` e `homolog-tests`; nomes de secrets foram consultados somente para homolog e nenhum valor foi lido. A API não reportou regra de proteção para `main`, coerente com a convenção em `openspec/config.yaml`.
- Tentativa de inventário remoto somente de leitura em 2026-10-15: alias `clearbudget-vnic` não resolvido pelo SSH local e conexão ao IP documentado `132.145.193.169` recusada por `Permission denied (publickey)`. O script remoto não iniciou; nenhum comando foi executado no host. Não há inventário operacional atual verificável nesta execução.
- Última referência versionada em `docs/RELEASE-PAYMENT-STATUS-API-WEB.md` registra `ubuntu@132.145.193.169`, checkout `/opt/markina-gallery`, Compose `markina-gallery`, domínio `https://markina.pickyourpic.com.br`, entrada Markina `127.0.0.1:8080`, API `:8000` e web `:3000` internos, com SHA/imagens observados `71be3b29659143293351968e15fb4886c2d72bf0` e registros de 2026-10-15. Esses valores são referências históricas e MUST ser reconfirmados no host imediatamente antes de qualquer execução.
- O rollout facial documentado em `docs/PRODUCAO-FACIAL-INVENTARIO-E-PLANO.md` ainda registra gates pendentes: base legal (humano/jurídico), calibração/equidade (corpus autorizado), capacidade ARM, inventário/recuperação atualizados, aprovação humana e fluxo infantil (representação e consentimento). A spec `productionize-facial-search` mantém produção desligada enquanto houver gate pendente; essa change não os substitui.
- Tasks 3.1–3.3 e 4.2–4.4 permanecem pendentes. A release desta mudança envolve pelo menos `web`, `api` e `face-search-worker`; o procedimento existente de produção cobre somente `web`, e outro runbook cobre API/web, sem autorizar workers faciais. Não existe ainda automação aprovada nem preflight entre serviços. Nenhum deploy foi iniciado.
- O plano preliminar, inventário versionado e gates pendentes estão em `deployment-readiness-20261015.md`. Ainda faltam credenciais SSH no environment `production` (sem compartilhar valores em chat), acesso para inventário somente de leitura e evidência/decisão para os gates faciais acima. Só então será possível confirmar serviços/imagens/portas/capacidade no host e apresentar o plano atualizado para aprovação explícita. Não criar workflow que trate secret ausente, inventário indisponível ou aprovação ausente como autorização de mutação.

## Evidências de CI

- CI #38815751058 no SHA `9891afb06f74722fd3aaabcd50b09fa4905164b1` concluiu com sucesso: backend (1.632 passaram, 23 ignorados), frontend (lint/testes/build), runtime Gemma, OpenSpec, política de inventário e Gitleaks. As falhas anteriores de fixture EXIF e da varredura foram resolvidas/ausentes nesta execução. Nenhum teste local foi executado.
