# Homologação e recuperação

## Inventário conhecido e escopo

Última inspeção somente leitura: `/opt/markina-gallery` no Oracle, revisão `fff7a742`, Alembic `20260920_0058`, 13 serviços Markina saudáveis. Subdomínio `https://markina-homolog.duckdns.org`, upstream próprio `127.0.0.1:8080`. Antes de publicar, atualizar este inventário e conferir se o servidor avançou.

Galeria 01 `cff9d256-bb0c-4158-89d2-3212f541fddd`: estado `deleting`, 2 pastas, 58 registros de foto, 1 galeria privada e 3 pedidos pendentes. Última operação falhou em `removing_records`, após confirmação de `preparing_history` e `removing_storage`, tentativa 2; início destrutivo em 20/09/2026 20:02:28 UTC. O erro sanitizado não permite atribuir uma causa específica de FK sem logs adicionais. Os testes reproduzem e cobrem dependências de fotos, interações, origens, mídia e notificações.

Recursos externos protegidos na inspeção anterior: firefly_bot `9335f5e9077e`, firefly_api `f06f36a5ed33`, firefly_frontend `6ea8a742b093`, firefly_db `768223c11835`, nginx-proxy-manager `66c25ca56d8c`, portainer `e49166611a66`. Não reiniciar, remover ou reconfigurar esses recursos. Não modificar redes, volumes, DNS, proxy, certificados ou portas de terceiros.

## Plano de impacto zero sobre outros projetos

1. CI do PR aprovado pelo usuário; verificar SHA, merge autorizado e execução do deploy de `develop`. Parar enquanto só houver CI pendente, conforme pedido do usuário.
2. Antes da ação operacional, apresentar inventário atualizado, subdomínio/porta acima e este plano. Confirmar autorização aplicável à publicação e ao alvo da exclusão. Backup do banco e inventário do storage conforme política de deploy; não adicionar dados ou segredos ao Git.
3. Publicar somente serviços do projeto `markina-gallery`, usando `docker compose -p markina-gallery -f docker/docker-compose.yml`. Migration 0059 é aditiva e não dispara exclusão nem retentativa automaticamente. Nenhum `prune` ou `down` global.
4. Validar SHA/migration/saúde/API e comparar os recursos externos antes/depois. Verificar login, histórico e confirmação de exclusão atualizada. Deploy pode reiniciar serviços Markina; impacto zero refere-se aos demais projetos.
5. Retomar a operação falha da Galeria 01 somente pelo fluxo administrativo autenticado e autorizado, após conferir inventário real. A retentativa recompõe o manifesto legado e refaz preparação textual idempotente. Não executar SQL manual de exclusão nem limpeza global de dados de teste.
6. Verificar operação concluída, ausência de galerias/pastas/fotos/prévias do escopo e preservação de nomes, valores, status, comunicações, notificações e movimentos. Conferir que outras galerias permanecem intactas. Se arquivos falharem, registrar pendência e validar retentativa; não declarar limpeza física completa.

## Rollback e aceite

Antes de existir histórico novo, downgrade 0059 é tecnicamente protegido pelo teste. Após registrar exclusões, indisponibilidade ou jobs, o downgrade recusa perda de dados; corrigir adiante com código compatível. Reverter código não restaura arquivos já excluídos. Qualquer restauração exige plano e autorização próprios.

Aceite real ainda pendente: Galeria 01; exclusão de pasta e foto; histórico de seleção sem compra, PIX aberto, comunicado e confirmado; cliente no celular/navegador; fotos compartilhadas de outra galeria preservadas. Só depois do aceite humano sincronizar specs principais e arquivar a change.

## Merge autorizado em 21/09/2026

PR #91 incorporado em develop às 11:10:34 UTC, merge `df1e14773f56a6ecd06066db5be7021a578e8c0e`, após todos os checks do head `e5d898d` passarem. O deploy no evento pull_request estava corretamente SKIPPED; somente push em develop o habilita após os checks dessa revisão.

Inventário somente leitura imediatamente antes do merge: checkout remoto limpo em `fff7a742`, migration 0058, 13 serviços Markina saudáveis. Subdomínio e upstream mantidos. IDs de todos os seis serviços de terceiros coincidem com os registrados acima. Inventário e plano de impacto zero apresentados ao proprietário; autorização de merge/deploy mantida na conversa.

Aguardar o novo CI de develop, sem polling, conforme solicitação do proprietário. Deploy e migration 0059 ainda não verificados. Não retomar automaticamente a exclusão da Galeria 01. Task 4.2 permanece pendente até publicação e verificação operacional.

## Deploy verificado em 21/09/2026

Execução `35592663503` concluída com sucesso, inclusive `deploy-homolog`, às 11:21:40 UTC. Verificação posterior somente leitura confirmou checkout remoto limpo no SHA `df1e14773f56a6ecd06066db5be7021a578e8c0e`, migration `20260921_0059`, 13 serviços Markina saudáveis e endpoints públicos `/api/health` e `/healthz` respondendo com sucesso. Os seis serviços de terceiros mantêm os mesmos IDs do inventário anterior.

Galeria 01 continua em `deleting`, com 58 fotos e 2 pastas; operação mais recente `failed`, tentativas 2. O deploy não reexecutou a exclusão, como projetado. Próximo passo de aceite: retentativa administrativa autenticada da operação existente e validação do histórico. Não foi executada operação destrutiva nesta verificação. Task 4.2 permanece pendente somente para a recuperação/aceite real; publicação técnica concluída.
