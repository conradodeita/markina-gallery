# Preparação operacional — não executada

## Destino e inventário

Destino previsto: homologação privada `https://markina-homolog.duckdns.org`, checkout `/opt/markina-gallery`, projeto Compose `markina-gallery`, arquivo `docker/docker-compose.yml`. O inventário de `../evolve-highres-facial-pipeline/deployment-inventory.md` registrou entrada `127.0.0.1:8080` e serviços internos; essa informação é histórica e exige conferência somente leitura antes de operar. Nenhuma porta, rede, subdomínio ou volume novo é necessário nesta change.

Código afetado: frontend, API, workers que leem consultas e notificações; migration aditiva `20260921_0060` após `20260921_0059`. Banco, mídia, branding, índices e recibos existentes devem ser preservados. A disponibilidade infantil passa a seguir os gates de serviço/galeria já existentes; quando disponíveis, consentimento explícito do responsável basta para nova consulta, sem cadastro de representação. Não editar flags ou segredos para contornar um gate indisponível.

## Plano de impacto zero em terceiros

1. Push da branch da change e PR para `develop`; parar conforme instrução humana e aguardar confirmação do CI verde. PR não dispara deploy. Não fazer merge nesta execução.
2. Antes de publicação autorizada, conferir SHA, Alembic head, health, serviços/portas do projeto, armazenamento e IDs dos containers de terceiros. Apresentar o inventário atualizado; preservar proxy, DNS, certificados, firewall, redes e volumes compartilhados.
3. Usar o workflow existente e sua aprovação humana de ambiente, preservando backup lógico e branding. Preparar imagens antes da troca. Coordenar API/frontend/workers na mesma revisão: nenhum worker antigo pode consumir novas consultas sem consentimento. A janela pode interromper brevemente o próprio Markina; não prometer zero downtime.
4. Aplicar migration 0060 e atualizar serviços próprios coordenadamente antes de aceitar novas consultas diretas. Não limpar/reindexar dados, não executar `compose down`, prune ou manutenção destrutiva. Conferir serviços e IDs de terceiros após a operação.
5. Validar autenticação/vínculo, disponibilidade infantil sem representação, checkbox único, admissão com aceite explícito, toque direto sem aceite e retorno ao topo, cancelamento e isolamento entre clientes. Teste com dados reais somente no escopo/lote cuja origem, finalidade e autorização de execução forem documentadas.
6. Registrar SHA implantado, revisão do schema e evidência sanitizada. Sem dados pessoais, fotos, vetores ou segredos nos artefatos.

## Retorno e bloqueios atuais

Após novas consultas, downgrade 0060 recusa apagar/reinterpretar autorizações. Preservar schema e lifecycle; corrigir adiante ou suspender novas admissões mediante autorização, sem restaurar binários incompatíveis. Não executar restore/downgrade operacional automaticamente.

Preparação concluída; inventário remoto atualizado, implantação e validação autenticada permanecem pendentes. A parada após **push + PR** é solicitação expressa do proprietário, não falta de autorização da decisão infantil. Nenhuma escrita remota, mudança de configuração ou migração operacional foi feita nesta execução.
