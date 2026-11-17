# Revisão de segurança e proteção de dados — 01/11/2026

## Escopo e limite

Checkpoint local e consultas somente leitura na instância ativa `APP_ENV=production`, `APP_VERSION=74f61300e7a818d1605afda3db1d07574c443110`, em 01/11/2026 (BRT). Nenhuma configuração, dado, arquivo de backup, serviço ou schema remoto foi alterado. Esta revisão não é pentest completo, não certifica segurança integral nem adequação LGPD.

## Banco de dados e transporte

- O container PostgreSQL não publica uma porta no host. O API usa `db:5432` pela rede Docker do projeto; o Nginx do projeto publica somente `127.0.0.1:8080`, atrás do proxy externo observado. Isso reduz exposição de rede direta do banco.
- Consultas read-only feitas pela conexão usada pela API encontraram `ssl=off`, 10 sessões em `pg_stat_ssl` com `ssl=false`, e `sslmode` ausente na URL efetiva.
- A role efetivamente usada pela API respondeu `rolsuper=true`, `rolcreatedb=true` e `rolcreaterole=true`. Portanto, uma intrusão na API herdaria privilégios de administração do PostgreSQL que excedem o necessário para servir requisições.
- PostgreSQL 17 oferece TLS nativo; sua documentação descreve a ativação via `ssl=on` e a configuração de certificados. A recomendação OWASP é exigir conexões cifradas, validar o certificado e limitar os privilégios da conta usada pela aplicação. Referências: [PostgreSQL 17 — SSL/TCP](https://www.postgresql.org/docs/17/ssl-tcp.html), [OWASP Database Security](https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html).
- A configuração local do Compose também usa a mesma identidade padrão de bootstrap em `DATABASE_URL` e `POSTGRES_USER`; isso reforça que a próxima mudança precisa separar explicitamente a role de runtime da role de migration. Nenhuma alteração foi feita.

## Cifragem em repouso e arquivos

- O código local usa AES-GCM para credenciais de integração (`backend/app/integration_secrets.py:146`), sementes TOTP (`backend/app/totp_crypto.py:105`) e envelopes biométricos (`backend/app/facial/crypto.py:105`); senhas usam Argon2id em `backend/app/auth.py`. Isso protege domínios específicos, não todas as colunas do banco.
- O código recebe os chaveiros desses domínios por variáveis de ambiente (`INTEGRATION_SECRET_KEYS`, `ADMIN_TOTP_KEYS` e `FACIAL_AEAD_KEYS_JSON`). Não li valores nem env de produção; a origem/proteção operacional dessas chaves, seu ciclo de rotação e custódia no backup não foram comprovados nesta revisão.
- Os JPEGs originais são gravados por `backend/app/media.py:451` no volume `media-source` declarado em `docker/docker-compose.yml:151,158`; não encontrei cifragem por arquivo no caminho de gravação. A proteção em repouso desses arquivos e dos dados comuns do PostgreSQL depende da camada de volume.
- O servidor apresenta `/dev/sda1` como ext4, sem `dm-crypt`, compatível com cifragem transparente gerenciada pelo provedor. A documentação oficial da Oracle afirma que Block Volumes, boot volumes e backups são sempre cifrados em AES-256 por padrão; porém, o recurso e a chave efetivos da instância não foram consultados na tenancy. Portanto, cifragem do provedor é uma inferência forte para a infraestrutura Oracle, e o uso de chave gerenciada pelo cliente continua desconhecido. [Oracle OCI — Block Volume Encryption](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/blockvolumeencryption.htm).

## Backups observados

- Há `oracle-project-backups.timer` ativo no host e o serviço declara fazer cópias cifradas/verificadas de Pick-your-Pic e ClearBudget.
- Em 02/11, o job registrou Pick-your-Pic como `verified`, com 2.917.197.819 bytes. A leitura do script confirmou que esse estado só é emitido depois da verificação lógica do dump restaurado, checksum após baixar a cópia remota e confirmação do manifesto remoto; o código declara `restore_verified=true` e `download_verified=true` e atualiza a cópia local `latest.tar.gz` com modo `0600`.
- A mesma execução terminou com status 1 ao encontrar novamente `RuntimeError: interrupted candidate needs reconciliation` durante a sequência multi-projeto. Portanto, o serviço global segue falhando e o outro projeto não foi confirmado nesta execução, embora o backup de Pick-your-Pic tenha sido marcado como verificado antes da falha. A verificação de restauração declarada pelo script ignora owner/privilégios e não representa uma recuperação integral de aplicação, mídias, filas ou ambiente.
- O script cria o arquivo tar local antes do envio e inclui configuração runtime privada; essa cópia local recebe modo `0600`, enquanto a transferência remota usa `rclone crypt`. A cifragem do arquivo local depende da camada de armazenamento do host; o volume/chave OCI efetivos continuam sem verificação. Não inspecionei conteúdo/candidato remoto, não executei restore, não reiniciei nem alterei o serviço.

## Borda HTTPS

- Uma requisição HEAD read-only à raiz pública retornou HTTP 200 e validação de certificado pelo cliente `curl` (resultado 0). O cliente disponível não expôs a versão TLS negociada.
- Na resposta da raiz não apareceram `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` ou `Permissions-Policy`. O código Next local configura `Referrer-Policy` somente em duas rotas administrativas (`frontend/next.config.mjs:20-25`); o Nginx local aplica `no-store` ao painel, sem definir os demais cabeçalhos (`docker/nginx/nginx.conf:59-60`). Esta observação cobre apenas a resposta testada, não todos os caminhos/proxies.

## Dependências e análise estática

- `npm audit`: 21 alertas no lockfile completo (18 moderados, 3 altos, 0 críticos). `npm audit --omit=dev`: 0 vulnerabilidades. Os alertas reportados estão no grafo de ferramentas de desenvolvimento/teste, incluindo `undici@8.12.1`, `vite@8.2.2`, `zod@4.4.3` e a cadeia ESLint/`minimatch`; nenhuma correção foi aplicada neste checkpoint.
- `pip-audit 2.10.1` contra `backend/requirements.txt` e o arquivo incluído por ele: `No known vulnerabilities found`. Também inventariei somente nomes/versões das 61 distribuições Python instaladas no container de produção e auditei essas versões exatas com `pip-audit --disable-pip --no-deps`: `No known vulnerabilities found` na consulta de 01/11/2026. Nenhum pacote foi instalado ou alterado no servidor; essa consulta de advisories não prova procedência/hash dos artefatos nem elimina risco desconhecido.
- `Bandit 1.9.4` sobre `backend/app`: 0 achados altos, 3 médios e 25 baixos. Os médios são: B104 no classificador de bindings (não abre socket); B608 sobre consulta que interpola somente nomes de tabela de uma tupla constante allowlisted; B310 na chamada Evolution, cuja URL vem de configuração privilegiada do servidor e não de entrada do fotógrafo/cliente, mas ainda merece validação de esquema/host. Não foi confirmado exploit a partir desses alertas.

## Atualização local — 02/11/2026

- Nova consulta `npm audit` no frontend retornou os mesmos 21 alertas do grafo completo: 18 moderados e 3 altos; `npm audit --omit=dev` retornou 0 vulnerabilidades. Nenhuma dependência foi alterada.
- Bandit não está instalado no ambiente virtual ativo, então os resultados 1.9.4 acima permanecem a última análise estática desse tipo; não instalei ferramenta nem dependências adicionais.
- Os testes focados independentes de autenticação, TOTP/OTP e criptografia facial passaram em SQLite temporário: 83 aprovados, 2 ignorados (testes de migration TOTP que exigem PostgreSQL), 50 avisos. A primeira tentativa também incluiu testes multi-tenant em um único SQLite e gerou colisões de fixture; esse resultado foi excluído, e isolamento tenant-versus-tenant continua pendente com o PostgreSQL sintético indisponível.
- Em 02/11, fiz nova consulta SQL estritamente read-only pela conexão efetiva da API. A role `markina_gallery_homolog` retornou `rolsuper=true`, `rolcreatedb=true` e `rolcreaterole=true`; `SHOW ssl` retornou `off`; a sessão da consulta e as outras nove sessões observadas em `pg_stat_ssl` estavam sem TLS. O inventário Docker confirmou o PostgreSQL saudável sem porta publicada no host (somente `5432/tcp` interno). A URL de conexão, tokens e valores de ambiente não foram exibidos.
- Consulta read-only ao timer e journal de backup mostrou uma tentativa em 02/11: Pick-your-Pic terminou a etapa como `verified` com 2.917.197.819 bytes, mas a execução total falhou em seguida por candidato interrompido. O script aponta criptografia `rclone crypt` no destino remoto e mantém uma cópia local com permissão `0600`; a chave/criptografia do volume hospedeiro segue desconhecida.
- Não reconsultei volume/chave OCI ou cabeçalhos neste checkpoint. Esses achados continuam sendo a fotografia read-only datada de 01/11/2026, não uma confirmação de estado atual.

## Validação de regressão e dependências OpenSpec

- A tentativa da suíte backend completa em 02/11 usou SQLite temporário e PostgreSQL sintético em `127.0.0.1:15470`, sem conexão com produção. Avançou até 68%, exibiu dois erros e 11 skips observados até 64%, mas ficou parada por mais de dez minutos enquanto o PostgreSQL sintético e os comandos Docker de leitura não respondiam. A execução foi interrompida sem resumo nem tracebacks; os dois erros permanecem sem classificação e a task 4.4 continua aberta. Log fora do Git: `C:\codex-data\temp\pyp-backend-final-20261102.log`.
- A change `improve-photographer-credit-workflows` está em 16/19: tasks 1.1–1.3 (persistir nome informado, busca por nome/e-mail e autocomplete) continuam pendentes porque dependem de R14-0–6; 1.4 (filtros por e-mail) já está concluída pela decisão anterior. Não foi feito backfill ou inferência de nomes.
- Gates R14 verificados diretamente nos `tasks.md`: TOTP aguarda revisão humana (`protect-admin-totp-secrets` 3.4); reconciliação/ensaio multi-tenant remoto mantém tasks de publicação e revisão pendentes (`add-small-multi-photographer-pilot` 8.2–8.4); compras MP mantém 4.2 aberta para os limites externos de PIX, chargeback e aprovação tardia; `add-platform-owner-console`, Drive, backup/restore e fidelidade ainda têm tarefas abertas, incluindo decisões comerciais/operacionais. A existência de uma capability, proposta ou teste local não fecha esses gates.
- Portanto, `add-photographer-signup-portal` não deve ser iniciada/ativada e as tasks de nome/autocomplete permanecem bloqueadas até validar e revisar os pré-requisitos. O proprietário já aprovou que fotógrafos sejam ativados somente após aprovação humana.
- Próxima mudança de segurança, se aprovada em OpenSpec: separar role de runtime e role de migration, exigir TLS com confiança de certificado em toda conexão API/worker e provar operação/rollback em PostgreSQL sintético. Correção do serviço de backup exige primeiro reconciliar o candidato existente sob revisão operacional. Nenhuma dessas ações foi executada em produção.
