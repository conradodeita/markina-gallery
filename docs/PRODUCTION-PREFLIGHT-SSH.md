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

## Estado da configuração em 2026-10-16

- O wrapper root-owned foi instalado em `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper`, proprietário `root:root`, modo `0755`; SHA-256 conferido com a cópia versionada: `13257952b6fca0b37125201cdf503fc44867b51a2d647b7e527ed83c5b22349b`.
- Uma chave ED25519 dedicada foi cadastrada em `/home/ubuntu/.ssh/authorized_keys` com `restrict` e comando forçado. Fingerprint: `SHA256:4MWJ/8ffnxxtIM6RBrA2Jj7sZmq0Y5hw5uJ6DfQVCLk`. Um comando arbitrário foi recusado pelo wrapper, sem tocar nos serviços.
- O environment `production-preflight` foi criado sem revisores, restrito à branch `main`. As variáveis `PRODUCTION_PREFLIGHT_SSH_HOST`, `PRODUCTION_PREFLIGHT_SSH_PORT`, `PRODUCTION_PREFLIGHT_SSH_USER` e `PRODUCTION_PREFLIGHT_PUBLIC_BASE_URL`, além dos secrets `PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY` e `PRODUCTION_PREFLIGHT_SSH_KNOWN_HOSTS`, foram configurados; seus valores não foram lidos nem registrados.
- A PR #192 foi integrada automaticamente como commit `b191e1c` após os seis checks ficarem verdes. No run da `main` #38839154615, todos os seis checks passaram, mas o preflight falhou antes de abrir SSH: o checkout raso não continha o commit pai (`fatal: bad revision '<SHA>^'`), então a verificação local de arquivos foi interrompida. Nenhum inventário remoto foi executado e nenhuma mutação ocorreu. A correção adiciona histórico suficiente ao checkout e exige cobertura da política; a execução positiva do inventário depende do próximo CI da `main`.
- O job `production-release` foi ignorado porque os gates faciais versionados seguem sem aprovação. O release mutável não foi iniciado.

O preflight não reutiliza nem modifica a chave ou os secrets de deploy. A aprovação de `production` permanece separada e protegida.
