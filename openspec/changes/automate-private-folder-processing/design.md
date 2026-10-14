## Contexto

O Acervo do Cliente usa pastas de conteúdo com `PhotoFolder.audience_scope = 'selected'`. O modelo multi-tenant já possui `FolderProcessingSettings`, geração por pasta, API administrativa e worker de prévias. A mudança deve especializar esse fluxo para pastas privadas sem criar um segundo modelo de configuração nem alterar o comportamento de pastas públicas.

## Decisões

1. `audience_scope = 'selected'` identifica uma pasta privada. As consultas continuam filtradas por `tenant_id` e as ações seguem autenticadas e auditadas. Pastas públicas (`all` ou legado nulo) mantêm os controles existentes.
2. A configuração efetiva de prévia de pasta privada fica sempre ativa e isolada da galeria pública. Sem override personalizado próprio, o valor é 75% e 0,0 EV. Valores personalizados já gravados continuam sendo específicos da pasta. A tabela `FolderProcessingSettings` existente é suficiente; não é necessária migration.
3. O modo facial local de uma pasta privada não bloqueia indexação. O gate global, rollout por galeria, elegibilidade, autorização de ambiente e controles biométricos continuam valendo. A interface não oferece herança, pausa ou permissão local.
4. O worker agenda a prévia privada somente depois do job facial mais recente da foto concluir com sucesso. Falha facial não impede as prévias convencionais. O ajuste usa os derivados administrativos limpos da fonte original.
5. Ao mudar intensidade ou exposição, o sistema incrementa a revisão, cancela a geração anterior e enfileira novamente apenas fotos da pasta cujo job facial mais recente concluiu. O worker continua validando geração e fingerprint antes de publicar.
6. A API existente `/admin/photo-folders/{id}/processing` identifica pastas privadas pelo escopo e retorna defaults efetivos. Para pastas privadas aceita apenas controles de intensidade/exposição do produto; valores locais antigos de herança/desligamento são ignorados por política. A retentativa facial permanece tenant-scoped.
7. O painel privado conserva o acordeão da pasta, remove opções e ações manuais obsoletas, salva controles imediatamente, mantém barras de progresso e empilha os cartões em uma coluna no desktop.

## Riscos e mitigação

- O rollout facial pode estar indisponível. O painel informa o gate e não oferece exceção por pasta.
- Alterações concorrentes com workers ficam protegidas por revisão, claim e fingerprint; a fonte convencional nunca é substituída.
- Limpeza global de prévias deve reconhecer pastas privadas como processamento sempre ativo e recusá-la enquanto elas existirem.
- Nenhum consentimento, criptografia, retenção, gate infantil ou configuração facial global será alterado.
