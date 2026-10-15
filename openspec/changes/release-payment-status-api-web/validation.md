# Evidência de preparação

## Inventário somente-leitura — 2026-10-15, 19:49 UTC

- SSH validado: `ubuntu@132.145.193.169`, host `clearbudget-vnic`, projeto `/opt/markina-gallery`, checkout limpo `71be3b29659143293351968e15fb4886c2d72bf0`.
- Main remota: `200859a0df0a1943b8c09ddc0f8f206e54dec851`. O comparativo remove a migration 0081 e código implantado de entrega/autenticação; candidato ainda não publicável sem integração.
- API saudável: container `6c2e64582b0bc56d642f2a228ca0619ca8984ec7ff06e7b87f0c17c48aa47744`, imagem `sha256:1efd40743c34fbf31f2b435942a4e78a8f31501928ea02ab2e238f8ba9155279`.
- Web saudável: container `611f86c0d5159e3a7543cbdf7631b3c5f49c91d82884d42c0ace82e19e5dfc34`, imagem `sha256:6941be2068c9143f4a54331da2c9bac1511e8d1998b16986bfdbf631284ec560`.
- Hashes SHA256 de `app/main.py`, `app/auth.py` e `app/tenant_hosts.py` dentro da API iguais aos blobs Git de `71be3b2`. `APP_VERSION` da API = SHA completo desse commit.
- Consulta SQL em transação READ ONLY: `alembic_version = 20261014_0081`; nenhuma alteração de dados.
- API 8000 e web 3000 apenas internos; nginx Markina saudável publica somente `127.0.0.1:8080`. Domínio `https://markina.pickyourpic.com.br`. `/healthz`, `/api/health` e `/` retornam 200; `/api/admin/payment-communications` retorna 403 sem sessão.
- Manifesto ativo: compose base, overlay branding, raw-development, preview-adjustment, system-monitor e override externo system-monitor. Arquivo de ambiente identificado: `docker/.env.homolog`; nenhum valor foi registrado.
- Docker Compose 2.35.1. Configuração resolvida com APP_VERSION ativo produz hashes idênticos aos labels: API `8c68c183a87bfdc14ea473faf7612780184934bc010d93e363c21fa39a1334a1`; web `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05`.
- Diagnóstico do hash: `compose config --hash` usa `WithoutEnvironmentResolution` nesta versão e não resolve o `env_file` adicional da API. Calcular o hash passando a configuração JSON resolvida apenas em memória a `compose -f - config --no-interpolate --hash api,web` reproduz exatamente os labels, sem imprimir segredos ou criar arquivo. Não relaxar o gate por causa desse comportamento do Compose.
- Demais serviços Markina saudáveis; outros projetos Firefly, Nginx Proxy Manager e Portainer identificados e fora do escopo. Disco do host: 194 GiB total, 73 GiB livres (63% utilizado).
- `web-last-healthy.sha=faafe14…` é registro antigo, não versão atual comprovada; rollback usará os IDs de imagem acima.

## Estado

Somente leitura no servidor. Reconciliação Git e runbook em preparação local. Nenhum deploy, migration, envio de mensagem ou alteração de configuração executados.

## Validação da integração local

- Conflitos reconciliados em CI (preservada a origem Docker Hub validada no PR #188) e no cabeçalho do pedido (cores novas e referência agrupada já implantada preservadas).
- Regressão reproduzida: o teste do download passa com `confirmed` e falha com `confirmed_undelivered` antes da correção. Após admitir ambos os estados confirmados, a suíte frontend passou: 524 testes em 60 arquivos.
- `ruff check backend/app backend/tests`: aprovado.
- `openspec validate release-payment-status-api-web --strict`: aprovado; `openspec validate --specs`: 21 specs aprovadas, com avisos já existentes de requisitos longos.
- Blocos Bash do runbook analisados por `bash -n`: sintaxe válida; revisão de escopo confirma comandos explícitos para API/web e recarga apenas do nginx Markina.
- Diff contra `71be3b2` em migrations, Compose, Dockerfiles, manifests e lockfile de dependências: vazio. Código de runtime difere somente em `backend/app/main.py`, página de pagamentos, cores e badge da interface.
- `git diff --cached --check` informa apenas duas linhas em branco ao final de documentos da change de download, trazidas do commit já implantado; nenhuma reformatação desses artefatos foi feita.
- Testes locais direcionados de backend, typecheck/build/lint frontend e CI do PR ainda em andamento; não são declarados concluídos nesta revisão.
