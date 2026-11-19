# Release de API e web em produção

## Ponte para snapshots protegidos — candidato de 18/11/2026

Esta seção atualiza o procedimento para a configuração real do host; as notas de outubro abaixo são histórico. A change `add-root-only-compose-release-bridge` registra a autorização do proprietário para ponte root-only e prova semântica por serviço. Implementação local e CI não comprovam instalação nem publicação no servidor: consultar as evidências da change.

- API e web podem usar fontes e diretórios diferentes. A ponte lê os labels de cada serviço e valida caminhos, proprietário, proteção de escrita e checksums. Não é necessário recriar containers para acrescentar `config-hash` ausente.
- A prova semântica inclui defaults das imagens, ambiente, comando, healthcheck, mounts, redes e políticas Docker. Diferença ou campo sem contrato bloqueia. O digest semântico não é um label Compose e não substitui os IDs de imagem, versão, saúde e fontes no fingerprint.
- Instalar pelo workflow manual **Instalar ponte API e web em produção** (`production-app-compose-bridge-install.yml`) em `main`. O primeiro job reaproveita o CI do mesmo SHA. O job protegido em `production` revalida a evidência antes de instalar os dois blobs revisados e confere que os IDs, imagens, inícios e estados dos containers permanecem iguais.
- O executável fica em `/usr/local/sbin/markina-gallery-app-compose-bridge` (`root:root 0755`); backups do executável/wrapper ficam em `/var/backups/markina-gallery`, arquivos `0600`. Não alterar sudoers ou permissões das fontes para fazê-las legíveis pela conta comum.
- O instalador faz fetch somente de `origin/main`, sob o lock operacional, para disponibilizar objetos de suporte; o checkout ativo permanece no SHA anterior. O preflight não faz fetch nem grava estado persistente. Cópias temporárias privadas são removidas na saída.
- Após a instalação, se o push do mesmo SHA falhou só no preflight, usar `gh run rerun <run-id> --failed` para preservar os jobs de CI verdes e repetir o inventário. Em outro caso elegível, usar `operation=app-release`. O preflight somente leitura identifica domínio `https://markina.pickyourpic.com.br`, entrada `127.0.0.1:8080`, schema `20261113_0126`, configuração facial e fingerprint. O job de release aguarda a revisão de `production` e recalcula o fingerprint antes de alterar estado.
- A imagem API base é exportada pelo próprio preflight read-only: somente o ID ativo inventariado é enviado por stdout do wrapper restrito. O runner ARM64 cria a camada API sobre esse ID, copiando somente `backend/app`; web usa o Dockerfile versionado. O bundle privado registra SHA, digest, ID-base, IDs das imagens e plataforma, e fica retido no Actions por um dia. Assim o runtime facial e as dependências ativas são preservados sem reconstrução no host.
- Depois de todos os gates de CI e da aprovação de `production`, o job verifica novamente o bundle e o ID-base, transfere os bytes usando uma chave SSH distinta com wrapper de upload forçado, e o executor valida digest/SHA/base antes de `docker load`. O modelo aplicado muda somente imagem e `APP_VERSION` da API. Redes e volumes são externos; `up` é limitado por serviço com `--no-build --no-deps --pull never`.
- Não reutilizar o recibo web antigo se ele não corresponde à imagem atual. Bootstrap somente leitura exige prova semântica e revisão de release igual ao checkout ancestral aprovado. Após sucesso, salvar recibo de imagem/digest semântico da nova versão.
- Em falha, conservar marcadores e cópias. `operation=app-rollback` exige inventário/aprovação próprios, confere cópias e restaura somente API/web. Não restaurar banco, limpar fontes ou executar rollback automático. O Nginx só recebe teste/reload já autorizado.
- Conclusão exige IDs de imagem e versão corretos, semântica preservada, schema intacto, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, saúde e HTTPS. Preservar evidência de invariância dos outros serviços. Não apagar cópias de recuperação sem política própria aprovada.

Este fluxo publica somente `api` e `web` para uma mudança comercial previamente revisada. Ele é separado da manutenção facial: alterações mistas são recusadas pelo classificador e não iniciam nenhum release automaticamente.

## Alvo e impacto

- Host: `clearbudget-vnic` (`132.145.193.169`), projeto Compose `markina-gallery` em `/opt/markina-gallery`.
- Compose: `docker/docker-compose.yml`, com os arquivos adicionais ativos inventariados pelo próprio servidor.
- O overlay `docker/docker-compose.raw-development.yml` foi aposentado e não faz parte da lista exigida pelos helpers API/web. A ausência de qualquer outro manifesto esperado continua bloqueando o inventário e informa o caminho ausente.
- Domínio público: `https://markina.pickyourpic.com.br`.
- Entrada Nginx da Markina: `127.0.0.1:8080`; o inventário valida o bind antes da aprovação.
- Serviços recriados: somente `api` e `web`, com `--no-deps`; nenhum worker, banco, Nginx, volume ou serviço externo é recriado.
- Sem migrations. Para o candidato atual, o schema precisa permanecer em `20261113_0126` e a base ativa é `bfe511f850224823254b0fc9f51fa7ff60ecfba0`.
- A reinicialização da API pode interromper brevemente qualquer rota atendida por ela, inclusive a disponibilidade temporária do Monitor. Nenhum arquivo, regra ou dado próprio do Monitor faz parte do release.

## Gates

CI verde, classificação `app` e preflight somente-leitura são pré-requisitos. O manifesto é reconciliado com a versão da API e o schema observados em produção para cada candidato. Em 17/11/2026, a API saudável reportou `bfe511f850224823254b0fc9f51fa7ff60ecfba0` e schema `20261113_0126`; esses valores são a base deste candidato, sem migration. API/web são construídas uma única vez no runner ARM64 a partir do SHA integrado, com a imagem API ativa fixada pelo preflight; o classificador usa a base ativa em vez do `before` da branch. Depois de cada release saudável, a base deve avançar para o SHA confirmado.

O manifesto fixa os blobs de API/web aprovados para cada candidato. Para este candidato, ele também fixa os módulos exatos do Picker e do backup global. O módulo `runtime_worker.py` pode ser incluído como código inerte na imagem API, mas nenhum worker/processo, unidade ou timer será instalado ou iniciado; nenhuma cópia será criada. Os arquivos de unidade, timer e lock têm allowlist e hashes próprios, mas não são aplicados pelo deploy API/web; `pyp-platform-backup.service` e `pyp-platform-backup.timer` não serão instalados nem iniciados. Testes, OpenSpec e runbooks podem acompanhar. Alterações em migrations, Docker/Compose, outros workers, código do Monitor ou runtimes fora dos pins bloqueiam o fluxo. O preflight compara o candidato com o checkout ativo; alterações faciais não são publicadas junto com o app.

O preflight usa a chave de leitura e o wrapper SSH restrito, inventaria checkout, versão ativa, revisão do banco, estado saudável, hashes da configuração resolvida, portas e smoke HTTPS. O fingerprint cobre o SHA candidato e o estado ativo. O JSON Compose resolvido não é impresso nem gravado.

## Preservação do reconhecimento facial

Em 14/11/2026, o proprietário informou que o reconhecimento facial está funcionando em produção e precisa permanecer com `FACIAL_PROCESSING_ENABLED=true` após deploy. O fluxo API/web valida a variável no runtime atual, no Compose resolvido e no Compose do SHA alvo antes do build/recreate; rollback também valida o alvo antes de recriar os serviços. O fluxo facial dedicado valida API e `face-search-worker`, e o release legado de aposentadoria InfinitePay valida a API e os workers que recria. Se a configuração estiver ausente ou resolver para outro valor, o gate aborta sem alterar os containers. O deploy não ativa a flag por conta própria nem inicia/reindexa workers.

Os pins versionados do wrapper restrito acompanham esses guards: facial `515c3c82c30bf76be0ec8f01013225fb71276df3`, API/web `cd8288133ce204285f6c6abf0cfda5fcf59ce2d2`, export read-only da imagem-base `b94df86a3e51901608ee0d5f33d0fd257200f595` e aposentadoria `d8fb13a50b5254e458f19d2c5d4ed8c43fadea1b`. A cópia root-owned no host é independente e precisa ser atualizada/conferida pelo procedimento autorizado antes de um preflight que use os novos scripts.

O `.env.example` continua com o default local `false`; isso não define o ambiente operacional. A fonte de configuração da produção deve resolver a flag explicitamente como `true`. O fluxo único de transição APP_ENV em `transition-biometric-app-env-context` foi concluído em outubro e não é o caminho de deploy API/web; suas evidências documentam aquela execução, não o estado atual informado pelo proprietário.

Somente após o inventário exato e os gates completos de CI, o job `production` aguarda aprovação protegida. Ele recalcula o fingerprint, salva tags e referências das imagens anteriores, verifica e carrega o bundle do mesmo run/SHA sem build ou pull no host, recria apenas `api` e `web`, valida saúde, verifica e recarrega somente o Nginx da Markina e testa HTTPS. Falhas não disparam rollback automático. O worker OTP e os workers faciais permanecem fora da lista de serviços e não serão recriados; a reinicialização da API ainda pode interromper brevemente rotas HTTP/OTP, por isso o estado do worker deve ser conferido antes e depois. A recuperação é iniciada manualmente pelo `workflow_dispatch`: o preflight inventaria novamente o SHA anterior, as imagens e o runtime; depois, `production` exige aprovação própria antes de restaurar apenas API/web.

## Pré-requisito operacional

O servidor usa um wrapper root-owned em `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper`, instalado na chave restrita de preflight. Além dos inventários, a versão candidata aceita somente o comando read-only `MARKINA_APP_BASE_IMAGE_EXPORT_SHA=<SHA>_IMAGE_ID=sha256:<ID>` e executa o exporter pinado, que transmite apenas a imagem API ativa. A mudança no arquivo do repositório não instala nem atualiza a cópia root-owned. Antes do primeiro preflight app, o operador autorizado deve instalar a versão revisada pelo procedimento do servidor e conferir proprietário, modo e hash; até essa conferência, o release permanece bloqueado.

O upload usa outro wrapper root-owned, `/usr/local/sbin/markina-gallery-app-artifact-ssh-wrapper`, e uma chave pública independente com forced command. Ele aceita somente SHA e digest completos, grava atomicamente em `/tmp/markina-gallery-app-artifacts-<uid>` com modo privado, verifica o tamanho e o SHA-256 e nunca extrai nem executa o conteúdo. O executor remove somente o bundle daquele SHA e o arquivo extraído ao terminar, inclusive em falha; o diretório privado permanece. O secret privado correspondente é `PRODUCTION_APP_ARTIFACT_SSH_PRIVATE_KEY`, no Environment `production`; o host e usuário devem corresponder ao destino já aprovado. A task operacional de instalação e cadastro permanece separada e pendente. Até ela ser autorizada e validada, o fluxo falha fechado antes do release.

O run `39025690297` registrou que a cópia instalada recusou `MARKINA_APP_TARGET_SHA` como comando não permitido. Portanto, a existência das regras novas neste repositório não comprova que o wrapper do host foi atualizado; até instalar e conferir a cópia root-owned, nenhum preflight app válido nem publicação pode ser declarado.

Em 18/10/2026, a comparação SSH confirmou que a única diferença da cópia instalada era o pin app `37e9c17b4affe5e8a823a8be93e186b4e4ad226d`. A cópia root-owned foi atualizada para o wrapper revisado de `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`, com owner `root:root`, modo `0755`, blob Git `95f04139093a146c8f66ddd60e299ff76f57e2b3` e SHA-256 `253f9407a322822122d8339216ea9895482e386749b795c6724d524de4f8bfb2`. O pin app passou a `6767d0ba092adb23666ab612db505af2e0900b35`; o pin facial permaneceu igual. A chave restrita continuou recusando comandos arbitrários. A cópia anterior foi preservada em `/var/backups/markina-gallery-preflight-ssh-wrapper-20261018-fe1f3bc6`.

O run `39135274157`, tentativa 2, concluiu preflight e release API/web com aprovação protegida do proprietário, sem migrations. O checkout anterior era `ffea8c437b9940498487476f6167fdeec1067e2e`; API/web novos e demais serviços ficaram saudáveis. Evidências e limites em `docs/RELEASE-SALES-PAYMENTS-20261018.md`.

As variáveis e chaves existentes do GitHub Environment `production-preflight` e `production` são reutilizadas. Nenhum segredo deve ser copiado para o repositório, logs, manifestos ou arquivos `.env`.
## Exclusão mútua com o release web-only

As operações mutáveis `release` e `rollback` adquirem o lock exclusivo `/var/lib/markina-gallery/deploy-state/production-release.lock`. O procedimento `deploy-prod-web.sh` usa o mesmo arquivo de lock e recusa iniciar enquanto houver release API/web em andamento ou tentativa API/web sem conclusão. Se o lock estiver ocupado, ausente ou houver uma tentativa web-only pendente, a operação falha antes de alterar serviços. Os modos de inventário permanecem somente-leitura e não disputam o lock de mutação.


## Coordenação com web-only — correção de outubro/2026

A change `fix-production-web-release-state` substitui a inferência do web por marcador pelo recibo `web-current.identity` (origem, ID Docker, hash Compose e checkout). App publica esse recibo após sucesso e restaura o recibo anterior em rollback; após web-only, API APP_VERSION pode permanecer anterior ao checkout desde que backend seja idêntico. IDs de recuperação e versão API anterior são conferidos independentemente do SHA de checkout. Tags de preservação usam ID, sem sobrescrever conflitos. Tentativa interrompida mantém bloqueio/recuperação aprovada; API indisponível para conferir schema continua bloqueio, sem enfraquecer o gate de banco.

Inventário app e wrapper candidato não criam temporários nem fazem fetch. Os objetos do alvo/helpers pinados devem ser obtidos previamente em preparação autorizada. O wrapper versionado valida corpo em memória por blob antes de alimentar o Bash; não executa stdin arbitrário do cliente. Sua instalação remota depende de autorização própria e não faz parte da publicação web-only de segurança. O pin antigo instalado impede automaticamente usar um script app diferente, preservando falha fechada.

Este fluxo app continua limitado a API/web, com revisão do banco, allowlist, aprovação protegida e recarga nginx anteriormente especificadas. Não deve ser usado para a atualização de dependências. O runbook `DEPLOY-PROD-WEB.md` define a publicação restrita e a solicitação conjunta de preparação/publicação/validação/recuperação.
