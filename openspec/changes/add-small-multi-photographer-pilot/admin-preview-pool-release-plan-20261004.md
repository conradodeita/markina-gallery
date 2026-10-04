# Publicação proposta — concorrência das prévias administrativas

## Status

Inventário preparado somente-leitura em 04/10/2026. Após apresentação deste escopo/impacto, o proprietário respondeu “autorizado” à criação da nova PR e publicação depois de informar CI verde. Autorizados commit seletivo, push e nova PR na branch existente; merge que dispara deploy permanece condicionado ao verde informado pelo proprietário, à base/inventário compatíveis e às verificações abaixo. Nenhum novo upload está liberado. Este plano integra a change atual, não cria funcionalidade ou encerra o piloto.

## Scope

### Validação final da fixture

Snapshot seletiva final sem as outras correções locais: 63 testes dirigidos aprovados, zero falhas/erros/skips, 280,355s no XML `pr136-fixture-final-63-20261004.xml` externo ao Git. Inclui 22 casos de prévias, as duas negativas legadas do CI vermelho e 39 casos de acervo/autoajuste. Ruff do escopo CI (app/tests) aprovado. Catálogo global inalterado após compilação PostgreSQL da cópia; SQLite real recusa as duas associações inválidas. Não há PostgreSQL local nem suíte integral final local; execução ampla intermediária obsoleta foi interrompida e preservada, incluindo um marcador de falha não classificado. CI integrado completo continua gate humano, sem polling. A atualização da PR não autoriza upload ou deploy antes do novo verde.

### Correção da fixture após backend vermelho da PR136

O proprietário informou a falha do backend da PR136/head `97dfd8b`. Dois testes legados de constraints SQLite falharam depois das novas fixtures PostgreSQL, embora os testes isolados e 1206 casos do CI tenham passado. A emissão PostgreSQL de `AddConstraint` altera os objetos Constraint do metadata compartilhado e omite essas FKs no SQLite posterior. A reprodução compilando DDL PostgreSQL e executando as duas negativas reais em SQLite privado produz duas falhas; compilar a partir de `MetaData` copiado preserva as duas negativas. Não é execução SQL PostgreSQL local nem prova de falha de produção.

A correção adicional é restrita ao próprio arquivo de testes da PR: fixture com cópia profunda privada do `MetaData` efetivo, mesmos bancos/queries/autenticação reais e guards de schema PostgreSQL descartável, mais duas regressões de ordem PostgreSQL→SQLite. `Table.to_metadata` recriou índices globais antigos dos flags Column além dos scoped; usar cópia exata em vez de remover constraints/índices. Não modificar dependências, aplicação, fixture comum, assertions ou servidor para esconder a falha. A aplicação continua contendo somente as duas remoções autorizadas. O CI anterior vermelho bloqueia merge/publicação: após push da correção, aguardar novo verde informado pelo proprietário, sem polling. A task 8.3i documenta a validação corretiva; a conclusão local da task 8.3h não é declaração de CI aprovado.

- Base publicada e `origin/develop`: `9b72f2b900ba04d9771130800991941a90650e40`, merge da PR #135. Consulta pontual ao GitHub e inventário remoto confirmaram a mesma revisão; não houve acompanhamento de CI.
- Aplicação: somente remover duas chamadas redundantes de `require_admin` em `admin_photo_preview` e `admin_watermarked_photo_preview`, em `backend/app/main.py`. O diff contra a base publicada contém apenas essas duas remoções.
- Regressões: `backend/tests/test_admin_preview_pool_concurrency.py`, 20 casos, com pool limitado, cookies/SQL reais, concorrência controlada, auditoria, retorno das conexões e negativas de acesso.
- OpenSpec: delta `specs/media-storage/protected-previews/spec.md`, este plano e somente os registros de proposal/design/tasks/validação correspondentes à task 8.3h e à publicação. Preparar índice seletivo e conferir a versão a publicar antes de qualquer commit autorizado.
- Excluir da release a correção local preexistente de inicialização do canal WhatsApp, seus testes, mudanças de texto/frontend, roadmap/cadastro autônomo e quaisquer outros hunks não necessários à correção do pool. Preservar integralmente esses arquivos no checkout; não usar reset, checkout destrutivo ou clean para obter uma árvore limpa.
- Não criar branch nova sem autorização específica. Proposta: reutilizar `feature/fix-capacity-monitor-layout`, abrir outra PR para `develop` e não reutilizar a PR #135 já integrada. Número da nova PR será conhecido somente após sua criação autorizada.
- Sem migration nova, dependência, configuração de pool, quota, recurso, topologia, segredo, nova busca facial ou limpeza de fotos. A mudança não autoriza publicação de outras correções locais.

## Evidence

Validações locais registradas em 03/10 e conferidas pelos relatórios XML em 04/10:

- Antes: duas regressões concorrentes falham com `QueuePool TimeoutError` na autenticação aninhada.
- Depois: 20 testes novos aprovados, zero skips; mais 39 regressões existentes de acervo/autoajuste aprovadas, zero skips. Total: 59. Ruff dirigido aprovado novamente em 04/10.
- Derivados próprios convencionais e autoajustados, autorização, isolamento, auditoria e headers privados preservados. Sem cache global de autorização ou aumento de conexões.
- Python 3.12, SQLAlchemy 2.0.52, FastAPI 0.141.1; banco SQLite privado. PostgreSQL sintético local e Docker estavam indisponíveis e não foram iniciados. Não atribuir a essas evidências validação PostgreSQL, capacidade remota, throughput ou a causa de todo evento histórico.
- Em 04/10, snapshot exclusiva do índice seletivo validada sem as correções locais excluídas: 59 testes aprovados/zero skips em 221,95s, Ruff completo backend aprovado e OpenSpec estrito completo com 76 itens aprovados/zero falhas. Import de `app.main` confirmado dentro da snapshot; blobs normalizados pelo Git correspondem ao índice e arquivos excluídos correspondem à base. Gitleaks portátil 8.24.3, SHA256 do arquivo comparado ao checksum publicado da release, analisou a snapshot sem detectar segredos. Apenas os três avisos de depreciação já existentes. Nenhum teste PostgreSQL local: porta 15470 continuou indisponível. PostgreSQL, suítes completas e gitleaks de histórico permanecem gates do CI da PR.

Artefatos privados fora do Git: `C:/codex-data/test-runs/admin-preview-pool-{before,after,integration}-20261003.{log,xml}`, lint correspondente e `admin-preview-pool-publication-{inventory,privacy,worker-readiness}-20261004.json`. Não incluir logs, dados locais, credenciais ou arquivos de teste gerados no commit.

Snapshot e evidências seletivas fora do Git: `C:/codex-data/test-runs/admin-preview-pool-release-snapshot-20261004`, `admin-preview-pool-release-snapshot-tests-20261004.{log,xml}`, `admin-preview-pool-release-snapshot-openspec-20261004.log` e `admin-preview-pool-release-snapshot-gitleaks-20261004.{log,json}`. A análise da snapshot não substitui a varredura do histórico do CI. A documentação final de evidências pode ser atualizada sem repetir os testes se os blobs do backend/testes permanecerem idênticos; repetir OpenSpec e conferir novamente o índice.

## Inventory

Inventário às 09:16 de 04/10/2026, America/Sao_Paulo, somente-leitura:

- Destino: Oracle `132.145.193.169`, checkout `/opt/markina-gallery`, projeto `markina-gallery`, Compose `docker/docker-compose.yml` e overlay existente de autoajuste.
- Homologação apenas: `https://markina-homolog.duckdns.org`; única entrada própria publicada `127.0.0.1:8080`. Sem novo domínio, porta, firewall ou certificado.
- Checkout remoto limpo; SHA acima; schema `20261001_0071`. `/healthz` e `/api/health` retornaram 200 nesta preparação.
- 13 serviços próprios ativos e healthy: api, web, worker, nginx, db, redis, evolution-api, evolution-db, evolution-redis, face-index-worker, face-search-worker, face-maintenance-worker e preview-adjustment-worker.
- Configuração existente verificada somente por resultados booleanos sanitizados: entradas obrigatórias únicas, chaves existentes válidas/distintas, origem pública e flag facial já correspondentes ao workflow, arquivo de ambiente com permissão 0600. Nenhum valor de segredo foi exposto ou alterado. Se qualquer condição divergir antes da publicação, interromper e pedir reconciliação; não gerar/rotacionar segredo implicitamente.
- Galerias privadas A/B/C seguem com 116/232/304 fotos, respectivamente; total 652, sem clientes vinculados, grants, acessos de clientes, convites individuais ou galerias derivadas. Uma pasta `JPEGs — carga` por conta, facial on, autoajuste custom habilitado, intensidade 50/exposição 0, sem pagamento. Runtime facial de index/search verificado em staging.
- O coletor v2 anterior encerrou naturalmente com 240 amostras/239 válidas. Seus alertas de degradação e falha de coleta continuam registrados e a admissão continua bloqueada. Recuperação atual não reabilita aquele ensaio.

## Deployment / Impact

O workflow existente dispara deploy em push/merge para `develop` somente após backend/frontend/OpenSpec/gitleaks. A PR isolada não faz deploy. Publicação futura SHALL ocorrer por esse fluxo, não por hot patch remoto ou alteração do workflow para contornar gates.

Embora o código corrigido seja apenas da API, `scripts/deploy-homolog.sh` executa a entrega do conjunto da aplicação: backup lógico exclusivo da Markina, build, preservação de branding, parada controlada dos escritores próprios, execução do Alembic existente, subida de api/web/worker e workers faciais/autoajuste ativos e recriação de nginx. Pode verificar/subir Evolution existente sem mudar seus recursos. Não apresentar isso como reinício apenas da API.

Não há revisão de banco nova nesta release: Alembic deverá continuar em `20261001_0071`. Interromper se a base, schema, diffs de migrations/configuração ou inventário mudarem. O deploy mantém arquivos, galerias, fotos, índices, originais locais, sessões/configurações e volumes próprios; não usar trailers `Homolog-Cleanup` no commit/merge. A manutenção automática posterior deverá ficar no modo inventário, nunca execute.

Impacto zero significa nenhuma alteração em recursos de terceiros. Firefly/Clearbudget, proxy compartilhado, Portainer, seus containers/imagens/redes/volumes e DNS/certificados/firewall ficam fora do alvo. O site Pick-your-Pic poderá ficar temporariamente indisponível durante parada/recriação; a janela não foi medida para esta release, portanto não prometer indisponibilidade zero nem duração exata. Nenhum upload pode estar em andamento na janela; conferir filas antes de prosseguir. Não aumentar quotas, reiniciar serviços vizinhos, usar prune ou compose down.

## Rollback

O script existente guarda SHA anterior e backup lógico. Se houver falha e a revisão de schema for comprovadamente inalterada, a reversão automática de código poderá retornar ao SHA anterior e reconstruir somente serviços da Markina. A versão anterior contém o defeito de pool: manter uploads suspensos após qualquer reversão. Não restaurar banco, apagar fotos, fazer downgrade ou ampliar ações automaticamente. Schema diferente/incerto bloqueia reversão automática e exige decisão humana própria.

## Human Gates / Next Steps

1. Autorização recebida em 04/10/2026 para commit seletivo, push e nova PR para `develop`, e publicação após CI verde informado pelo proprietário; não incluir as outras correções locais.
2. Snapshot seletiva validada em 04/10; conferir novamente o índice e base remota antes do commit. Registrar commit e anexar a PR ao chat após criá-la. Não incluir arquivos gerados/segredos ou outras correções locais.
3. O proprietário acompanha o CI e informa o resultado; não fazer polling de CI. Merge que dispara deploy exige autorização explícita deste inventário/impacto. Pode ser autorizado junto à etapa 1 de forma condicionada ao verde informado pelo proprietário.
4. Após publicação confirmada, verificar SHA/schema, saúde dos serviços próprios, headers/prévias com sessão administrativa autorizada e ausência de novos timeouts, sem afirmar resolução de todos os incidentes históricos.
5. Fazer novo preflight de acesso/configuração/fontes/filas, criar coletor independente com evidência nova e alertas antigos preservados, verificar coleta saudável e só então liberar os mesmos 50 JPEGs por A/B/C, nas pastas existentes. Não reabrir o coletor v2 ou relaxar critérios de parada.
6. Quando explicitamente liberado, o proprietário inicia os três uploads manuais e avisa `iniciei`; acompanhar processamento/métricas durante o turno ativo. Totais previstos A166/B282/C354 são projeções, não resultados atuais. Não liberar 1000/2124, cleanup, produção, mensagens, buscas ou revisão final por esta aprovação.

Tasks 8.3h e 8.3i concluídas somente no escopo local validado. 8.3f permanece parcial/bloqueada; 8.3, 8.3a e 8.4 continuam pendentes. Progresso 36/40 refere-se à árvore local completa, que preserva registros do piloto não incluídos nesta PR seletiva; snapshot reduzida 28/31. Atualização da PR não significa CI verde ou publicação. Sem sync/archive ou conclusão do piloto.
