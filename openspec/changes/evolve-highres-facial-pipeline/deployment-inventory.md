# Paridade local/homologação — inventário de 20/09/2026

## Pedido e autorização

Após a validação local, o proprietário pediu validar fotos reais diretamente em homologação e levar ao servidor o mesmo sistema local. Preparação da publicação e inventário somente leitura realizados nesta execução. A spec de deployment exige apresentação deste plano e aprovação explícita antes de alterar o ambiente. O ambiente GitHub `homolog` também possui `required_reviewers`; não aprovar em nome do proprietário nem contornar o workflow por SSH.

A preferência de continuidade registrada nas changes anteriores permanece: depois de push/início do Actions, aguardar o proprietário conferir verde/vermelho, sem polling ou automação. O pedido de paridade não foi interpretado como revogação dessa preferência.

## Inventário verificado por SSH

- Destino: `https://markina-homolog.duckdns.org`, checkout `/opt/markina-gallery`.
- SHA remoto e `last-healthy.sha`: `9b83f062e21ea613537c1b931bd885cf5241972f`; checkout limpo.
- O conteúdo desse merge é idêntico ao HEAD local anterior às alterações high-res. Portanto a entrega incremental é a change high-res; não é necessário republicar/reimplementar as funcionalidades anteriores.
- Migration operacional: `20260914_0056 (head)`.
- Arquitetura `aarch64`, 4 CPUs; RAM total 23.988 MiB, disponível 19.757 MiB; disco 194 GB, 125 GB livres, 36% utilizado. Load 0,46/0,19/0,12 no inventário.
- 13 serviços Markina saudáveis: nginx, web, API, worker, PostgreSQL, Redis, três Evolution, três faciais e preview-adjustment-worker.
- Entrada única do projeto `127.0.0.1:8080`; PostgreSQL/Redis/Evolution/web/API internos. Proxy compartilhado mantém HTTPS existente. Nenhuma porta/subdomínio nova.
- Facial habilitado (`FACIAL_PROCESSING_ENABLED=true`); high-res ainda ausente. Concorrência facial 1. Índice: 1 CPU/768 MiB; busca: 0,75 CPU/512 MiB; manutenção: 0,25 CPU/256 MiB; ajuste: 0,5 CPU/768 MiB.
- Push já habilitado em API/worker e WhatsApp transacional desabilitado: preservar o estado real atual, que difere de registros históricos. Não enviar notificações de teste nem alterar esses gates.
- Volumes duráveis de mídia/fonte/histórico/referências/branding/banco presentes. Índice antigo ainda não monta a fonte; Compose candidato adiciona somente leitura ao volume existente.

## Terceiros para comparação posterior

| Serviço | ID atual |
|---|---|
| firefly_bot | 9335f5e9077e |
| firefly_api | f06f36a5ed33 |
| firefly_frontend | 6ea8a742b093 |
| firefly_db | 768223c11835 |
| nginx-proxy-manager | 66c25ca56d8c |
| portainer | e49166611a66 |

Preservar containers, imagens, redes, volumes, proxy, certificados, DNS e firewall de terceiros. IDs próprios pré-operação: nginx b765eb6db552, API 7acf0b0d81d3, web 4434c0408316, worker dc13c2bb4786, índice ec705dff40c2, busca 190dc99c9b8a, manutenção f904ace15887, ajuste 180e77cdf9f4, db 56caed105a12, redis ebfa19d492e5, Evolution c0db1647bc23/de2ca0cf5a16/3112575298ff.

## Plano concreto de publicação

1. Commit/PR exclusivos da change para `develop`, preservando as continuidades locais de outras changes e `.codex-tmp`. Publicar o código local testado, não uma cópia parcial por SSH. Registrar SHA do candidato no PR.
2. CI obrigatório: backend/frontend/build/OpenSpec/gitleaks. Aguardar conferência do proprietário conforme preferência registrada. Merge somente do head revisado e CI verde.
3. Após aprovação deste plano e do ambiente GitHub, script `deploy-homolog.sh` existente cria backup lógico exclusivo, preserva branding, constrói imagens, aplica a migration aditiva 0057 e atualiza API/web/workers geral/faciais/ajuste da mesma versão. Manter overlays de branding e preview-adjustment ativos.
4. Não limpar dados, reindexar legado, executar manutenção destrutiva, restore, downgrade, prune ou `compose down`. A migration preserva fotos e ciphertext legados; não cria bbox fictícia. Os novos arquivos não entram em análise apenas por implantação.
5. Publicação do código conserva `FACIAL_HIGHRES_ENABLED=false` como default. Para testar o fluxo novo, a aprovação deve incluir explicitamente persistir **somente** `FACIAL_HIGHRES_ENABLED=true` na configuração de homologação e recriar os serviços próprios que a consomem. Não mudar segredos, chaves, thresholds, flags de canais ou limites CPU/RAM. A configuração do ambiente é necessariamente distinta do default seguro local; código, schema e modelos devem ser os mesmos.
6. Conferir SHA/arquivos executados, revisão 0057, flags permitidas, mount da fonte somente leitura no índice, health de todos os serviços, `/healthz` e `/api/health`. Comparar os IDs de terceiros. Registrar versões dos runtimes/modelos: mesma revisão de código não significa mesmas versões instaladas no Windows e no Linux ARM.
7. Validar primeiro um pequeno lote enviado pelo fotógrafo, documentando origem/finalidade e autorização já recebida. Medir memória/CPU/latência/fila durante o lote antes de ajustar recursos. Não alegar recall melhor sem ground truth; não iniciar benchmark massivo nem acessar fotos arbitrárias do servidor.

## Impacto e retorno

Impacto zero significa preservar terceiros. A aplicação Markina pode ter breve indisponibilidade durante preservação/recriação da API; não prometer zero downtime. Build acontece antes dessa janela conforme script atual. Limites de recursos permanecem; fotos difíceis podem atingir o teto do worker, motivo para começar com lote pequeno e medir.

Depois de 0057, rollback preferencial é desligar novas admissões high-res e manter o código com suporte ao lifecycle já criado. Não voltar automaticamente ao binário 0056 depois de fontes apagadas. Guard de schema do deploy preserva o banco e exige revisão em falha de migration. Não executar restore/downgrade sem autorização própria. Nenhuma ação remota de escrita foi realizada na preparação.
