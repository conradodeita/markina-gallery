# Release de API e web em produção

Este fluxo publica somente `api` e `web` para uma mudança comercial previamente revisada. Ele é separado da manutenção facial: alterações mistas são recusadas pelo classificador e não iniciam nenhum release automaticamente.

## Alvo e impacto

- Host: `clearbudget-vnic` (`132.145.193.169`), projeto Compose `markina-gallery` em `/opt/markina-gallery`.
- Compose: `docker/docker-compose.yml`, com os arquivos adicionais ativos inventariados pelo próprio servidor.
- Domínio público: `https://markina.pickyourpic.com.br`.
- Entrada Nginx da Markina: `127.0.0.1:8080`; o inventário valida o bind antes da aprovação.
- Serviços recriados: somente `api` e `web`, com `--no-deps`; nenhum worker, banco, Nginx, volume ou serviço externo é recriado.
- Sem migrations. O schema precisa permanecer em `20261017_0084`.
- A reinicialização da API pode interromper brevemente qualquer rota atendida por ela, inclusive a disponibilidade temporária do Monitor. Nenhum arquivo, regra ou dado próprio do Monitor faz parte do release.

## Gates

CI verde e classificação `app` são pré-requisitos. O manifesto registra a base saudável `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`, publicada em 18/10/2026, e o schema observado `20261017_0084`. O classificador usa essa base em vez do `before` da branch: uma reconciliação de `main` com commits que já estão implantados resulta em `none`, enquanto um delta descendente pode selecionar um release. Após cada release saudável, a base deve ser avançada para o novo SHA confirmado, sem runtime adicional, e o manifesto de blobs deve refletir o estado aprovado.

Para a identificação de responsáveis em pastas privadas, o manifesto fixa `backend/app/main.py`, `backend/app/private_folder_overview.py`, `frontend/app/admin/galleries/private-folder-client-overview.tsx` e `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx`, além dos runtimes já permitidos. Testes, OpenSpec e runbooks podem acompanhar. Alterações em Docker/Compose, migrations, workers, código do Monitor ou outros runtimes bloqueiam o fluxo. O preflight também compara o candidato com o checkout ativo; alterações faciais não são publicadas junto com o app.

O preflight usa a chave de leitura e o wrapper SSH restrito, inventaria checkout, versão ativa, revisão do banco, estado saudável, hashes da configuração resolvida, portas e smoke HTTPS. O fingerprint cobre o SHA candidato e o estado ativo. O JSON Compose resolvido não é impresso nem gravado.

Somente após o inventário exato, o job `production` aguarda aprovação protegida. Ele recalcula o fingerprint, salva tags e referências das imagens anteriores, constrói `api` e `web`, recria apenas esses dois serviços, valida saúde, verifica e recarrega somente o Nginx da Markina e testa HTTPS. Falhas não disparam rollback automático. O worker OTP e os workers faciais permanecem fora da lista de serviços e não serão recriados; a reinicialização da API ainda pode interromper brevemente rotas HTTP/OTP, por isso o estado do worker deve ser conferido antes e depois. A recuperação é iniciada manualmente pelo `workflow_dispatch`: o preflight inventaria novamente o SHA anterior, as imagens e o runtime; depois, `production` exige aprovação própria antes de restaurar apenas API/web.

## Pré-requisito operacional

O servidor usa um wrapper root-owned em `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper`, instalado na chave restrita de preflight. O wrapper precisa reconhecer `MARKINA_APP_TARGET_SHA=<SHA completo>` e `MARKINA_APP_ROLLBACK_SHA=<SHA completo>` e fixar o blob revisado de `scripts/deploy-prod-app-services.sh`. A mudança no arquivo do repositório não instala nem atualiza a cópia root-owned. Antes do primeiro preflight app, o operador autorizado deve instalar a versão revisada pelo procedimento do servidor e conferir proprietário, modo e hash; até essa conferência, o release permanece bloqueado.

O run `39025690297` registrou que a cópia instalada recusou `MARKINA_APP_TARGET_SHA` como comando não permitido. Portanto, a existência das regras novas neste repositório não comprova que o wrapper do host foi atualizado; até instalar e conferir a cópia root-owned, nenhum preflight app válido nem publicação pode ser declarado.

Em 18/10/2026, a comparação SSH confirmou que a única diferença da cópia instalada era o pin app `37e9c17b4affe5e8a823a8be93e186b4e4ad226d`. A cópia root-owned foi atualizada para o wrapper revisado de `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`, com owner `root:root`, modo `0755`, blob Git `95f04139093a146c8f66ddd60e299ff76f57e2b3` e SHA-256 `253f9407a322822122d8339216ea9895482e386749b795c6724d524de4f8bfb2`. O pin app passou a `6767d0ba092adb23666ab612db505af2e0900b35`; o pin facial permaneceu igual. A chave restrita continuou recusando comandos arbitrários. A cópia anterior foi preservada em `/var/backups/markina-gallery-preflight-ssh-wrapper-20261018-fe1f3bc6`.

O run `39135274157`, tentativa 2, concluiu preflight e release API/web com aprovação protegida do proprietário, sem migrations. O checkout anterior era `ffea8c437b9940498487476f6167fdeec1067e2e`; API/web novos e demais serviços ficaram saudáveis. Evidências e limites em `docs/RELEASE-SALES-PAYMENTS-20261018.md`.

As variáveis e chaves existentes do GitHub Environment `production-preflight` e `production` são reutilizadas. Nenhum segredo deve ser copiado para o repositório, logs, manifestos ou arquivos `.env`.
## Exclusão mútua com o release web-only

As operações mutáveis `release` e `rollback` adquirem o lock exclusivo `/var/lib/markina-gallery/deploy-state/production-release.lock`. O procedimento `deploy-prod-web.sh` usa o mesmo arquivo de lock e recusa iniciar enquanto houver release API/web em andamento ou tentativa API/web sem conclusão. Se o lock estiver ocupado, ausente ou houver uma tentativa web-only pendente, a operação falha antes de alterar serviços. Os modos de inventário permanecem somente-leitura e não disputam o lock de mutação.
