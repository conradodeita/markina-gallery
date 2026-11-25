# Design: cópia de backup no Google Workspace

> **SUPERCEDIDA — NÃO IMPLEMENTAR NEM DESPACHAR.** Este design pertence à tentativa encerrada em 25/11/2026; consulte [retire-platform-backup-runtime](../retire-platform-backup-runtime/proposal.md) e [prove-open-source-backup-and-recovery](../prove-open-source-backup-and-recovery/proposal.md).

## Contexto

O proprietário escolheu Google Workspace para a segunda cópia global. Em 17/11/2026 escolheu a conta Workspace já conectada também para a rotina. O app criou e verificou uma pasta dedicada em Meu Drive. D15–D16 continuam definindo frequência, retenção, escopo cifrado e custódia da chave offline. O chamador produtivo deve validar a configuração e comprovar a cópia recorrente e a recuperação sem depender do servidor de origem.

A base local está em `backend/app/platform_backup/`; ela produz artefato autenticado, catálogo append-only, store retomável e restore global, mas não tem caller de produção. `backend/app/google_drive_storage.py` já implementa upload resumable com transporte injetável. `backend/app/google_drive_oauth.py` mantém OAuth owner-only, PKCE/state, scope `drive.file` e refresh token cifrado. Esta change reutiliza esses limites; não ativa runtime.

## Decisões de arquitetura

1. A integração recebe credenciais por um provider interno protegido e destino por identificador de pasta. O provider exige conexão OAuth owner-only do tenant esperado, estado `connected` e escopo persistido exatamente igual a `drive.file`; descriptografa o refresh token com o contexto tenant/credencial e o troca por access token efêmero. Se a resposta da renovação trouxer `scope`, ele também deve ser exatamente `drive.file`; sua omissão mantém o escopo exato já persistido. O token de acesso fica em `SecretStr` somente durante a operação. Os transportes de troca de token e Drive são injetados explicitamente. O ensaio pré-abertura e a rotina usam a conta Workspace escolhida, com destino e escopo verificados.
2. O callback deve confirmar que o conjunto de escopos concedidos é exatamente `{drive.file}` antes de persistir o refresh token; não aceitar escopos adicionais vindos de concessão acumulada. Para arquivos e pastas criados pelo aplicativo, manter o scope `drive.file`; a documentação do Google limita esse escopo a arquivos criados pelo app ou compartilhados explicitamente com ele. Não ampliar para `drive` ou `drive.readonly` como fallback. Se o destino não estiver acessível, a cópia falha fechada.
3. O destino será uma pasta dedicada, privada e sem ACL pública. A criação/configuração da pasta e a inspeção das permissões efetivas pertencem à etapa operacional. O Shared Drive só será usado depois de confirmar edição Workspace compatível, quota pooled e membership/permissões. A documentação do Google registra que service accounts não têm quota própria nem podem possuir arquivos; esta change usa OAuth de usuário e não cria service account.
4. Reutilizar `upload_drive_file` para transporte resumable, UUID do backup como nome opaco e `application/octet-stream`. Depois da confirmação, buscar o arquivo pela pasta e UUID; somente um match exato pode ser lido. Zero matches permite upload; múltiplos ou metadata divergente são conflito e não criam nova cópia automaticamente.
5. A consulta `files.list` delimita a busca a `corpora=user` ou ao `corpora=drive` com `driveId` exatamente configurado, sempre pela pasta pai. `incompleteSearch`, paginação inesperada ou duplicidade falham fechado; não usar `allDrives` como corpora amplo.
6. A leitura de retorno usa `files.get` com `alt=media`, transmitida em blocos para arquivo temporário privado, sem acumular o backup inteiro em memória. O fluxo compara tamanho/SHA-256 do ciphertext e autentica AES-GCM, manifesto e schema com o contexto original antes de registrar `verified`.
7. A recuperação Workspace reutiliza `restore_global`, que exige alvo descartável, isolado, vazio e atômico. O catálogo só registra `restore_verified` depois da validação do alvo e da cópia correspondente.
8. O catálogo guarda somente UUIDs, hash, tamanho, revisão de schema, timestamps UTC e estados sanitizados. O objeto Drive é localizado pelo nome UUID dentro da pasta configurada e é revalidado antes de cada readback. Tokens, refresh tokens, IDs/links compartilháveis, URL de sessão resumable, conteúdo, nomes de clientes e dados do dump MUST NOT entrar no catálogo/logs.
9. O adapter remoto é independente da rotina `LocalBackupWorker`; integrar cópias remotas não transforma o worker local em runtime de produção. Um runner/scheduler produtivo, origem confiável no console e restauração real continuam gates específicos.
10. A cópia remota não habilita expurgo nem substitui a cópia local. Nenhuma retenção externa é removida automaticamente. Erro OAuth, quota, conectividade, checksum, GCM, schema ou restore deixa a cópia indisponível e não abre onboarding.
11. O provider de credenciais é uma biblioteca interna sem rota/caller produtivo nesta change. Seus testes usam conexão e token sintéticos; a troca e o acesso externos permanecem bloqueados até release e autorização operacional específica.
12. Constantes e protocolo/transporte HTTP compartilhados residem em `backend/app/google_drive_client.py`; `google_drive_oauth.py` os reexporta para preservar seus consumidores. O provider de backup e o storage importam a fronteira comum sem carregar o módulo de rotas OAuth.

## Evidência externa e limites

- OAuth scopes: [`drive.file` e escopos Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth). Manter o menor escopo possível; a pasta precisa ser criada pelo app ou explicitamente autorizada.
- Refresh OAuth: [RFC 6749, seção 6](https://www.rfc-editor.org/rfc/rfc6749.html#section-6) define que escopo omitido em refresh mantém a concessão original; se o provedor retornar `scope`, o provider verifica que permanece exatamente `drive.file`.
- Shared Drives: [visão geral oficial](https://developers.google.com/workspace/drive/api/guides/about-shareddrives). Arquivos pertencem à organização e contam contra armazenamento pooled; permissões da pasta pai propagam aos filhos. Edição, quota e permissões reais do projeto do proprietário não foram consultadas.
- Uploads: [upload resumable](https://developers.google.com/workspace/drive/api/guides/manage-uploads) é indicado para arquivos grandes ou redes sujeitas a interrupção.
- Download de conteúdo: [`files.get` com `alt=media`](https://developers.google.com/workspace/drive/api/guides/manage-downloads) permite recuperar bytes de arquivo binário.
- Listagem de arquivos: [`files.list`](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) permite restringir a consulta a `corpora=drive`/`driveId` e informa `incompleteSearch`; a integração exige resultado completo.

## Não objetivos

- Não enviar fotos, arquivos biométricos/WhatsApp, arquivos em claro ou backup por tenant.
- Não autorizar scope OAuth amplo, compartilhar pasta, criar conta/credencial real ou fazer chamada Google nesta etapa local.
- Não ativar job de produção, publicar migration/código, mudar DNS, pausar serviços, apagar qualquer cópia ou abrir cadastro público.
- Não declarar a quota de aproximadamente 100 TB como verificada; ela é uma informação do proprietário até leitura autenticada.

## Segurança e recuperação

As verificações seguem fail-closed e deixam a origem local intacta. O ensaio pré-abertura com a conta do proprietário exige inventário do destino, escopo, quota e permissões; leitura de retorno; validação de tamanho/hash/GCM/manifesto/schema; restore global em destino descartável isolado e vazio; e evidência sanitizada revisada pelo proprietário. Antes da abertura, a identidade Workspace dedicada da rotina também deve comprovar uma cópia lida de volta e validada. A aprovação não concede publicação, alteração operacional nem expurgo.
