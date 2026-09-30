# Registro da liberação da fundação de propriedade

Estado em 2026-09-30: **publicada em homologação; aceite integral desta change pendente**. Este registro reconcilia o planejamento anterior com fatos observáveis, sem atribuir à primeira migration verificações que não foram registradas.

| Campo | Resultado observado |
|---|---|
| Change e etapa | `add-tenant-ownership-foundation`, etapa 1 — propriedade do acervo |
| Ambiente | Homologação, `https://markina-homolog.duckdns.org/` |
| Publicação verificável | PR [#115](https://github.com/conradodeita/markina-gallery/pull/115) integrado em `develop` em 2026-09-29 20:41 UTC; [workflow 36628097734](https://github.com/conradodeita/markina-gallery/actions/runs/36628097734) concluiu os cinco jobs, inclusive `deploy-homolog`, às 20:53 UTC |
| Versão/schema | Merge `ff680e411d0c04fd3ca82c1885204891f56451a9`; no deploy do merge, Alembic registrou `20260929_0069 (head) → 20260929_0069 (head)`. A revisão 0069 já estava aplicada antes desse workflow, conforme [inventário de 19:34 UTC](../archive/2026-09-29-fix-homologation-service-resume/validation.md). A aplicação inicial de `0068 → 0069` não tem horário/SHA operacional reconciliado neste registro. |
| Estado posterior | O deploy do PR #115 registrou `tenant=1`, `tenant_admin=1`, `admin_user=1`, `client=0`, `photo_asset=0`, quatro raízes de mídia vazias e serviços Markina saudáveis. A [verificação posterior](../archive/2026-09-29-fix-homologation-service-resume/validation.md) confirmou schema 0069, HTTPS/healthchecks HTTP 200, Evolution e serviços vizinhos ativos. Mudanças posteriores chegaram a homologação; o último [workflow 36747828201](https://github.com/conradodeita/markina-gallery/actions/runs/36747828201) publicou `ce628f01d4aa9f7f9d7eb24bf347e30ae42579d3` mantendo schema 0069 e healthchecks públicos HTTP 200. |
| Topologia/impacto | Compose `markina-gallery`, nginx próprio em `127.0.0.1:8080`, API/web/bancos/Redis/Evolution em portas internas. A verificação posterior do PR #115 confirmou Evolution, Firefly, Nginx Proxy Manager e Portainer ativos. Nenhum recurso vizinho aparece como alvo do workflow. |
| Backup/reversão | O workflow do PR #115 registrou backup lógico exclusivo da Markina antes da publicação. Não há neste registro prova de ensaio de restauração nem correspondência desse backup com o instante da aplicação inicial da 0069. Após 0069, o binário anterior não é compatível com novas escritas sem proprietário; uma correção compatível é o caminho de recuperação, e restauração/downgrade exigem autorização separada. |
| Autorização | O proprietário autorizou merge e deploy em homologação na conversa e o procedimento de parada/retomada dos serviços próprios está registrado na [validação do ensaio posterior](../archive/2026-09-29-fix-homologation-service-resume/validation.md). Não há evidência suficiente neste repositório para afirmar que a primeira aplicação da 0069 e limpeza seguiram integralmente a janela, backup e ordem específicos de `release-runbook.md`; a task 6.2 continua aberta até essa reconciliação. |

## Entregue

Galerias de origem, galerias privadas e fotos passaram a guardar a conta proprietária do fotógrafo. O vínculo do administrador com essa conta é conferido pelo servidor. A mudança é uma proteção interna: não há botão novo para o fotógrafo. A instalação permanece limitada a **um fotógrafo ativo**; ainda não há isolamento comercial completo para admitir outro fotógrafo.

## Você pode testar

Em homologação, entrar como fotógrafo com senha e TOTP, criar uma galeria de teste, enviar um JPEG sintético, abrir uma prévia protegida e conferir a galeria como cliente por convite e OTP. Seleção/checkout dependem de uma galeria e cliente de teste autorizados. Não usar dados reais nem executar nova limpeza apenas para este roteiro. A mudança de domínio profissional continua fora desta etapa.

## Verificado

- Implementação: [CI 36586629460](https://github.com/conradodeita/markina-gallery/actions/runs/36586629460) aprovou 890 testes backend (19 skips condicionais), 352 frontend, lint, build, OpenSpec, varredura de segredos e política de deploy. Os ensaios PostgreSQL sintéticos cobriram migration, integridade e preservação; detalhes em [validation.md](validation.md).
- Publicação: [CI/deploy 36628097734](https://github.com/conradodeita/markina-gallery/actions/runs/36628097734) aprovou os cinco jobs. O log do deploy mostra escritores Markina interrompidos, backup lógico, schema 0069 sem nova migration nesse merge, serviços saudáveis e inventário sanitizado com uma conta/vínculo e sem cliente/foto.
- Operação posterior: o [ensaio de retomada documentado](../archive/2026-09-29-fix-homologation-service-resume/validation.md) confirmou serviços próprios e vizinhos ativos e quatro healthchecks HTTP 200. O [deploy pós-merge mais recente](https://github.com/conradodeita/markina-gallery/actions/runs/36747828201) também passou e conservou 0069.

## Pendente

- Reconciliar a autorização, a janela e o backup da **primeira aplicação remota de 0069**, pois o workflow do merge encontrou o schema já em 0069. Não usar o sucesso do deploy posterior como prova retroativa dessa sequência.
- Consolidar evidência reproduzível e vinculada a esta liberação para propriedade/contagens no banco, login/TOTP, OTP de cliente, galeria, upload, prévias, checkout e ausência de impacto nos vizinhos. Há verificações parciais e relatos de testes posteriores, mas o aceite integral da task 6.3 não está demonstrado neste registro.
- Submeter este resultado à revisão humana. Sincronização das três delta specs e arquivamento dependem da task 6.5; nenhuma habilitação de múltiplos fotógrafos decorre desta publicação.
