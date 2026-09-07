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

As versões de aviso, consentimento, base legal, retenção, política infantil e calibração são gates independentes. Dados reais em homologação privada exigem autorização humana explícita por execução e registro não pessoal de lote, origem, finalidade, responsável pelo upload, quantidade e retenção. O lote pode incluir adultos e menores, mas a janela autorizada não habilita produção nem o fluxo infantil comum. Depois de habilitado, o sistema cria políticas técnicas internas automaticamente; o fotógrafo não as prepara nem ativa por galeria.

## Backup, migration e rollback

Antes de migration ou deploy autorizado:

1. confirmar projeto Compose e paths absolutos do workspace/volumes;
2. registrar SHA da aplicação, head Alembic e inventário de containers/portas;
3. produzir backup consistente do PostgreSQL e verificar restauração em destino isolado;
4. aplicar somente `alembic upgrade head`; as revisions são aditivas e não ligam a flag nem fazem backfill;
5. subir a aplicação com flag desligada e sem o profile facial;
6. validar healthchecks; somente depois, em aprovação separada, habilitar e iniciar o profile facial, que reconciliará galerias elegíveis uma vez no startup.

Rollback: desligar o kill switch, interromper novos jobs, priorizar purge, confirmar a prova de limpeza e retornar aplicação/worker ao SHA anterior. As tabelas aditivas permanecem para auditoria; não executar downgrade destrutivo em homologação ou produção. Seleções, pedidos, privadas e mídia histórica não são apagados pelo purge facial.

## Incidentes e limpeza

- Fila facial alta ou degradação de prévias: desligar o kill switch e parar somente `face-worker`; mídia e seleção manual continuam operacionais.
- Modelo/versão divergente: desligar o subsistema, corrigir imagem/configuração e reiniciar para reconciliação automática versionada; nunca aceitar índice antigo silenciosamente.
- Referência além de 15 minutos ou candidata além de 24 horas: executar o cleaner idempotente e confirmar `facial-cleanup-proof`; abrir incidente se o SLA continuar violado.
- Revogação de finalidade, foto ou galeria: purge prioridade zero antes de qualquer exclusão operacional.
- Notificação ambígua: não reenviar automaticamente; a UI autorizada continua sendo a fonte do resultado.

Logs e métricas podem conter somente IDs internos, estados, versões, contagens, latência, fila e categorias sanitizadas. Imagem, vetor, score, landmarks, caixa facial, nome inferido e telefone são proibidos.

## Piloto privado em homologação

A ativação operacional usa o workflow manual `.github/workflows/facial-homolog.yml`, aprovado no Environment `homolog`, que envia `scripts/manage-homolog-facial.sh` por stdin; nunca use edição manual improvisada. O modo `inventory` é somente leitura. O modo `activate-private` exige SHA integral publicado, host ARM64, confirmação `ENABLE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG`, identificador não pessoal do lote, referências de origem, autorização e operador, quantidade esperada de 500–1.000 arquivos, retenção de 1–72 horas, janela de 30–240 minutos, declaração sobre menores e inventário imediatamente anterior. Ele gera a chave AEAD no host, grava o manifesto operacional restrito, limita concorrência/CPU/memória, aguarda job de mídia em andamento antes de recriar processos persistentes e valida o mesmo gate na API e no worker, além de migration e ausência de porta nova. `FACIAL_MINOR_SEARCH_ENABLED=true` só é aceito quando a própria janela autorizada declara menores e ainda não expirou.

O modo `monitor` usa `scripts/benchmark-homolog-facial.py`, confirma lote/autorização/quantidade/menores contra o runtime e preserva por sete dias somente JSONL agregado. O upload é feito pelo administrador/fotógrafo autenticado depois que o monitor iniciar; o workflow não transfere imagens. Se fotos desse mesmo lote concluírem as prévias sem job por divergência comprovada do gate em processo persistente, `reconcile-private` exige `RECONCILE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG`, o SHA publicado e os mesmos lote/autorização/quantidade/menores; o manifesto limita a seleção à janela ativa, a contagem deve ser exata e a operação somente enfileira jobs idempotentes, sem reinício, novo upload ou extensão. Uma divergência material comprovada entre a quantidade registrada e a persistida exige também `Facial-Recorded-Count`; a execução valida os dois números, corrige somente a quantidade no ambiente/manifesto com trilha de auditoria e preserva os demais vínculos e prazos. Para o lote já publicado cujo workflow ainda não continha esse modo, o job de CI `reconcile-facial-homolog` pode transmitir o script corrigido por stdin após todos os gates e aprovação do Environment, enquanto exclui explicitamente o deploy comum. O deploy comum recusa flag ou worker facial ativos antes de qualquer troca de SHA. Para encerrar o piloto, use `close-private` com o mesmo `batch-id` e `CLOSE_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG`: ele interrompe o worker, revoga as políticas, elimina embeddings, candidatas e referências cifradas, confirma contagens agregadas zeradas, registra o manifesto de fechamento, desliga o processamento e remove os gates temporários. Não existe revogação manual por galeria no painel do fotógrafo. Em emergência, interromper a capacidade de processamento tem prioridade, mas resíduos cifrados ainda exigem limpeza posterior registrada.

Excepcionalmente, a migração do piloto legado que antecede `FACIAL_HOMOLOG_PRIVATE_MODE` usa o trailer exato `Homolog-Facial: pause-legacy-for-private-upgrade`. O job protegido envia o modo `pause-legacy-for-private-upgrade` com a confirmação `PAUSE_LEGACY_FACIAL_FOR_PRIVATE_UPGRADE`; o script recusa se o marcador privado estiver ativo, se a flag já estiver desligada ou se o `face-worker` não existir. A operação faz inventário e backup restrito, desliga somente a flag facial, para somente o worker, recria somente a API e recarrega o Nginx da Markina. As fotos permanecem intactas e não há reativação automática. Depois do deploy, a exclusão administrativa das fotos remove também seus registros faciais; antes de iniciar o novo monitor e reupload, confirmar o inventário remanescente e manter `FACIAL_PROCESSING_ENABLED=false`. A ativação privada continua sendo uma execução manual separada.
