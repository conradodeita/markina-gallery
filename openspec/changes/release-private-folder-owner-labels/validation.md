# Validação e continuidade

## Inventário atualizado somente-leitura

- Host `clearbudget-vnic`, checkout limpo `/opt/markina-gallery`, SHA `b4f15abd6a71585082758062feba7fcfcc225587`, Alembic `20261017_0084`.
- Domínio `https://markina.pickyourpic.com.br`, Nginx Markina em `127.0.0.1:8080`; API, web, worker OTP, workers faciais, Redis, banco e Evolution saudáveis. `/api/health` respondeu HTTP 200.
- Wrapper instalado `root:root 0755`, SHA-256 `5172e31e89862b7ba585c5936099987eab39262ffe4475a5a5d1ad4f1bd62bf0`; ele já suporta comandos app, mas o pin do script app ainda é o anterior. Acesso SSH operacional e sudo não interativo foram confirmados sem mutação.
- Outros projetos inventariados incluem Firefly, Proxy Manager e Portainer; seus recursos ficam fora dos comandos de release.

## Validação local integrada

- Classificador: 11 testes aprovados, incluindo grafo Git real, baseline, app, facial, mixed e ausência de runtime.
- App scope: 6 testes aprovados, incluindo blobs exatos, arquivos fora do escopo e testes frontend explicitamente permitidos.
- Simulação Git Bash de inventário, release e rollback API/web aprovada; schema divergente recusado no preflight e no release sem mutação. Worker e Alembic não são chamados.
- Política de produção e política de homologação aprovadas; Ruff aprovado.
- OpenSpec na versão fixada pelo CI (1.14.0): `validate --all --strict`, 118 aprovados e zero falhas. A versão local 1.14.1 adiciona warnings estritos em artefatos preexistentes; nenhum deles foi reescrito nesta change.

## Integração

- Preservada a proteção de ancestralidade somente-leitura da linha `main` no script app e os testes correspondentes; preservados os runtimes de produto já instalados de `develop` e o commit original da PR #220.
- A política de CI reconhece `auth.py` idêntico ao baseline instalado, preservando o fix OTP. O manifesto facial não é reescrito, e o gate app continua recusando alterações em runtime facial após o baseline.
- Publicação ainda pendente: concluir commit candidato, conferir diff real, executar CI e preflight protegido antes de qualquer recriação de serviços.

## Candidato reconciliado

- Merge `0be3e44` preserva os SHAs originais de `main`, do servidor e da PR #220 como ancestrais.
- Execução real do classificador: `release_scope=app`, base `b4f15abd6a71585082758062feba7fcfcc225587`.
- Execução real do gate app desde o SHA instalado: `app_release_ready=true`, critério `somente_api_web`. O diff de publicação não contém migrations, Docker/Compose, workers nem runtime facial dedicado.
