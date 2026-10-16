# Credencial SSH somente-leitura para preflight de produção

O job `production-preflight` não usa o environment `production` e não pode acessar a chave de deploy. Ele usa o environment separado `production-preflight`, sem revisores obrigatórios, com uma chave dedicada cujo único comando aceito é o inventário.

## Preparação no servidor

1. Gerar uma chave SSH dedicada fora do repositório e guardar a chave privada somente como secret de `production-preflight`.
2. Instalar uma cópia root-owned de `scripts/production-preflight-ssh-wrapper.sh` em `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper`, com proprietário `root:root` e modo `0755`. O wrapper busca o script de inventário no SHA imutável solicitado e confere o blob Git contra o hash revisado nele; se o script mudar, o preflight falha fechado até que o hash e a revisão do wrapper sejam atualizados.
3. Acrescentar a chave pública correspondente ao `authorized_keys` do usuário SSH configurado para o preflight, usando uma entrada com comando forçado e recursos SSH desativados:

   ```text
   restrict,command="/usr/local/sbin/markina-gallery-preflight-ssh-wrapper" ssh-ed25519 <chave-publica> github-production-preflight
   ```

4. Confirmar que o usuário consegue executar o inventário sem shell, forwarding, PTY, SFTP/SCP ou comandos fornecidos pelo cliente. O wrapper valida `SSH_ORIGINAL_COMMAND` como `MARKINA_TARGET_SHA=<40 hex>`, baixa somente o arquivo pinado por SHA/blob e sempre executa `--mode inventory`; não usa stdin remoto nem altera refs Git do checkout.
5. Conferir a regra de `authorized_keys` e as permissões do wrapper por inspeção. Não usar a chave de deploy, não modificar secrets existentes e não executar comandos de release durante essa preparação.

## Configuração no GitHub

Criar o environment `production-preflight`, permitir somente a branch `main`, sem required reviewers, e cadastrar somente os valores necessários ao inventário:

- Variables: `PRODUCTION_PREFLIGHT_SSH_HOST`, `PRODUCTION_PREFLIGHT_SSH_PORT`, `PRODUCTION_PREFLIGHT_SSH_USER`, `PRODUCTION_PREFLIGHT_PUBLIC_BASE_URL`.
- Secrets: `PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY`, `PRODUCTION_PREFLIGHT_SSH_KNOWN_HOSTS`.

O environment existente `production` permanece protegido pelo revisor `conradodeita` e continua contendo exclusivamente as credenciais mutáveis de deploy. O job `production-release` é o único que o referencia; assim o inventário fica disponível antes da única aprovação de release.

## Bloqueios

A configuração requer criar chave e entrada de `authorized_keys` no servidor e cadastrar os metadados no environment GitHub. Nenhum desses passos foi executado por este change. A publicação continua bloqueada até a configuração ser validada em um preflight real, e nenhum release deve reutilizar a credencial protegida de deploy para contornar o gate.
