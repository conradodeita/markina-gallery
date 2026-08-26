# Resultado da homologação de autenticação — 2026-08-25

## Escopo executado

- Código instalado exclusivamente em `/opt/markina-gallery`, no commit `17911c8`.
- Compose executado somente com `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Porta publicada exclusivamente em `127.0.0.1:8080`; PostgreSQL e Redis não receberam portas no host.
- Segredos e credenciais iniciais foram gerados no servidor, fora do Git, com permissões `0600` e propriedade de `ubuntu`.

## Evidências aprovadas

- `docker compose config --quiet`: aprovado.
- Migration `alembic upgrade head`: concluída pelo serviço `migrate`, com saída `0`.
- Healthchecks: `db`, `redis`, `api`, `web`, `nginx` e `worker` saudáveis.
- `GET http://127.0.0.1:8080/healthz`: resposta `ok`.
- `GET http://127.0.0.1:8080/api/health`: resposta `{"status":"ok","service":"api"}`.
- Seed do administrador `conradodeita@gmail.com`: concluído sem expor senha ou segredo TOTP.
- Smoke de administrador: senha, TOTP e autorização de `/api/admin` aprovados internamente. O cookie permanece `Secure` em homologação.
- Desafio de acesso de cliente em adaptador sandbox: `POST /api/auth/client/challenge` retornou `202`, sem envio externo de WhatsApp.
- O nginx da Markina foi associado exclusivamente à `npm-network` com o alias `markina-homolog-nginx`; a rede possui apenas esse container e o `nginx-proxy-manager` como membros relacionados ao encaminhamento.
- Host HTTPS exclusivo criado: `markina-homolog.duckdns.org` encaminha para `markina-homolog-nginx:80`, está online e possui certificado Let's Encrypt próprio. O host existente do ClearBudget não foi alterado.
- HTTP redireciona para HTTPS (`301`); os healthchecks público e API retornaram sucesso por HTTPS.
- Smoke externo de administrador: senha, TOTP, cookie `Secure` e autorização de `/api/admin` aprovados.
- Smoke externo de cliente: conta sintética sem dados reais concluiu desafio, verificação, redirecionamento e autorização de galeria por HTTPS.
- Rollback testado somente no nginx da Markina: retorno ao commit saudável `17911c8` e restauração do commit `a16c27d`, ambos com healthcheck local aprovado. Nenhum recurso externo foi reiniciado ou editado.

## Limitações operacionais

- O adaptador de WhatsApp permanece em sandbox e não enviou mensagens reais.
- A conta administrativa inicial e o segredo TOTP estão apenas em arquivos externos ao Git, com permissões `0600`. O proprietário deve guardar essas credenciais por canal seguro e, então, remover o arquivo temporário `INITIAL_ADMIN_CREDENTIALS.txt`; o `.env.homolog` continua protegido no servidor.

## Próxima ação autorizável

Guardar as credenciais iniciais por canal seguro, confirmar o acesso humano no navegador e remover o arquivo temporário de credenciais iniciais do servidor. A promoção para produção requer change e aprovação próprios.
