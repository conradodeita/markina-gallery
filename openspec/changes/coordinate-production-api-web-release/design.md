# Design

## Context

`production-app-release` no workflow `CI` executa `scripts/deploy-prod-app-services.sh` sob o Environment protegido `production`, preserva as imagens API/web anteriores e oferece rollback aprovado. O procedimento manual `scripts/deploy-prod-web.sh` publica exclusivamente `web`. Ambos usam `/var/lib/markina-gallery/deploy-state`, mas originalmente não disputavam um lock comum.

O script API+web é enviado ao host por SSH como conteúdo em `stdin`; por isso não pode depender de um helper que exista apenas no checkout local do runner. O fluxo web-only, por outro lado, executa do checkout e pode carregar `scripts/deploy-prod-lock.sh` diretamente.

## Goals / Non-Goals

**Goals:**

- Serializar operações que alteram serviços de produção por meio do mesmo arquivo `production-release.lock`.
- Falhar fechado antes de qualquer mutação se o lock estiver ocupado ou se o estado de outro fluxo exigir reconciliação.
- Manter intactos inventários somente-leitura, gates de SHA/schema, aprovação protegida e rollback existentes.

**Non-Goals:**

- Criar um novo processo, script ou aprovação para release API+web.
- Alterar elegibilidade de candidatos, migrations, Compose, workers, dados ou topologia de produção.
- Fazer as alterações de API e web atômicas ou garantir zero downtime.

## Decisions

- `scripts/deploy-prod-app-services.sh` adquire o lock apenas em `release` e `rollback`; inventários continuam read-only.
- O script API+web implementa a aquisição localmente porque é executado via `stdin` remoto. Usa o mesmo caminho e semântica do helper web-only: diretório de estado obrigatório, `flock -n`, recusa de `web-in-flight.sha`.
- `scripts/deploy-prod-web.sh` continua usando `scripts/deploy-prod-lock.sh`; o helper adquire o mesmo lock e recusa `app-in-flight.sha`.
- O lock permanece aberto durante todo o processo de mutação e é liberado ao encerrar o processo. Marcadores de tentativa permanecem como proteção adicional após falha.
- Concorrência, lock ausente ou marcador pendente abortam antes de selecionar/buildar/recriar serviços.

## Risks / Trade-offs

- `flock` precisa estar disponível no host Linux. A ausência é erro fechado e não dispara fallback sem lock.
- O lock não converte Compose em transação nem torna API e web atômicos; gates de saúde, aprovação e rollback existentes continuam necessários.