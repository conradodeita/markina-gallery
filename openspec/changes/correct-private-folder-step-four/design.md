# Design

## Context

Consulte `proposal.md` para a motivação. A API de pastas já lista pastas canônicas da galeria-fonte e pode incluir as restritas; o modelo de concessões relaciona cada pasta a uma ou mais clientes. O acervo da cliente já cria e fecha lotes pela API existente. A etapa Imagens ainda registra fotos sem `upload_batch_id`.

## Goals / Non-Goals

**Goals:**
- Acrescentar à resposta administrativa das pastas os nomes das clientes efetivamente atribuídas, limitados ao tenant e às pastas consultadas.
- Reutilizar os endpoints existentes de lote para pastas restritas no upload da etapa Imagens.
- Fechar o lote após o loop de tentativas, mesmo com falha parcial, sem perder o erro do upload.
- Remover a seção UI e os artefatos exclusivos da interpretação anterior.

**Non-Goals:**
- Alterar regra de elegibilidade, transporte, destinatários ou idempotência das notificações.
- Alterar lotes de pastas comuns ou inventar responsável para pasta sem concessão.
- Notificar antes de as prévias protegidas ficarem disponíveis.

## Decisions

- A API administrativa da lista de pastas retorna `client_names` como lista para pastas restritas; a consulta usa `FolderClientGrant`, `Client`, tenant e os IDs das pastas da origem validada. A interface mostra `nome da pasta — nome 1, nome 2`; pastas sem nomes continuam com o nome original.
- Ao iniciar upload restrito, a etapa cria um lote; cada registro recebe seu `upload_batch_id`; um `finally` fecha o lote após as tentativas. Pastas comuns mantêm o caminho atual. Reutilizar lotes abertos do acervo não é necessário nesta tela, cujo envio não expõe retomada concorrente.
- Se falha uma transferência, registrar o erro, continuar tentativas das demais fotos e fechar o lote. Se criação do lote falhar, não registrar fotos privadas sem lote. Se fechamento falhar, apresentar erro operacional sem declarar o envio como concluído.
- A etapa deixa de importar e renderizar o componente de overview da mudança anterior; o card da pasta original passa a ser a única apresentação. Os hashes de `backend/app/main.py` e do editor são atualizados no manifesto do preflight para o candidato exato. Nenhum gate de escopo, container, worker, banco, Docker/Compose ou migration é alterado.

## Risks / Trade-offs

- **[Consultas extras por cliente]** → resolver nomes numa consulta agrupada por concessão, evitando N+1.
- **[Lote sem fechamento após interrupção do processo]** → o fechamento ocorre em `finally`; uma falha de rede fica visível como erro e poderá ser repetida pelo fotógrafo, sem relaxar o gate do worker.
- **[Falha de alguns arquivos]** → o lote fecha para permitir processamento dos arquivos aceitos; o worker mantém o filtro de jobs terminais e fotos prontas.

## Migration Plan

Sem migração de banco. Atualizar backend e frontend juntos. Rollback consiste em reverter os arquivos da change; o campo adicional da resposta é aditivo, e os lotes já processados são registros auditáveis que não exigem limpeza.
