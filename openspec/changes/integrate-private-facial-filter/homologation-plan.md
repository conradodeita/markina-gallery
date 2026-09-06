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
