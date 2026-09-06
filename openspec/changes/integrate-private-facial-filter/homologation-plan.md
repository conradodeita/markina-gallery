# Inventário e roteiro de homologação sintética

## Inventário zero-impact proposto

- Projeto Compose: `markina-gallery`, arquivo `docker/docker-compose.yml`.
- Subdomínio conhecido: `markina-homolog.duckdns.org` por meio do proxy/rede externa `npm-network` já existente.
- Única porta publicada pelo projeto: Nginx `${MARKINA_GALLERY_PORT:-8080}:80`.
- Serviços atuais preservados: `nginx`, `web`, `api`, `worker`, `migrate`, `db`, `redis`; Evolution permanece em profile próprio.
- Novo serviço: `face-worker`, profile `facial`, sem porta, até 1 CPU e 768 MiB, volume de derivados somente leitura e volume exclusivo de referências.
- Nova migration: revision `0043`, somente aditiva, sem política/backfill/ativação implícitos.
- Estado inicial obrigatório: `FACIAL_PROCESSING_ENABLED=false`, profile facial não iniciado e nenhuma galeria ativa.

Nenhum container, rede, volume, proxy, firewall, DNS, certificado ou secret de terceiro será alterado. Este inventário não autoriza execução.

## Roteiro após autorização específica

1. registrar SHA de `develop`, SHA atualmente publicado, run anterior, head Alembic, containers, networks, mounts e portas;
2. confirmar backup/restauração e espaço disponível sem exibir credenciais;
3. executar build e migration autorizados com flag desligada;
4. validar `/healthz` e `/api/health`, login do fotógrafo, login OTP e seleção manual antes de tocar no filtro;
5. confirmar migration no head e ausência do `face-worker`/portas novas no profile padrão;
6. com autorização de ativação separada, iniciar profile `facial` e verificar healthcheck/uso ocioso sem política ativa;
7. criar uma Galeria pública exclusivamente sintética, com 500–1.000 JPEGs de adultos ficcionais, e ativar somente essa política;
8. observar prévias simultâneas, fila, prontas/total, CPU, RSS, disco, backpressure, carga/descarga do modelo e ausência de impacto no worker de mídia;
9. executar consentimento, `ready|no_face|multiple_faces|low_quality|no_candidates|failed`, fechamento/retomada, seleção, cotação, cancelamento, expiração e revogação;
10. confirmar via prova de limpeza que referências, candidatas, outbox pendente e embeddings foram eliminados, enquanto fotos, privada, seleções e histórico permaneceram;
11. revisar UI móvel/desktop e acessibilidade com imagens sintéticas adultas;
12. desligar política/profile e registrar resultados, métricas e rollback.

Falha de healthcheck, isolamento, retenção, backpressure, regressão de mídia/seleção manual ou recurso acima do limite interrompe apenas o piloto facial e aciona rollback. Nenhum dado real ou infantil poderá ser introduzido.

## Ativação sintética auditável

O script `scripts/manage-homolog-facial.sh` oferece inventário e ativação somente no checkout fixo `/opt/markina-gallery`, exige SHA integral, repositório esperado, host ARM64 e o token explícito `ENABLE_SYNTHETIC_ADULT_FACIAL_HOMOLOG`. O job `activate-synthetic-facial-homolog` somente executa depois do deploy verde quando o commit autorizado contém o trailer `Homolog-Facial: activate-synthetic-adults`.

Antes da mutação, o script registra SHA, arquitetura, CPUs, memória, disco, migration, containers, portas e presença dos gates sem revelar valores secretos. A ativação faz backup restrito de `docker/.env.homolog`, gera ou preserva a chave AEAD no próprio host, fixa versões identificadas como exclusivas da homologação sintética, mantém menores desabilitados, constrói o runtime ARM e recria somente `api` e `face-worker`. O worker continua sem porta, concorrência 1, limite de 1 CPU e 768 MiB. Falha de configuração, build, healthcheck ou porta restaura o arquivo anterior, interrompe somente o worker facial e recria somente a API.

Enquanto o piloto estiver ativo, o deploy comum SHALL falhar no preflight antes de alterar código ou banco. A política da galeria deve ser revogada e a prova de limpeza confirmada antes de desligar o profile e liberar um novo deploy.
