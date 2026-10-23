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
- A PR #192 foi integrada automaticamente como commit `b191e1c` após os seis checks ficarem verdes. No run da `main` #38839154615, todos os seis checks passaram, mas o checkout raso não continha o commit pai (`fatal: bad revision '<SHA>^'`), impedindo o início do SSH. A correção foi integrada na PR #193 como `a8fa383`, com profundidade 2 e cobertura da política.
- No run da `main` #38844941508, os seis checks e a validação local do preflight passaram; o inventário remoto começou, mas parou porque o hash Compose do container `api` diverge do Compose atual. Conferência adicional somente de leitura confirmou que `web` corresponde e `api` e `face-search-worker` divergem. O script não produziu fingerprint de inventário completo, não houve mutação e o motivo da divergência ainda não foi determinado.
- O job `production-release` foi ignorado porque os gates faciais versionados seguem sem aprovação. A divergência operacional também precisa ser reconciliada antes de considerar o inventário válido. O release mutável não foi iniciado.

O preflight não reutiliza nem modifica a chave ou os secrets de deploy. A aprovação de `production` permanece separada e protegida.

## Preflight específico da aposentadoria InfinitePay

A operação manual `infinitepay-retirement` usa a mesma chave SSH restrita de `production-preflight`. O wrapper versionado reconhece somente `MARKINA_RETIREMENT_TARGET_SHA=<SHA completo>` e baixa `scripts/deploy-prod-infinitepay-retirement.sh` pelo SHA da `main`, comparando o blob imutável antes de executar apenas `--mode inventory`. O inventário é minimizado e não imprime configuração Compose, conteúdo do binding ou valores de segredo.

Após integração do código em `main`, a cópia root-owned do wrapper em `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper` precisa ser atualizada por uma sessão operacional autorizada para fixar o blob do wrapper e do script do SHA integrado. Conferir conteúdo, proprietário `root:root`, modo `0755`, hash do script e os comandos permitidos em `authorized_keys`; não ampliar a chave para shell nem conceder modo release. Até essa atualização e conferência, o workflow remoto falhará fechado e nenhum inventário pode ser alegado.

O inventário só fica apto quando comprova checkout/runtime alinhados, `20261021_0086`, serviços saudáveis, hashes Compose API/web, domínio/porta registrados, smoke HTTPS e binding regular exclusivo sem link simbólico, hardlink ou referência externa. O JSON sanitizado e seu fingerprint são apresentados antes de qualquer etapa mutável. O manifesto de release API/web em `0084` segue sem alteração até que esse estado seja confirmado pelo host.

## Verificação de ancestralidade do candidato

O checkout de produção pode não conter o commit recém-mergeado em `main`. Para verificar que o SHA candidato descende do último release saudável sem alterar refs ou objetos do checkout ativo, o inventário busca a ponta de `main` com filtro de blobs em um repositório Git bare temporário configurado como partial clone, confirma que ela continua igual ao SHA solicitado e verifica a ancestralidade nesse banco temporário. O diretório é removido ao terminar; qualquer falha ou mudança da ponta de `main` faz o preflight falhar fechado antes de produzir o fingerprint.

## Correção do diagnóstico de hash — 2026-10-16

O fluxo foi esclarecido pelo proprietário: esta entrega corrige um runtime já ativo, sem primeira ativação ou ampliação de escopo. O preflight avalia a autorização de manutenção por baseline, arquivos/blobs revisados e flag já ativa, separadamente dos gates documentais de ativação/expansão. Inventário, CI e aprovação protegida continuam necessários. Os registros jurídicos/calibração pendentes não são marcados aprovados para liberar código de manutenção.

A conclusão anterior de divergência real foi refutada. Compose 2.35.1 omite a resolução do `env_file` no hash direto, comportamento já registrado em `RELEASE-PAYMENT-STATUS-API-WEB.md`. Com o JSON resolvido somente em memória, `--no-interpolate` e `APP_VERSION` da API ativa, os hashes dos três serviços correspondem aos labels. Não é necessário recriar containers para corrigir essa falsa divergência.

O script corrigido completou inventário remoto somente leitura, saúde dos três serviços, bind exclusivo `127.0.0.1:8080`, HTTPS 200 e fingerprint `141aa2f1f90286bc915ec6a5eed6b94b71e8a91f819846840901341bdf5987ec`, com alvo `57bbc7c`. A correção também relê hashes após a troca, aguarda saúde por até 120 segundos e valida/recarrega exclusivamente o nginx Markina antes do smoke. CI e instalação do novo blob fixado no wrapper devem preceder o próximo preflight automático. Isso não aprova os gates jurídicos, do corpus, capacidade ou restauração.

O wrapper foi atualizado no host em 2026-10-17 para fixar o blob `081350c451047cd4f26da4e8bb807881901ce741` do inventário corrigido; proprietário/modo conferidos `root:root 0755`, SHA-256 `fddafdb3652e211a49880ab617cfa7ab4c5e29020072c1e627919859830b37a0`. A chave dedicada continua limitada ao inventário. O inventário Docker somente leitura confirmou os serviços Markina saudáveis, Nginx em `127.0.0.1:8080` e domínio `https://markina.pickyourpic.com.br`; a alteração não reiniciou serviços nem alterou credenciais. O preflight automático positivo desta correção ainda aguarda CI verde e merge.
