# Validação e continuidade — 17/10/2026

## Publicação anterior e conferência visual

As PRs #204/#210/#212 foram integradas em develop e publicadas em homologação no SHA `25cd338`. O CI/deploy `39046656588` e o inventário `39049112709` confirmaram schema 0083 e saúde. A PR #214 registra essa publicação. Esses resultados são históricos e não cobriram o erro de persistência descoberto no teste real posterior.

Após liberação de sessão administrativa pelo proprietário, foram conferidos os rótulos/valores `Pastas com importação ativa = 0` e `0 fotos nas pastas ativas`, ausência do KPI agregado `Falhas de mensagem` no painel financeiro carregado e Push/WhatsApp habilitados em `Novas fotos privadas`. Nenhum formulário foi salvo e nenhum aviso foi enviado pelo executor. Capturas permanecem em diretório local ignorado, fora do Git.

## Reprodução real autorizada

O proprietário iniciou um lote privado de quatro fotos para o cliente de teste indicado na conversa. Consultas SQL em transação `READ ONLY` e inspeção somente leitura do container confirmaram:

- quatro jobs de mídia `completed`, quatro fotos disponíveis e pasta canônica restrita `released`;
- lote `closed`, sem `announced_at`, sem evento privado ou entrega;
- worker geral encerrado com código 1 às 17:17:51 UTC, sem OOM;
- traceback no flush de `enqueue_event`, com `sqlalchemy.exc.DataError` / `psycopg.errors.StringDataRightTruncation`: valor maior que `character varying(192)`;
- identidade composta do aviso com 193 caracteres, contra coluna existente de 192.

O proprietário relatou depois ausência de OTP. A fila apresentou solicitações OTP `queued` e `expired` criadas após a saída do worker. O worker geral também consome essa fila; o incidente afeta os dois fluxos. Não foram lidos códigos, payloads, segredos ou dados de outros destinatários. Na consulta inicial, o cliente de teste tinha telefone verificado e nenhuma inscrição push ativa; essa condição foi informada separadamente e não causa a falha do INSERT.

## Regressão antes da correção

- As primeiras execuções da nova regressão exigiram ajuste da importação da fixture e da associação sintética fotógrafo/conta. Essas falhas de preparação não são evidência da causa de runtime.
- CI `39054048258`, SHA `c0a57fd`: lint e steps anteriores aprovados; regressão PostgreSQL falhou no fluxo real com `StringDataRightTruncation` em `VARCHAR(192)`; regressão SQLite falhou com `assert 193 <= 192`. Resultado focado: `2 failed` em 6,49 segundos. Nenhum transporte externo foi usado.
- A suíte antiga do CI `39052639852` foi cancelada porque sua revisão documental foi substituída pela regressão; não conta como backend integral aprovado. As execuções de reprodução anteriores também não contam como validação positiva.

## Correção preparada

O gerador preserva chaves textuais que já cabem em 192 caracteres e condensa somente as maiores em prefixo do evento mais SHA-256 da identidade completa. Não altera coluna, migrations, snapshots, acesso, destinatários, templates, configuração dos canais ou retry. O lote real permanece para retomada pelo worker corrigido, sem enfileiramento manual nem edição de dados.

As regressões verificam gravação em PostgreSQL, conclusão do lote, os dois canais, repetição sem duplicação, distinção entre novos lotes das mesmas fotos e compatibilidade com uma chave curta preexistente. Testes automatizados executados somente no CI, conforme preferência vigente.

CI positivo completo, publicação e confirmação real da retomada estão pendentes. A entrega será integrada à correção facial para validar/publicar a combinação preservando develop e schema 0083. O deploy continua exigindo inventário atualizado e aprovação operacional; nenhum restart, deploy, alteração de configuração ou disparo manual foi executado por este chat.
