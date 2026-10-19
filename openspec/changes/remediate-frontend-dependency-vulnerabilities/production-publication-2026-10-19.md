# Pick-your-Pic — publicação web-only concluída

## 1. Resultado: PUBLICADO

Publicação manual autorizada na Oracle em **19/10/2026, 08:04:45 BRT** (11:04:45 UTC). Verificação independente final às 08:08:13 BRT. A correção de segurança do frontend está disponível para os clientes.

## 2. Identidade efetivamente publicada

- SHA frontend/checkout: `4b464f081dfa2451472848622853460398834e6d`.
- Nova imagem em execução: `sha256:6aef1935d8a4ba4bfc125a1bf5bea52ae6e26db361ef4942a1fedc55c4efc20a`.
- Container novo: `298a3c5fc91e4394ce33415457e1ea4cd78e8097b067f3b8bf247f637588a6fa`.
- Imagem anterior preservada: `sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573`.
- Origem e checkout anteriores: `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`.
- Referência de recuperação validada por ID: `markina-gallery-web:rollback-9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573`.
- Next.js **16.4.0**, sharp **0.35.5**, Node **v24.22.0**, conferidos por leitura no container publicado e comparados ao lockfile aprovado. Build ID `yaHHcfsXPnMGPdpXunN8G`. source-map-js não aparece como pacote autônomo no standalone; nenhuma instalação adicional foi feita.

## 3. Saúde, HTTPS e disponibilidade

Os endpoints `/healthz`, `/api/health`, `/` e `/admin/payments` retornaram **200**; `/admin/statistics` retornou **404**. Vendas/pagamentos disponível por HTTP e Estatísticas permanece removida. Sem OTP, transação financeira ou envio real como teste.

Asset público `/_next/static/chunks/1-nqmp1rl8kqt.js` retornou 200 e tem exatamente o mesmo SHA256 do arquivo no container novo: `cd8e8b5b5f9a280bd64064eca10fc2ac616a4a0f14ede9ef39e880ac13c39f78`. A confirmação não se baseia apenas na saída do script de publicação.

## 4. Estado final dos serviços

**15/15 serviços ativos saudáveis.** Existe também o migrate histórico parado, mantido intacto.

| Serviço | Estado final |
|---|---|
| api | Saudável |
| db | Saudável |
| evolution-api | Saudável |
| evolution-db | Saudável |
| evolution-redis | Saudável |
| face-gemma-index-worker | Saudável |
| face-index-worker | Saudável |
| face-maintenance-worker | Saudável |
| face-search-worker | Saudável |
| migrate | Parado, preservado |
| nginx | Saudável |
| preview-adjustment-worker | Saudável |
| raw-development-worker | Saudável |
| redis | Saudável |
| web | Saudável |
| worker | Saudável |

## 5. Preservação dos serviços e dados

A comparação anterior/posterior confirmou que somente web mudou de ID/imagem/início. Os 15 containers não-web (14 ativos e migrate histórico parado) mantiveram IDs, imagens, início, estado, configuração, portas, redes e montagens. API APP_VERSION continua em fe1f3bc6e1a483bd1ac5f4e71149f903e724873f.

Nenhuma alteração operacional em API, banco/schema/migrations, workers, Redis, Nginx, proxy, volumes, fotografias, ambiente/segredos ou terceiros. Nenhuma limpeza Docker. Hashes dos seis Compose e ambiente permanecem iguais; lock mantém inode/tamanho/mtime e está livre. A aplicação continuou funcionando; isso não é uma auditoria bit a bit de dados alterados por seu uso normal.

Recibo atual e marcador web apontam ao SHA/imagem publicados; recibo anterior guarda exatamente fe1f3bc6/9567b1d8; registros de adoção e release constam em web-history.log. Marcadores app/global anteriores foram preservados. Nenhuma tentativa ficou pendente.

## 6. Rollback

**Não foi necessário nem executado.** O modo somente leitura rollback-inventory passou e comprovou a restauração disponível exatamente para a imagem/checkout anteriores autorizados, com mesmo snapshot não-web/configuração. A imagem antiga continua presente sob a referência dedicada, validada pelo ID; não foi usada uma versão histórica diferente.

## 7. Pendências e limites

Nenhuma pendência impeditiva identificada para esta manutenção. Os cinco alertas altos de ferramentas dev já documentados continuam fora desta correção runtime; o npm ci do builder os informou, como previsto. O resultado runtime zero vem da auditoria anterior do lockfile aprovado, preservado nesta operação; não foi iniciada auditoria geral nova. As versões corrigidas foram conferidas na imagem em produção.

Duas leituras auxiliares de coleta precisaram de compatibilidade local: Python 3.8 não oferece str.removeprefix e sharp não exporta package.json via require. Foram ajustados apenas os comandos locais de leitura (fatiamento de string e leitura direta do JSON). Nenhum script aprovado, aplicação ou configuração do servidor foi alterado por isso; evidências iniciais e a leitura final aprovada estão preservadas. Não foram falhas do release nem exigiram rollback.

Os registros OpenSpec finais são consolidados neste conjunto documental; sincronização/arquivamento permanecem sujeitos à revisão humana. Isso não impede a utilização do frontend publicado.

## 8. Segurança disponível aos clientes

**Sim: a correção identificada está efetivamente em produção e disponível aos clientes**, no frontend do SHA aprovado, comprovada por imagem/recibo, versões runtime, saúde e conteúdo público correspondente ao container novo.

## Histórico consolidado das integrações e do bloqueio resolvido

| Etapa | Resultado e evidência |
|---|---|
| PR #226 — dependências | Integrado em `81eb0741ab824a74a1f2b4f3df4dfb86da81b5c5`; [CI pós-merge aprovado](https://github.com/conradodeita/markina-gallery/actions/runs/39167932644). Auditoria runtime zero; cinco altas dev preservadas e documentadas. |
| PR #227 — identidade e recuperação web | Integrado em `34d2afd5b8f407adb70b0dee165fa8d55a83b478`; [CI do PR](https://github.com/conradodeita/markina-gallery/actions/runs/39174812713) e [pós-merge](https://github.com/conradodeita/markina-gallery/actions/runs/39177622419) aprovados. 32 contratos de release e backend 1709 aprovados/23 ignorados. |
| Tentativa de 18/10 BRT no SHA de #227 | Bloqueada em reconcile-inventory: `map has no entry for key "Health"` no migrate histórico parado. Somente fetch preparatório de Git; nenhuma adoção, tag, build ou substituição web. A imagem anterior e os serviços permaneceram intactos. |
| PR #228 — Health opcional | Integrado em `4b464f081dfa2451472848622853460398834e6d`; [CI do PR](https://github.com/conradodeita/markina-gallery/actions/runs/39183663312) e [pós-merge](https://github.com/conradodeita/markina-gallery/actions/runs/39186678648) aprovados. 35 contratos e backend 1709 aprovados/23 ignorados/658 warnings; Code Review final sem apontamentos acionáveis. |
| Publicação de 19/10 BRT | Autorização específica para #228, reconciliação auditável, imagem anterior preservada por ID e atualização exclusivamente web; resultado final descrito neste documento. |

O diagnóstico anterior mostrou marcador web legado divergente do release conjunto e abertura de lock que truncava seu conteúdo. O PR #227 introduziu recibos de identidade, adoção auditável, inventários sem escrita e lock sem truncamento. O PR #228 corrigiu a leitura de Health/Status opcionais, mantendo containers parados no snapshot e as recusas para inspect falho ou campo obrigatório ausente. A regressão reproduziu a falha real antes e passou depois com Docker CLI real contra API sintética.

Os três merges tiveram `release_scope=none`, com sete jobs remotos ignorados; nenhum deles publicou a aplicação. A publicação descrita aqui foi manual e separadamente autorizada. Os registros finais locais dos commits `a6b094e`, `9311227`, `88ede3c`, `7917b1b` e `3a613a0` foram reconciliados nesta documentação; suas branches originais não foram apagadas. O PR #177 para develop foi preservado, sem integração por este trabalho.

## Evidências para revisão independente

- `01-before-readonly.stdout` e `01-before-summary.json`: gates iniciais e imagem/proveniência autorizadas.
- `02-readonly-gates.stdout`: Compose/HTTPS antes das escritas.
- `03-prepare-approved-commit.stdout`: SHA/árvore/blobs verificados após fetch.
- `04-reconcile-inventory.stdout`, `05-reconcile.stdout`: fingerprint e adoção auditável.
- `06-release-inventory.stdout`, `07-release.log` e `.meta.json`: imagem anterior preservada, build e substituição exclusivamente web, exit 0.
- `08-after-readonly.stdout`, `11-final-stability.stdout`, `12-final-comparison.json`: estados e identidades completos, sem drift não-web.
- `09-rollback-readiness.stdout`: capacidade de recuperação exata confirmada por leitura.
- `10-independent-verification.stdout`: HTTPS, versões efetivas, asset público e histórico. Leituras auxiliares iniciais estão nos arquivos 10-initial-collector-compatibility e 10-package-metadata-export-check.
- `SHA256SUMS.json`: integridade dos arquivos do pacote. Valores de segredos/ambiente e dados de clientes não foram incluídos.

Fonte e CI: [PR #226](https://github.com/conradodeita/markina-gallery/pull/226), [PR #227](https://github.com/conradodeita/markina-gallery/pull/227), [PR #228](https://github.com/conradodeita/markina-gallery/pull/228), [CI final do SHA publicado](https://github.com/conradodeita/markina-gallery/actions/runs/39186678648). A proveniência da imagem anterior foi conferida no run 39135274157, tentativa 2, job 117710134038. No encerramento operacional, main estava em `4b464f081dfa2451472848622853460398834e6d`; PR #177 e develop foram preservados. Commits exclusivamente documentais posteriores não modificam o SHA efetivamente publicado.

Pacote original preservado localmente: `pickyourpic-web-release-20261019-evidencias.zip`, SHA-256 `b1b5451170648245dd281a1d79e150abbb8bfdbae264af8813dc1b0f3af69414`. Os arquivos brutos sanitizados continuam fora do Git; os nomes acima permitem conferência no pacote compartilhável. Esta consolidação publica somente documentação e não modifica o SHA implantado. Não arquivar/sincronizar specs sem revisão humana.
