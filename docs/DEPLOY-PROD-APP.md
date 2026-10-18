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

CI verde e classificação `app` são pré-requisitos. O manifesto registra a base saudável `b4f15abd6a71585082758062feba7fcfcc225587` e o schema observado `20261017_0084`. O classificador usa essa base em vez do `before` da branch: uma reconciliação de `main` com commits que já estão implantados resulta em `none`, enquanto um delta descendente pode selecionar um release. Após cada release saudável, a base deve ser avançada para o novo SHA confirmado, sem runtime adicional, e o manifesto de blobs deve refletir o estado aprovado.

Para a identificação de responsáveis em pastas privadas, o manifesto fixa `backend/app/main.py`, `backend/app/private_folder_overview.py`, `frontend/app/admin/galleries/private-folder-client-overview.tsx` e `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx`, além dos runtimes já permitidos. Testes, OpenSpec e runbooks podem acompanhar. Alterações em Docker/Compose, migrations, workers, código do Monitor ou outros runtimes bloqueiam o fluxo. O preflight também compara o candidato com o checkout ativo; alterações faciais não são publicadas junto com o app.

Para iniciar ou repetir um preflight após a integração, execute manualmente o workflow `CI` na branch `main` e selecione `app-release`. O dispatch padrão (`none`) não faz inventário nem release. A opção `app-release` roda a suíte completa, verifica o manifesto e segue pelo mesmo preflight read-only e gate de aprovação protegida usado no push. `app-rollback` continua separado e exige escolha explícita.

O preflight usa a chave de leitura e o wrapper SSH restrito, inventaria checkout, versão ativa, revisão do banco, estado saudável, hashes da configuração resolvida, portas e smoke HTTPS. O fingerprint cobre o SHA candidato e o estado ativo. O JSON Compose resolvido não é impresso nem gravado.

Somente após o inventário exato, o job `production` aguarda aprovação protegida. Ele recalcula o fingerprint, salva tags e referências das imagens anteriores, constrói `api` e `web`, recria apenas esses dois serviços, valida saúde, verifica e recarrega somente o Nginx da Markina e testa HTTPS. Falhas não disparam rollback automático. O worker OTP e os workers faciais permanecem fora da lista de serviços e não serão recriados; a reinicialização da API ainda pode interromper brevemente rotas HTTP/OTP, por isso o estado do worker deve ser conferido antes e depois. A recuperação é iniciada manualmente pelo `workflow_dispatch`: o preflight inventaria novamente o SHA anterior, as imagens e o runtime; depois, `production` exige aprovação própria antes de restaurar apenas API/web.

## Pré-requisito operacional

O servidor usa um wrapper root-owned em `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper`, instalado na chave restrita de preflight. O wrapper precisa reconhecer `MARKINA_APP_TARGET_SHA=<SHA completo>` e `MARKINA_APP_ROLLBACK_SHA=<SHA completo>` e fixar o blob revisado de `scripts/deploy-prod-app-services.sh`. A mudança no arquivo do repositório não instala nem atualiza a cópia root-owned. Antes do primeiro preflight app, o operador autorizado deve instalar a versão revisada pelo procedimento do servidor e conferir proprietário, modo e hash; até essa conferência, o release permanece bloqueado.

O run `39025690297` registrou que a cópia instalada recusou `MARKINA_APP_TARGET_SHA` como comando não permitido. Portanto, a existência das regras novas neste repositório não comprova que o wrapper do host foi atualizado; até instalar e conferir a cópia root-owned, nenhum preflight app válido nem publicação pode ser declarado.

As variáveis e chaves existentes do GitHub Environment `production-preflight` e `production` são reutilizadas. Nenhum segredo deve ser copiado para o repositório, logs, manifestos ou arquivos `.env`.
