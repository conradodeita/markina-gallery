# Runbook do filtro facial privado

## Estado seguro e topologia

O recurso MUST permanecer com `FACIAL_PROCESSING_ENABLED=false` por padrão. O serviço opcional `face-worker` pertence ao profile Compose `facial`, não publica porta e usa apenas PostgreSQL, Redis e os volumes exclusivos `media-derivatives` (somente leitura) e `facial-references`. O único bind de rede da aplicação continua sendo o Nginx em `${MARKINA_GALLERY_PORT:-8080}`; banco, Redis, API, web e workers ficam apenas nas redes internas já existentes.

O limite inicial é um processo, concorrência 1, até 1 CPU e 768 MiB. O loop consulta a fila durável no banco, bloqueia em Redis quando ela está vazia, não varre galerias, carrega YuNet/SFace somente para jobs `index|search`, descarrega após ociosidade e recicla após o limite configurado de jobs.

## Modelos e dependências

- A imagem facial é construída separadamente por `backend/Dockerfile.face`.
- O build baixa apenas os dois artefatos do manifesto versionado `backend/facial-assets/model-manifest.json` e verifica arquitetura, tamanho, SHA-256 e licença antes de concluir.
- Nenhum ONNX, corpus, JPEG de benchmark ou embedding entra no Git.
- Divergência de manifesto, arquitetura, hash, versão, chave ou ambiente MUST impedir o worker de iniciar.
- OFIQ não pertence ao runtime desta change; sua comparação ARM continua bloqueada até provisionamento operacional específico.

## Segredos e configuração

As chaves AEAD e credenciais WhatsApp MUST ser injetadas pelo mecanismo de secrets do host e nunca copiadas para `.env.example`, frontend, logs, backup em claro ou banco comum. `FACIAL_CREDENTIAL_ENV` precisa coincidir com `APP_ENV`. A rotação mantém a chave anterior somente durante a leitura/eliminação dos envelopes existentes; não há fallback para chave desconhecida.

As versões de aviso, consentimento, base legal, retenção, política infantil e calibração são gates independentes. Preencher valores não autoriza dados reais: ativação também exige revisão humana e jurídica registrada.

## Backup, migration e rollback

Antes de migration ou deploy autorizado:

1. confirmar projeto Compose e paths absolutos do workspace/volumes;
2. registrar SHA da aplicação, head Alembic e inventário de containers/portas;
3. produzir backup consistente do PostgreSQL e verificar restauração em destino isolado;
4. aplicar somente `alembic upgrade head`; a revision facial é aditiva e não habilita política nem faz backfill;
5. subir a aplicação com flag desligada e sem o profile facial;
6. validar healthchecks; somente depois, em aprovação separada, iniciar o profile facial ainda sem ativar galeria real.

Rollback: desligar o kill switch, suspender políticas, priorizar purge, confirmar a prova de limpeza e retornar aplicação/worker ao SHA anterior. As tabelas aditivas permanecem para auditoria; não executar downgrade destrutivo em homologação ou produção. Seleções, pedidos, privadas e mídia histórica não são apagados pelo purge facial.

## Incidentes e limpeza

- Fila facial alta ou degradação de prévias: desligar o kill switch e parar somente `face-worker`; mídia e seleção manual continuam operacionais.
- Modelo/versão divergente: manter política suspensa, corrigir imagem/configuração e reindexar explicitamente; nunca aceitar índice antigo silenciosamente.
- Referência além de 15 minutos ou candidata além de 24 horas: executar o cleaner idempotente e confirmar `facial-cleanup-proof`; abrir incidente se o SLA continuar violado.
- Revogação de finalidade, foto ou galeria: purge prioridade zero antes de qualquer exclusão operacional.
- Notificação ambígua: não reenviar automaticamente; a UI autorizada continua sendo a fonte do resultado.

Logs e métricas podem conter somente IDs internos, estados, versões, contagens, latência, fila e categorias sanitizadas. Imagem, vetor, score, landmarks, caixa facial, nome inferido e telefone são proibidos.

## Piloto sintético em homologação

A ativação operacional usa `scripts/manage-homolog-facial.sh` e nunca edição manual improvisada. O modo `inventory` é somente leitura. O modo `activate-synthetic` exige SHA integral publicado, host ARM64, confirmação `ENABLE_SYNTHETIC_ADULT_FACIAL_HOMOLOG` e inventário imediatamente anterior. Ele gera a chave AEAD no host, marca as versões como `homolog-synthetic-*`, mantém `FACIAL_MINOR_SEARCH_ENABLED=false`, limita concorrência/CPU/memória e valida API, worker, migration e ausência de porta nova.

O deploy comum recusa flag ou worker facial ativos antes de qualquer troca de SHA. Para encerrar o piloto, primeiro revogue as políticas pelo painel, aguarde purge e confirme a prova de limpeza; só então desative a flag/profile por operação auditada. Em emergência, interromper a capacidade de processamento tem prioridade, mas resíduos cifrados ainda exigem limpeza posterior registrada.
