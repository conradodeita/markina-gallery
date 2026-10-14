## Authorization

Continuidade da integração Gemma: o proprietário autorizou push, merge e deploy em homologação, e em seguida pediu a correção da disposição visual publicada. A autorização permanece no escopo Gemma. Não há mudança de segredo, exclusão, benchmark ou ativação do seletor nesta execução.

## Inventory

Inventário SSH em 11/10/2026: /opt/markina-gallery no SHA 6453eabc87a3f0c8fb09cb4f2e1ea8537bc35243, schema conhecido 0074, API/web/Nginx/workers/SFace/Gemma saudáveis. Gemma já selecionado pelo proprietário na UI observada; preservar escolha atual. RAM disponível 19.726 MiB, disco livre 89 GiB, uso 55%.

Nginx próprio: 127.0.0.1:8080 -> 80. Subdomínio HTTPS vigente: markina-homolog.duckdns.org. Firefly bot/API/frontend/DB, nginx-proxy-manager e Portainer ativos, recursos de terceiros preservados. Nenhuma porta, rede, volume ou proxy será alterado.

## Plan

Commit seletivo e PR para develop com CI verde; atualização de inventário e backup verificável antes do merge. O deploy utiliza somente o fluxo vigente do projeto markina-gallery, preserva overlays persistidos de monitor/branding, environment e dados, incluindo worker Gemma já existente. Não há nova migration ou dependência de runtime neste ajuste. A pausa transitória atinge apenas serviços próprios pelo ciclo já aprovado; PostgreSQL/Redis, Evolution e recursos vizinhos permanecem intactos.

Após deploy, verificar SHA/schema, saúde e identidades dos vizinhos, invariância do arquivo docker/.env.homolog por hash e apresentação autenticada no navegador sem trocar o motor. Rollback de frontend/código pelo procedimento existente, sem downgrade ou restauração automática de banco.
