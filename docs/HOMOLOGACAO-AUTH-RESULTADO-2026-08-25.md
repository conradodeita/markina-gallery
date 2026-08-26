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

## Limitações e gate restante

- O host `markina-homolog.duckdns.org` já resolve para o servidor, mas ainda não existe proxy host/certificado HTTPS exclusivo no Nginx Proxy Manager compartilhado. A tentativa HTTPS falhou no handshake; nenhum host existente foi alterado.
- A validação externa do cookie `Secure` e do fluxo pela URL pública fica pendente até que um administrador do Nginx Proxy Manager crie somente o host `markina-homolog.duckdns.org` apontando para `127.0.0.1:8080`, com certificado próprio.
- Não há versão anterior da Markina Gallery neste servidor para um rollback real. O rollback permanece documentado e restrito ao projeto `markina-gallery`; não foi executado para não interromper a primeira instância saudável.

## Próxima ação autorizável

Um administrador do Nginx Proxy Manager deve cadastrar o host e o certificado exclusivos acima. Após isso, repetir os smoke tests por HTTPS, conferir o cookie seguro no navegador e remover o arquivo temporário de credenciais iniciais do servidor.
