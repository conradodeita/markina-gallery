# Operação do segredo TOTP administrativo

## Escopo e estado

O segredo TOTP do administrador é persistido em envelope AES-256-GCM no banco. O keyring é dedicado e deve vir de um gerenciador de segredos externo ao banco e ao Git. `APP_ENV` e `ADMIN_TOTP_SECRET_ENV` precisam identificar o mesmo ambiente. A API, o worker, a migration e o seed recebem a mesma configuração através do ambiente do servidor; o frontend nunca recebe as chaves.

Este procedimento descreve a operação da implementação local. Ele **não autoriza** migration, mudança de segredo, reinício, deploy ou teste com contas/dados de produção ou homologação. A produção observada executa API e worker em versões distintas; a liberação permanece bloqueada até inventariar os consumidores, validar um conjunto compatível de imagens/código, comprovar backup restaurável e aprovar janela e plano de impacto zero.

## Provisionamento

1. Gere uma chave AES de 32 bytes e um `key_id` estável (1–48 caracteres ASCII de letras, números, `_` ou `-`) diretamente no gerenciador de segredos aprovado para o ambiente.
2. Configure `APP_ENV`, `ADMIN_TOTP_SECRET_ENV` (valor idêntico), `ADMIN_TOTP_ACTIVE_KEY_ID` e `ADMIN_TOTP_KEYS` como objeto JSON `{ "<key_id>": "<chave em Base64>" }` no secret store. Não coloque valores reais em `.env`, `.env.example`, logs, comandos registrados ou artefatos Git.
3. Garanta que API, worker, `migrate` e `seed-admin` recebem as mesmas versões necessárias do keyring. Chave ausente, chave ativa ausente, Base64 inválido ou ambiente divergente causa falha fechada.
4. Antes de habilitar a migration, execute o ensaio com banco PostgreSQL descartável: upgrade de base vazia e com fator sintético, leitura TOTP com o mesmo fator, downgrade e restore isolado. Inspecione somente se o banco contém envelope, sem imprimir a chave nem o plaintext.

## Rotação

1. Publique primeiro no secret store a chave nova junto com todas as chaves antigas ainda referenciadas; selecione a nova como ativa. Não remova a antiga.
2. Em cópia isolada/restaurável, rode `python -m app.rotate_totp_keys --dry-run`. O resumo mostra somente contagens por `key_id`, itens pendentes e o identificador ativo.
3. Após validação e autorização operacional específica, rode `python -m app.rotate_totp_keys --apply --confirm ROTATE_ADMIN_TOTP_KEYS:<key_id-ativo>` no alvo aprovado. O comando trava os registros e executa a operação em uma transação; uma falha aborta o lote.
4. Confirme que `pendentes` é zero num novo dry-run e que cada envelope pode ser decifrado com o keyring que contém a chave nova. Faça login de teste controlado com o mesmo fator e confira auditoria sanitizada.
5. Preserve as chaves antigas necessárias a backups históricos. A remoção só pode ocorrer depois de inventariar envelopes em todos os bancos/backups retidos e validar restore sem a chave removida. O comando de rotação recusa envelopes cuja chave não está no keyring, sem alterar os registros.

Uma execução `--dry-run` não grava alterações. `--apply` exige confirmação literal do `key_id` ativo; IDs e contagens não são segredos, mas saídas continuam restritas a operadores autorizados.

## Recuperação de acesso e perda de chave

- Códigos de recuperação são mostrados uma vez após senha e passo TOTP válido ainda não usado. Devem ser guardados offline pelo administrador. O backend guarda somente seletor e hash Argon2id da parte secreta; o navegador não persiste os códigos em local/session storage.
- Um código de recuperação autentica um único desafio MFA uma única vez. Para emitir outro lote, o operador precisa de sessão, senha e TOTP atual; não há bypass por e-mail ou identidade.
- Se uma versão de chave for perdida, interrompa o rollout e restaure essa versão pelo secret store/cópia controlada antes de tentar ler ou migrar os registros dependentes. O banco não permite reconstruir a chave.
- A restauração de backup exige também recuperar o conjunto de chaves correspondente ao snapshot, em ambiente isolado e com fixture sintética. Não descarte cópias antigas de chave nem restaure o banco de produção para teste.
- Perda simultânea de TOTP, códigos offline e chave externa exige procedimento humano assistido; não redefina TOTP nem enfraqueça MFA por SQL ou endpoint ad hoc.

## Rollback e compatibilidade

A migration `20261031_0091` é expand: adiciona `totp_secret_envelope` e `totp_last_used_step`, faz backfill autenticado e mantém `admin_user.totp_secret` legado sem alteração para a API antiga. O modo `ADMIN_TOTP_LEGACY_DUAL_WRITE=true` só pode ser ligado durante convivência explicitamente planejada; nessa janela, a aplicação nova grava envelope e mantém o campo legado sincronizado. Escritas antigas posteriores ao backfill são reprocessadas pelo runtime novo ou reconciliadas por `0093` antes da limpeza.

A migration `0093` é contract: exige dual-write desligado, consumidores antigos atualizados/drenados e envelope/contexto válido para todas as contas; adquire lock que bloqueia escritas concorrentes à tabela de admins, permite leituras, reconcilia qualquer envelope válido com a última escrita legada e só então define plaintext como NULL. O ensaio operacional deve considerar esse breve bloqueio de autenticações que atualizem a tabela. O downgrade de `0093` decifra e restaura somente as linhas cujo plaintext foi limpo e preserva qualquer plaintext ainda presente, numa transação antes de rollback de aplicação. Mantenha as colunas/envelopes depois do rollback; remover o envelope ou chave externa é operação separada e nunca automática.

O proprietário confirmou depois que a produção atende clientes e não pode ser desligada no plano padrão. Portanto, não executar `0093` ou `alembic upgrade head` enquanto o lock, a troca de consumidores e o atendimento contínuo não forem ensaiados e demonstrados no candidato real. Se a etapa exigir bloqueio de login ou outra indisponibilidade temporária, apresentar alcance, duração estimada, janela e retorno e obter consentimento específico antes dela. Sem esse consentimento, manter o runtime atual ativo e a etapa contract pendente.

Código antigo que lê diretamente `totp_secret` espera plaintext. A expansão preserva a coluna; a etapa contract não é compatível com binários antigos até executar downgrade e restaurar plaintext. O pacote de release precisa confirmar todas as instâncias/processos, drenagem de API/worker, rota de tráfego, restore e rollback; nada disso autoriza publicação. Na situação atual, nenhuma migration remota, alteração de keyring, teste autenticado ou deploy foi autorizado.

## Evidência operacional

Registre em `openspec/changes/protect-admin-totp-secrets/validation.md` somente ambiente, versão/commit, contagens agregadas, estado de restore, resultado e bloqueios. Nunca registre chave, TOTP, código de recuperação, conteúdo de `.env`, segredo de integração ou dados pessoais.
