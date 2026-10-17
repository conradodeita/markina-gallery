# Validação e continuidade — 17/10/2026

## Teste real após deploy 4342a366 — estado atual

CI/deploy `39067997576` publicou `4342a366` às 18h21 BRT. O proprietário confirmou login OTP e busca com DSC07382.jpg retornando 23 possibilidades, incluindo as duas fotos esperadas, com direcionamento automático. O worker geral e todos os workers faciais estavam saudáveis na consulta posterior, sem restart manual.

O novo lote privado de seis fotos terminou e gerou evento às 18h29min33s BRT. Consulta em transação `READ ONLY` confirmou seis jobs `completed`, pasta `released`, lote `completed` e `announced_at` preenchido. A entrega WhatsApp ficou `cancelled`, zero tentativas, `last_error=transport_disabled`. API e worker têm `TRANSACTIONAL_WHATSAPP_ENABLED=false`; nenhum valor foi alterado. Não havia entrega push desse evento.

Uma segunda consulta somente leitura confirmou `recipient_allowed=false` para a chave opaca de 85 caracteres da primeira correção. Portanto simplesmente ativar o gate não resolve o contrato de autorização. Preparação em andamento: preservar identificadores de pasta/vínculo numa chave v2 limitada e o hash da identidade completa; verificar o envio, e não somente enfileiramento. Eventos históricos opacos/cancelados não serão reabertos. O proprietário exige preservar a disponibilidade do OTP; nenhum restart, deploy ou mudança de configuração foi executado nesta investigação. Testes automatizados continuam no CI conforme preferência vigente.

PR #218 (`e3e4abe`), CI `39072065552`: passaram lint, política de deploy, regressão da chave em PostgreSQL, regressões de autorização/transporte/OTP e login/reenvio OTP. Frontend, OpenSpec, inventário e Gitleaks verdes. A suíte completa estava em execução neste registro; não conta como integração concluída. O plano operacional `activation-plan.md` registra o inventário adicional, eventos afetados, parada controlada do deploy e recuperação, aguardando autorização específica para configuração.

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

Integração `cf21eca` concluída na branch da PR #213, preservando a correção facial, a correção de chave e as duas regressões focadas do workflow. A entrega originada na PR #215 será revisada em conjunto na PR #213; não publicar duas revisões concorrentes. CI positivo da combinação e aprovação operacional ainda pendentes.

## Validação positiva focada e configuração do OTP

CI combinado `39054318967`, revisão `071343f`: steps “Regressões dos limites faciais por origem” e “Regressão da chave do aviso privado em PostgreSQL” aprovados; frontend, Gemma, OpenSpec, Gitleaks e política de homologação também aprovados. Backend integral ainda em execução neste checkpoint. Não tratar o step focado como conclusão da suíte completa ou confirmação no servidor.

Consulta somente leitura da configuração do cliente de teste confirmou binding Evolution válido, canal `staging` em estado `ready`, remetente correspondente e verificação registrada às 17:31:25 UTC. Nenhuma conexão foi refeita ou credencial alterada. A configuração consultada não revelou outro bloqueio; o worker geral parado continua impedindo consumo da fila. Após retomada aprovada, solicitar um OTP novo pelo fluxo normal e confirmar recebimento com o proprietário.
