# Preparação de produção — 2026-10-15

## Estado atual

- Candidata: PR #192, SHA `9891afb06f74722fd3aaabcd50b09fa4905164b1`; CI GitHub #38815751058 passou. O SHA ainda não está integrado à `main`.
- O environment GitHub `production` foi criado e verificado: revisor obrigatório `conradodeita`, branch permitida somente `main`, bypass administrativo desativado. A lista de secrets desse environment está vazia; nenhum valor de segredo foi lido ou alterado.
- O inventário remoto somente de leitura não foi obtido. `clearbudget-vnic` não resolveu no cliente SSH e `ubuntu@132.145.193.169` recusou a autenticação por chave pública; o script de inventário não chegou a iniciar.
- Portanto, este documento é um plano preliminar baseado em registros versionados, não é aprovação nem inventário atual. Nenhuma mutação ou deploy foi executado.

## Última referência versionada

`docs/RELEASE-PAYMENT-STATUS-API-WEB.md` registra como referência (reconfirmar imediatamente antes de qualquer execução):

| Item | Registro versionado |
| --- | --- |
| Host/checkout | `ubuntu@132.145.193.169` / `/opt/markina-gallery` |
| Projeto Compose | `markina-gallery`, `docker/docker-compose.yml` |
| Domínio | `https://markina.pickyourpic.com.br` |
| Entrada do projeto | `127.0.0.1:8080`; web `:3000` e API `:8000` internos |
| SHA de checkout registrado | `71be3b29659143293351968e15fb4886c2d72bf0` |
| Serviços faciais no Compose | `face-search-worker`, `face-index-worker`, `face-maintenance-worker`; profile `facial`, sem portas |

O registro de API/web e seus IDs/hash de imagem é anterior à consulta atual e não comprova o estado presente. O estado da flag facial, workers ativos, healthchecks, IDs de containers/imagens, revisão Alembic, configuração resolvida, capacidade livre, espaço de backup e ocupação de recursos compartilhados permanecem desconhecidos até inventário SSH atualizado.

## Escopo e impacto esperado

A change altera o frontend da câmera, a API/provedor de referência facial e o worker de busca. O conjunto candidato é `web`, `api` e `face-search-worker`, sujeito à confirmação pelo inventário atual. Não há migration de banco nem reindexação. O plano não inclui `db`, `redis`, `migrate`, proxy compartilhado, DNS, firewall, certificados, redes, volumes ou qualquer recurso de outro projeto.

Mesmo limitado ao projeto `markina-gallery`, recriar API/web pode causar breve indisponibilidade e reiniciar o worker pode atrasar jobs de busca. Não prometer zero downtime. Se CPU, memória ou disco compartilhados não comportarem a construção, a operação deve parar antes de substituir containers saudáveis.

## Plano preliminar de execução e reversão

1. Depois de provisionar acesso SSH de inventário e resolver os gates faciais, atualizar este inventário no host imediatamente antes da execução: SHA `main` integral, árvore remota, migrations, containers/healthchecks, imagens reais, configuração efetiva comparada em memória, domínio/bindings, capacidade, backup disponível e isolamento dos recursos Markina. Não imprimir nem persistir configurações com segredos.
2. Apresentar inventário, impacto, possível interrupção e SHA alvo ao proprietário e obter aprovação explícita para essa execução. A aprovação do environment GitHub, por si só, não substitui a aprovação do plano específico.
3. Construir as imagens do SHA aprovado antes de substituir containers; usar exclusivamente `docker compose -p markina-gallery -f docker/docker-compose.yml` e apenas os serviços confirmados como necessários. Preservar IDs/imagens anteriores e parar se configuração, SHA, serviços ou recursos divergirem.
4. Substituir somente os serviços aprovados, validar saúde interna e HTTPS de `/healthz`, `/api/health` e `/`. O worker pode atrasar jobs durante a troca; não expor imagens, embeddings, scores ou PII nos logs.
5. Se a saúde falhar, interromper o rollout, apresentar diagnóstico e novo plano de recuperação. Restaurar somente as imagens Markina previamente registradas após aprovação explícita; nunca restaurar banco automaticamente nem tocar recursos compartilhados.

## Gates que impedem a execução

1. Configurar secrets de SSH dentro do environment `production`, com nomes definidos pelo workflow/runbook que vier a ser revisado. Não enviar valores pelo chat.
2. Obter acesso suficiente para o inventário somente de leitura acima.
3. Revalidar os gates da change `productionize-facial-search`: base legal, calibração/equidade com corpus autorizado, capacidade ARM, recuperação e o gate próprio de representação/consentimento para fluxo infantil. O registro versionado em `docs/PRODUCAO-FACIAL-INVENTARIO-E-PLANO.md` os mantém pendentes ou bloqueados; esta change não os satisfaz.
4. Implementar e validar workflow e preflight multi-serviço fail-closed sem permitir que environment ausente, secret ausente, inventário divergente ou aprovação ausente cause mutação.

Até esses gates serem resolvidos e o inventário ser aprovado, não iniciar deploy nem habilitar a busca facial em produção.
