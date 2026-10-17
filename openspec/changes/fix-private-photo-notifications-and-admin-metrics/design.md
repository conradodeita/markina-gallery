# Design

## Context

Ver proposal.md e as três delta specs. A arquitetura atual usa `PhotoFolder` canônica tanto para conteúdo público quanto restrito; `audience_scope=selected` distingue a pasta privada. A outbox de `private_photos_ready` já revalida grants e autorização. Porém, o lote durável existente (`PrivateUploadBatch`) só aceita `DerivedGallery` legado, enquanto o componente de upload da pasta canônica não agrupa ativos. A publicação automática feita pelo worker, após `client_preview`, não tem lote para correlacionar e não cria o evento. A mudança precisa estender o lote com escopo canônico e associar o upload no componente da pasta restrita.

## Goals / Non-Goals

**Goals:**
- Tornar a disponibilidade da prévia o ponto de sincronização entre lote concluído e publicação da pasta.
- Reutilizar os eventos transacionais e suas configurações por canal, sem enviar diretamente do request HTTP.
- Remover o KPI financeiro agregado que interpreta uma projeção legada como falha atual.
- Fazer contagens da Visão Geral refletirem fotos de conteúdo e jobs relacionados.

**Non-Goals:**
- Alterar o contrato dos seis eventos da central, templates, gates de transporte ou histórico de auditoria.
- Reenviar avisos antigos, anunciar vínculos criados depois do fechamento do lote ou gerar avisos por foto.
- Remover reenvio e estados de entrega por pedido que sejam acionáveis.
- Consultar ou alterar dados, chaves, configuração ou serviços do servidor.

## Decisions

### 1. Aviso é específico ao lote de pasta restrita finalizado

Estender `PrivateUploadBatch` com escopo canônico opcional (`parent_gallery_id` e `folder_id`) e tornar `derived_gallery_id` opcional, mantendo os lotes legados válidos. Uma restrição garante que cada lote pertença exclusivamente a uma privada legada ou a uma pasta canônica restrita. A associação lote/ativo passa a permitir que o mesmo ativo participe de novo lote quando o fotógrafo retenta um upload; o vínculo continua único por par lote/ativo. A migration preserva lotes e associações legados, remove somente a restrição de unicidade global por ativo que impedia retentativas e não apaga registros. Criar rotas por `folder_id` para reabrir lista de lotes, abrir/fechar lotes, associar cada ativo registrado e permitir que o worker processe lotes canônicos fechados.

Manter o encerramento do upload como barreira para agrupar arquivos. O worker avalia lotes fechados cujo processamento terminou, confirma que há prévia convencional pronta e disponível, e enfileira uma vez por cliente com grant e acesso efetivos usando `record_restricted_folder_ready`. A disponibilidade da pasta privada é automática após o processamento; não existe dependência de um clique posterior. A rota de upload de pasta pública não cria lote privado e não participa deste aviso. Lotes abertos não são anunciados; lotes sem fotos utilizáveis terminam sem mensagem.

Alternativa descartada: disparar aviso no `Salvar e avançar` da Galeria pública; essa ação opera a Galeria pública, não finaliza uploads numa pasta privada e não deve ser confundida com o evento privado.

### 2. Não contar a projeção antiga como saúde atual de mensagens

Remover o KPI agregado da página financeira. A projeção de `PaymentNotificationOutbox` permanece para compatibilidade de telas e retry, mas `failed`, `cancelled` e `channel_disabled` não são equivalentes. Não criar um substituto agregado sem uma consulta única à outbox autoritativa e uma superfície clara de recuperação.

Alternativa descartada: corrigir apenas a descrição do KPI. Isso ainda apresentaria canais desativados e estados antigos como falhas que exigem atenção.

### 3. Pastas com importação de fotos em andamento

O card SHALL contar pastas de conteúdo públicas e privadas que contenham pelo menos um `MediaJob` de foto em `queued` ou `processing`. Pastas auxiliares e pastas sem job de mídia ativo ficam fora da contagem. O segundo valor SHALL ser a quantidade total de `PhotoAsset` cadastradas dentro das pastas contadas, incluindo fotos cujo job já terminou enquanto outra foto da mesma pasta segue ativa. Assim, os valores representam pastas com importação em andamento e o volume de fotos importadas nessas pastas, não a quantidade global de jobs nem pastas apenas marcadas como `preparing`.

Uploads de bytes em trânsito ainda não persistem um estado durável para pastas públicas; a contagem observa os jobs persistidos de geração de derivados. Lotes privados abertos também não bastam para contar uma pasta sem uma foto com job ativo. A interface deve nomear os valores como pastas com importação ativa e fotos nessas pastas, evitando sugerir que uma foto já pronta aguarda liberação manual.

## Risks / Trade-offs

- Evento e disponibilização precisam persistir juntos para que restart não perca o aviso → inserir o evento dentro da transação da publicação e usar o worker apenas para transporte.
- Um lote com falhas parciais pode ainda ter fotos utilizáveis → anunciar somente as prévias disponíveis, sem aguardar reconhecimento facial ou ajuste opcional.
- Resumo pode ficar menor que antes → isso é intencional; exclui categorias sem relação com importação de fotos de conteúdo.
- KPI agregado sai da página → falhas reais permanecem nos detalhes por pedido e nas superfícies operacionais existentes.

## Migration Plan

### Correção delimitada após teste real de 17/10/2026

O teste autorizado revelou que o identificador composto do evento canônico (pasta UUID, lote UUID, digest de fotos de 24 caracteres, vínculo UUID e cliente UUID, separados por dois-pontos) possui 193 caracteres. A coluna existente `notification_event.event_key` aceita 192. O PostgreSQL rejeitou o INSERT em `enqueue_event`; o worker geral encerrou e a transação preservou o lote fechado e sem anúncio. As quatro fotos estavam disponíveis, com jobs completos e pasta liberada. A ausência de inscrição push do cliente é uma condição independente; não explica a falha de persistência que também impede WhatsApp.

A correção SHALL manter a identidade completa do evento e o limite existente do banco sem migration: preservar a chave textual quando ela já cabe em 192 caracteres; para chaves maiores, usar `private_photos_ready:v2:<pasta UUID hex>:<vínculo UUID hex>:<SHA-256 da identidade completa>`. Pasta e vínculo permanecem recuperáveis para revalidar autorização; o digest cobre lote, conjunto de fotos, vínculo e cliente. O consumidor aceita o formato textual legado e o formato v2 estrito, preservando todas as consultas de autorização atuais. Chaves opacas da primeira correção permanecem recusadas: não inferir pasta por acesso a outra pasta, não reconstruir autorizações nem reenviar histórico automaticamente. Não alterar o ciclo do worker, autenticação, schema ou configuração de transporte nesta correção.

O teste real posterior confirmou o lote concluído e aviso cancelado em `transport_disabled`, sem tentativa. `TRANSACTIONAL_WHATSAPP_ENABLED=false` na API e no worker é um bloqueio operacional independente. A ativação dessa configuração exige autorização explícita e plano que preserve OTP; este patch não a altera. A primeira chave condensada também falha em `recipient_allowed`, pois o consumidor esperava seis campos. A regressão deve verificar autorização positiva, envio por transporte sintético, revogação e manutenção do gate desligado, além da persistência PostgreSQL já coberta.

Uma regressão em PostgreSQL sintético SHALL percorrer a conclusão do lote com UUIDs completos, gravar o evento e suas entregas, repetir a avaliação sem duplicar e distinguir outro lote das mesmas fotos. A regressão SQLite existente também verificará o contrato de 192 caracteres. O CI executará esses casos antes da suíte completa, sem transporte real. Reutilizar somente a evidência histórica de schema/deploy; a correção nova exige CI e publicação aprovados.

Adicionar colunas nullable de escopo canônico a `private_upload_batch`, tornar `derived_gallery_id` nullable e adicionar check constraint que exige exatamente um dos escopos e valida os campos correspondentes. Preservar todos os lotes legados sem backfill nem exclusão; remover a restrição de unicidade por ativo e manter a chave lote/ativo para permitir retentativas. O downgrade recusa operação se houver lote canônico ou ativo em mais de um lote. Atualizar criação/consulta/fechamento de lotes e o worker de forma compatível com os registros existentes. Entregas históricas não serão recriadas. Validar localmente com testes direcionados e OpenSpec; qualquer publicação em servidor continua fora do escopo e exige gate operacional separado.
