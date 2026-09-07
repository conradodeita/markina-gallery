# Inventário e roteiro de homologação privada controlada

## Inventário zero-impact proposto

- Projeto Compose: `markina-gallery`, arquivo `docker/docker-compose.yml`.
- Subdomínio conhecido: `markina-homolog.duckdns.org` por meio do proxy/rede externa `npm-network` já existente.
- Única porta publicada pelo projeto: Nginx `${MARKINA_GALLERY_PORT:-8080}:80`.
- Serviços atuais preservados: `nginx`, `web`, `api`, `worker`, `migrate`, `db`, `redis`; Evolution permanece em profile próprio.
- Novo serviço: `face-worker`, profile `facial`, sem porta, até 1 CPU e 768 MiB, volume de derivados somente leitura e volume exclusivo de referências.
- Migrations faciais: revisions `0043` e `0045`, aditivas; `0045` apenas amplia notificações administrativas. Nenhuma migration liga a flag ou processa fotos.
- Estado inicial obrigatório em uma instalação nova: `FACIAL_PROCESSING_ENABLED=false` e profile facial não iniciado.

Nenhum container, rede, volume, proxy, firewall, DNS, certificado ou secret de terceiro será alterado. Este inventário não autoriza execução.

## Roteiro após autorização específica

1. registrar SHA de `develop`, SHA atualmente publicado, run anterior, head Alembic, containers, networks, mounts e portas;
2. confirmar backup/restauração e espaço disponível sem exibir credenciais;
3. executar build e migration autorizados com flag desligada;
4. validar `/healthz` e `/api/health`, login do fotógrafo, login OTP e seleção manual antes de tocar no filtro;
5. confirmar migration no head e ausência do `face-worker`/portas novas no profile padrão;
6. com autorização operacional separada e registro do lote, habilitar a configuração privada de homologação e iniciar o profile `facial`, verificando healthcheck/uso ocioso;
7. criar uma Galeria pública de teste autenticada, com 500–1.000 JPEGs sintéticos ou reais de adultos e menores enviados pelo administrador/fotógrafo, e confirmar que a política interna e o backfill nascem automaticamente uma única vez;
8. observar prévias simultâneas, fila, prontas/total, CPU, RSS, disco, backpressure, carga/descarga do modelo e ausência de impacto no worker de mídia;
9. executar consentimento, `ready|no_face|multiple_faces|low_quality|no_candidates|failed`, fechamento/retomada, seleção, cotação, cancelamento, expiração e revogação;
10. confirmar via prova de limpeza que referências, candidatas, outbox pendente e embeddings foram eliminados, enquanto fotos, privada, seleções e histórico permaneceram;
11. revisar UI móvel/desktop e acessibilidade com imagens pertencentes ao lote autorizado;
12. desligar a flag/profile por operação controlada e registrar resultados, métricas e rollback.

O ensaio do item 8 usa `scripts/benchmark-homolog-facial.py`: primeiro `snapshot`, depois `monitor` iniciado antes do upload e limitado ao SHA publicado. O observador exige `BENCHMARK_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG` e confere identificador do lote, referência da autorização, quantidade esperada e declaração sobre menores contra o gate ativo. O modo monitor aceita 30–14.400 segundos e registra JSONL agregado para um arquivo temporário fora do Git. A execução SHALL ser interrompida se a quantidade divergir do lote autorizado ou se faltarem origem documentada, finalidade, responsável, retenção ou autorização humana explícita. O relatório final consolida tempo ativo e throughput facial, estados das filas de mídia/facial, derivados, rostos agregados, picos de CPU/memória/PIDs, delta de disco e health dos serviços, sem identificador de pessoa, título, nome de arquivo, telefone, imagem, embedding ou score.

Falha de healthcheck, isolamento, retenção, backpressure, regressão de mídia/seleção manual ou recurso acima do limite interrompe apenas o piloto facial e aciona rollback. Nenhum dado fora do lote registrado e autorizado poderá ser introduzido.

## Ativação privada auditável

O script `scripts/manage-homolog-facial.sh` oferece inventário, ativação, reconciliação e fechamento somente no checkout fixo `/opt/markina-gallery`, exige SHA integral, repositório esperado e host ARM64 para ativar. O workflow manual `.github/workflows/facial-homolog.yml` usa confirmações explícitas da homologação privada, vincula a execução ao registro operacional do lote e exige aprovação humana do ambiente `homolog`; não há ativação por push ou trailer de commit. Uma correção de lote já ativo pode usar o job protegido `reconcile-facial-homolog` mediante trailer exato e metadados coincidentes com o gate vigente; esse job exclui o deploy comum e não habilita, estende ou fecha a janela.

Antes da mutação, o script registra SHA, arquitetura, CPUs, memória, disco, migration, containers, portas, identificador não pessoal do lote e presença dos gates sem revelar valores secretos ou dados das pessoas. A ativação faz backup restrito de `docker/.env.homolog`, gera ou preserva a chave AEAD no próprio host, fixa versões identificadas como exclusivas da homologação privada e habilita o tratamento de menores somente durante execução que o autorize expressamente. Depois de aguardar qualquer job de mídia em processamento, o runtime ARM recria `api` e o worker de mídia com o mesmo gate e inicia o `face-worker`; este continua sem porta, concorrência 1, limite de 1 CPU e 768 MiB. Pausa, fechamento e rollback também propagam o gate aos processos persistentes da Markina. A reconciliação de um lote já ativo não reinicia serviços: confere o manifesto, exige a contagem autorizada e as duas prévias prontas e apenas enfileira jobs idempotentes da janela vigente.

Enquanto o piloto estiver ativo, o deploy comum SHALL falhar no preflight antes de alterar código ou banco. A política da galeria deve ser revogada, a prova de limpeza confirmada e qualquer gate temporário de menores novamente desabilitado antes de desligar o profile e liberar um novo deploy.
