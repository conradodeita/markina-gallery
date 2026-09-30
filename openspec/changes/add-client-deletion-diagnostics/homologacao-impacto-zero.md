# Homologação e impacto zero

## Inventário de referência

- Último deploy saudável verificado: run `36660152673`, SHA `abd4d21f8fec1efd0f18eb0a8eebe4c0f2444293`, concluído em 2026-09-30 02:43 UTC. O job `deploy-homolog` terminou com sucesso.
- O inventário sanitizado daquele deploy registrou 13 containers Markina saudáveis, incluindo Evolution API, banco e Redis conectados. O banco permaneceu em `20260929_0069 (head)`; esta change não adiciona migration.
- Endereço público atual: `https://markina-homolog.duckdns.org/`.
- Porta publicada no host: somente Nginx em `127.0.0.1:8080`; banco e Redis não publicam portas.
- Verificação somente leitura em 2026-09-30 03:25 UTC: `/healthz` e `/api/health` responderam HTTP 200.

## Plano de impacto zero

1. Integrar somente após CI aprovado; o job `deploy-homolog` exige aprovação do Environment `homolog`.
2. O deploy usa exclusivamente `-p markina-gallery -f docker/docker-compose.yml`; cria backup lógico dedicado da Markina antes da atualização e executa as migrations já versionadas, sem migration nova nesta change.
3. Reconstruir/recriar apenas os serviços Markina selecionados pelo script de deploy e conferir o inventário rotulado por projeto. Evolution API, banco e Redis permanecem no projeto existente; a operação não altera DNS, firewall, proxy global, certificados, nem recursos de outros projetos. Não executar `down` ou prune.
4. Confirmar o SHA publicado, estado saudável dos serviços e HTTP 200 em `http://127.0.0.1:8080/healthz`, `http://127.0.0.1:8080/api/health` e nas duas rotas públicas do domínio acima.
5. Se smoke test falhar, seguir o rollback do script para o SHA saudável anterior, mantendo o backup lógico e registrando os resultados antes de qualquer tentativa adicional.

## Verificação específica desta change

Os testes locais verificam erro sintético antes do commit (HTTP 500, `request_id`, resultado `not_committed` e corpo/log sem SQL ou PII) e falha auxiliar depois do commit (HTTP 200, recibo concluído e referência de reconciliação). A interface também cobre resposta HTTP 502 não JSON sem renderizar o HTML do proxy e sem repetir automaticamente a mutação.

Uma falha inesperada injetada diretamente no processo de homologação não faz parte do smoke test: não há chave ou mecanismo de falha sintética habilitado no produto. A publicação verificará saúde e SHA; a validação do contrato de falha permanece coberta pelos testes isolados e pelo CI.

## Resultado pós-publicação

- Em 2026-09-30, o CI pós-merge run `36700111541` concluiu com sucesso para o SHA `9b3793aa42d208aa4107288ed11261eb2c1c39d0`; o job `deploy-homolog` terminou com sucesso.
- Verificação somente leitura após o deploy: `/healthz` e `/api/health` no domínio público responderam HTTP 200. O inventário sanitizado do deploy mostrou os serviços Markina saudáveis, inclusive API, banco, Evolution API e seus serviços de suporte.
- O inventário sanitizado do deploy ainda registrou um cadastro de cliente de teste e estado operacional residual; portanto, não considerar a limpeza concluída.
- Na primeira sessão autenticada, `/admin/clients` respondeu “Acesso negado”. Após novo login, a consulta carregou o inventário sanitizado de um cadastro elegível sem histórico comercial protegido: 1 cadastro, 1 telefone, 1 estado operacional, 1 notificação, 1 sessão e 2 entregas OTP; a interface indicou que galerias e fotos seriam preservadas.
- Após confirmação explícita no momento da ação, uma tentativa de exclusão retornou HTTP 500. A UI mostrou “A exclusão não foi concluída”, a referência de diagnóstico `b782fca7-9ae2-4f3d-9bf9-5294a02cf052` e orientou recarregar a lista antes de tentar novamente. A lista foi recarregada e continuou mostrando o cadastro; nenhuma segunda tentativa foi feita naquela versão.
- A causa do HTTP 500 foi identificada no código: o evento de auditoria serializava 646 caracteres em `AuditEvent.subject`, cuja coluna PostgreSQL aceita até 320. O recibo durável já contém cliente, ator, resultado, fingerprint e contagens completas; o evento agora guarda apenas `client_deletion_receipt:<UUID>`.
- A regressão sintética combina telefone, estado em tombstone, notificação, sessão e duas entregas OTP, confirma preservação do tombstone e do recibo completo, e limita o evento ao tamanho permitido. O módulo passou com 21 testes locais; a etapa dedicada em PostgreSQL passou no PR #122 e no CI pós-merge.
- Em 2026-09-30, o run pós-merge `36707965516` publicou com sucesso o SHA `049eb5cc83c158bdaafa88a4b88bd8a4a4bdeebf` em homologação; `/healthz` e `/api/health` responderam HTTP 200. Após recarga da interface, o cadastro de teste ainda constava sem histórico comercial protegido. Novo inventário autenticado repetiu 1 cadastro, 1 telefone, 1 estado individual de galeria pública, 1 notificação, 1 sessão e 2 entregas OTP; a interface informou que galerias e fotos seriam preservadas. A exclusão definitiva aguardava confirmação no momento da ação.

## Confirmação da limpeza específica

- Após a confirmação, o proprietário realizou a exclusão pela interface. A página apresentou “Cadastro e estado operacional excluídos” e, após recarga, a lista de clientes permaneceu vazia. O executor não enviou outra requisição de exclusão.
- Com autorização específica para inspeção do banco, a consulta ao PostgreSQL `markina_gallery_homolog` foi executada por `docker compose --env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml exec -T db` em transação `READ ONLY`, encerrada com `ROLLBACK`. Nenhum dado ou serviço foi alterado por essa inspeção.
- O recibo mais recente tinha status `completed` às 11:47:13 UTC em 2026-09-30 e registrava remoção de 1 cliente, 1 telefone, 1 estado individual de galeria pública, 1 notificação, 1 sessão, 2 entregas OTP e 2 tentativas de entrega. A consulta direta encontrou 0 clientes no banco; para o UUID alvo do recibo, 0 registros em `client_phone`, `gallery_client_state`, `gallery_membership_notification_outbox` e `auth_session` de cliente. Para o telefone do teste, encontrou 0 linhas em `client`, `client_phone`, `whatsapp_delivery` OTP e `auth_challenge` OTP.
- O evento `client.deleted_without_history` apareceu uma vez para o recibo, com `subject` de 60 caracteres. Um tombstone de galeria permaneceu em `parent_gallery`; `photo_asset` tinha 0 registros no momento da inspeção, portanto não há comparação de fotos antes/depois. O banco continha 1 administrador, e `api`, `db`, `evolution-api`, `evolution-db` e `evolution-redis` estavam `healthy`.
