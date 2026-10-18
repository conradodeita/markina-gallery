# Tasks

## 1. Diagnóstico

- [x] 1.1 Registrar a evidência do deploy interrompido antes da preservação, do checkout remoto ainda em `0779b3e`, do Alembic `20261016_0082` e da saúde HTTP 200; confirmar que a regressão de política falha contra o probe antigo.

## 2. Correção do probe

- [x] 2.1 Consultar `alembic_version` diretamente no container PostgreSQL do projeto e validar a revisão contra a única head do SHA alvo; confirmar com teste automatizado que o caminho não usa a imagem `migrate` anterior para o probe prévio.
- [x] 2.2 Fazer a falha do probe emitir diagnóstico sanitizado e continuar interrompendo antes de parar writers; validar sintaxe Bash e regressões de política do deploy.

## 3. Integração e release

- [x] 3.1 Executar validação OpenSpec, policy suite de homologação e `alembic heads`; abrir PR #212 e confirmar checks obrigatórios verdes e merge em `develop` no commit `25cd338`.
- [x] 3.2 Após merge e gate autorizado, executar o workflow `39046656588`; confirmar backup, SHA `25cd338`, migration `20261016_0082 → 20261017_0083` e health checks locais/públicos; inventário somente leitura `39049112709` confirmou revisão `20261017_0083` e HTTP 200 em `/healthz` e `/api/health`.
