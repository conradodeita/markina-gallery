# Inventário e plano de implantação restrita — 14/10/2026

## Estado observado

- Host Oracle `132.145.193.169`; checkout `/opt/markina-gallery`, projeto Compose `markina-gallery`, arquivo principal `docker/docker-compose.yml`.
- Domínio real `https://markina.pickyourpic.com.br`. Nginx Markina mantém `127.0.0.1:8080 -> 80`; web 3000, API 8000, PostgreSQL/Redis internos. Proxy compartilhado usa 80/81/443; outros projetos incluem Firefly/ClearBudget e Portainer.
- Somente o container `markina-gallery-face-search-worker-1` será substituído. Sem portas publicadas; limites vigentes 512 MiB/0,75 CPU.
- Imagem anterior `sha256:dec0ba442b75e61f01a048ed2f0811ff0ebb5011d954de251aa4f0688b96eaf2`, tag `markina-gallery-face-search-worker:latest`.
- Compose efetivo inclui overlays de branding, RAW, preview-adjustment e system-monitor. Reutilizar exatamente essa lista, arquivo externo existente `docker/.env.homolog`, profiles e project name; comparar configuração do serviço antes da troca sem imprimir valores sensíveis.
- Contagens atuais: 1 owner, 1 galeria, 3 pastas, 2.693 ativos, 1 cliente, 10.531 embeddings; 0 pedidos, 0 itens de pedido, 0 grupos de pagamento, 0 consultas pendentes. São dados reais; não classificá-los como descartáveis pelo nome homolog.
- Backup anterior observado: `predeploy-20261013T233909Z-3b15529c4bd5.dump` e manifesto, armazenados somente no servidor. Não é prova de backup dos uploads posteriores nem autorização para restaurar banco.

## Plano de impacto zero nos dados e demais serviços

1. Receber aprovação explícita do proprietário para esta implantação restrita.
2. Repetir preflight de SHA/código, imagem, saúde, configuração e pendências. Se o servidor mudou de base, interromper a troca para reconciliar.
3. Criar imagem derivada da imagem anterior já instalada, copiando exclusivamente `app/facial/engine.py` e `app/facial/search_worker.py`. Não baixar modelos, instalar dependências, aplicar migration ou usar o deploy geral/manutenção.
4. Guardar tag da imagem anterior e fonte/checksums do hotfix em diretório técnico exclusivo. Build de camada COPY, sem alteração da imagem original.
5. Validar importação offline da imagem nova com container efêmero, sem rede, fontes/referências ou volumes de banco. Comparar ambiente/mounts/limites/cmd/rede do serviço, sem expor segredos.
6. Usar overlay exclusivo que troca somente a imagem do face-search-worker; `docker compose --env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml [overlays existentes] -f <overlay-hotfix> --profile facial up -d --no-deps --no-build face-search-worker`. Preservar configuração externa, modelos, chaves, volumes e filas.
7. Conferir container saudável, imagem/checksums, ausência de reinícios/erro de lease, contagens protegidas e saúde dos serviços preexistentes.
8. Na sessão cliente já aberta, iniciar busca por região da galeria autorizada e observar contadores reais, resultado terminal e duração. Não criar pedido/seleção, reindexar acervo ou ampliar acesso. Notificações decorrentes do fluxo existente continuam conforme configuração e preferência do cliente; nenhum envio avulso será executado.

## Impacto esperado e rollback

Somente processamento de busca pode pausar por alguns segundos durante a troca. Navegação, indexação concluída, OTP, compras e arquivos permanecem nos serviços/volumes existentes. Consultas em voo seguem a recuperação normal de lease; não editar o banco para retomá-las.

Rollback troca somente o overlay de imagem pela tag anterior e recria somente face-search-worker com os mesmos arquivos Compose e `--no-deps --no-build`. Não restaurar banco, fazer down, prune, purge ou limpeza de homologação. Rollback técnico depende de nova indicação humana se o hotfix causar regressão; registrar a autorização e as evidências.

O hotfix deve ser integrado à fonte versionada antes de um deploy geral futuro, que pode substituir a imagem derivada. Não executar reset/maintenance para publicar a correção.
