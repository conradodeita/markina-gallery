# Inventário e plano de implantação restrita — 14/10/2026

## Estado observado

- Host Oracle `132.145.193.169`; checkout `/opt/markina-gallery`, projeto Compose `markina-gallery`, arquivo principal `docker/docker-compose.yml`.
- Domínio real `https://markina.pickyourpic.com.br`. Nginx Markina mantém `127.0.0.1:8080 -> 80`; web 3000, API 8000, PostgreSQL/Redis internos. Proxy compartilhado usa 80/81/443; outros projetos incluem Firefly/ClearBudget e Portainer.
- Serão substituídos somente os containers `markina-gallery-face-search-worker-1` e `markina-gallery-web-1`. O worker não publica portas e mantém 512 MiB/0,75 CPU. O frontend expõe somente a porta interna 3000, acessada pelo Nginx Markina; a publicação `127.0.0.1:8080 -> 80` permanece inalterada.
- Imagem anterior `sha256:dec0ba442b75e61f01a048ed2f0811ff0ebb5011d954de251aa4f0688b96eaf2`, tag `markina-gallery-face-search-worker:latest`.
- Compose efetivo inclui overlays de branding, RAW, preview-adjustment e system-monitor. Reutilizar exatamente essa lista, arquivo externo existente `docker/.env.homolog`, profiles e project name; comparar configuração do serviço antes da troca sem imprimir valores sensíveis.
- Contagens atuais: 1 owner, 1 galeria, 3 pastas, 2.693 ativos, 1 cliente, 10.531 embeddings; 0 pedidos, 0 itens de pedido, 0 grupos de pagamento, 0 consultas pendentes. São dados reais; não classificá-los como descartáveis pelo nome homolog.
- Backup anterior observado: `predeploy-20261013T233909Z-3b15529c4bd5.dump` e manifesto, armazenados somente no servidor. Não é prova de backup dos uploads posteriores nem autorização para restaurar banco.

## Plano de impacto zero nos dados e demais serviços

1. Receber aprovação explícita do proprietário para esta implantação restrita.
2. Repetir preflight de SHA/código, imagem, saúde, configuração e pendências. Se o servidor mudou de base, interromper a troca para reconciliar.
3. Preparar contexto temporário da revisão aprovada e buildar a imagem do frontend pelo `frontend/Dockerfile`, sem tocar no checkout ou no frontend em execução.
4. Criar imagem do worker derivada da imagem anterior já instalada, copiando exclusivamente `app/facial/engine.py` e `app/facial/search_worker.py`. Não baixar modelos, instalar dependências, aplicar migration ou usar o deploy geral/manutenção.
5. Guardar tags anteriores e fonte/checksums em diretório técnico exclusivo. A imagem do worker é uma camada COPY sem alteração da imagem base; registrar a imagem anterior do frontend para rollback.
6. Validar build/healthcheck da imagem do frontend e importação offline da imagem facial com containers efêmeros. Não anexar rede, volumes de dados nem segredo à validação offline. Comparar environment/mounts/limites/comando/rede dos serviços efetivos sem imprimir valores sensíveis.
7. Usar overlay exclusivo para substituir somente as imagens de `web` e `face-search-worker`. Reaproveitar a lista exata de Compose/overlays, `--env-file docker/.env.homolog`, profiles e `-p markina-gallery`; executar `up -d --no-deps --no-build web face-search-worker`. Preservar configuração externa, modelos, chaves, volumes e filas.
8. Conferir ambos os containers saudáveis e estáveis, imagens/checksums, ausência de reinícios/erro de lease, contagens protegidas e saúde/IDs dos serviços não alvo.
9. Na sessão cliente já aberta, iniciar busca por região da galeria autorizada e observar contagem de fotos comparadas, percentual, resultado terminal e duração. Não criar pedido/seleção, reindexar acervo ou ampliar acesso. Notificações decorrentes do fluxo existente continuam conforme configuração e preferência do cliente; nenhum envio avulso será executado.

## Impacto esperado e rollback

Busca e interface podem pausar por alguns segundos durante a troca. API, Nginx, indexação concluída, OTP, compras e arquivos permanecem nos serviços/volumes existentes. Consultas em voo seguem a recuperação normal de lease; não editar o banco para retomá-las.

Rollback troca somente as imagens do overlay pelas tags anteriores e recria `web` e `face-search-worker` com os mesmos arquivos Compose e `--no-deps --no-build`. Não restaurar banco, fazer down, prune, purge ou limpeza de homologação. Rollback técnico depende de nova indicação humana se o hotfix causar regressão; registrar a autorização e as evidências.

O hotfix deve ser integrado à fonte versionada antes de um deploy geral futuro, que pode substituir a imagem derivada. Não executar reset/maintenance para publicar a correção.
