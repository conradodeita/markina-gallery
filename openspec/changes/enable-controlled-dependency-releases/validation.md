# Evidências e continuidade

## Oracle — coleta atual em 20/10/2026

Coleta SSH somente leitura em 16:25:07 UTC (13:25:07 BRT), após o proprietário informar a identidade SSH já autorizada. A tentativa anterior de autenticação padrão falhou; não foi contornada. Nenhum segredo, mapa de ambiente, log ou dado de cliente foi consultado. O coletor inicial precisou usar `index` para Health opcional do migrate parado; nenhuma aplicação foi alterada.

- Host e todas as imagens: Linux ARM64 (`aarch64`/`arm64`).
- Checkout: `4b464f081dfa2451472848622853460398834e6d`.
- API declara APP_VERSION `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`, coerente com o histórico de release; web-current.identity associa o checkout acima ao ID web observado.
- 15 serviços running/healthy; migrate histórico exited, preservado.
- Web instalado: Next 16.4.0, React/React DOM 19.2.8.
- Os oito consumidores Python abaixo têm aiohttp 3.14.3, multidict 6.8.0, urllib3 2.7.0, yarl 1.24.5.
- Imagens próprias têm RepoDigests vazio: os IDs abaixo são IDs Docker de conteúdo, não digests de registry. Nginx/DB/Redis/Evolution foram apenas inventariados e não são candidatos.

| Serviço ativo candidato | ID de imagem anterior observado |
|---|---|
| web | sha256:6aef1935d8a4ba4bfc125a1bf5bea52ae6e26db361ef4942a1fedc55c4efc20a |
| api | sha256:afc54e0ff0b008ac7bcc2ab28095f279da6213aaa5bec1ac98fae8269fc0715c |
| worker | sha256:25067618cf99f3b662f9096fc2f7aa88bcf272da5b2ea62dd91d9de9bd8d3b21 |
| face-search-worker | sha256:5c783d14d9714a89dc4ecde53878c81b5bc82f87788d5cdafad6a9d5475847c2 |
| face-index-worker | sha256:3f127a03e2c7336c62532ad1febdca1de38bf2c40373bb6081b24ca884a5f388 |
| face-maintenance-worker | sha256:0bdc5fec10352c85cbfd6e8e6dba6fe7065f36d47c5e39fbc6a6be0334443381 |
| face-gemma-index-worker | sha256:d353c1a5afc82a39c741ef034fb58c10af4cc3d38dff4340da4a63c00163f597 |
| preview-adjustment-worker | sha256:4d17f0b3f06a904a6b985ae018322cf28b114c64bc9711467b5b18020e24ce60 |
| raw-development-worker | sha256:8bb5cff143069e15e1426ae7f60cc0a564c1b9320ee0d4b69fbdb054bb368449 |

## Escopo e gates

O delta de checkout 4b464f para main inicial 48e8778 afeta só package.json/lockfile web e requirements-push runtime, além de infraestrutura/docs/testes. Cinco Dockerfiles Python consomem requirements-push através de requirements.txt. API/worker são serviços distintos mesmo compartilhando definição de build. migrate/seed-admin não devem ser executados.

O plano web sobre o inventário real passou na análise de árvore/contexto: árvore frontend `5da848c893b4e7b263531b94147e1a74c2bd67b3`, requisitos Python pendentes explicitamente separados da versão API. A verificação do Compose resolvido será repetida pelo inventário operacional; análise offline não substitui esse fingerprint.

O grupo Python permanece bloqueado: o executor pinado atual cobre somente api/web; não oferece rollback do worker nem dos seis workers especializados ativos. Nenhum gate facial/app foi afrouxado. A classificação própria de dependências não satisfaz as condições de deploy automático. Não há imagens candidatas publicadas pelo CI; versões declaradas não são comprovação de imagem na Oracle.

## Validação local e integração

- `python scripts/test_dependency_release.py -v`: 19 testes aprovados; os cinco cenários obrigatórios, includes/constraints, referências ausentes/não copiadas, contextos extras, symlinks, inventário inválido e helper shell real.
- `python scripts/test_classify_prod_release.py`: 13 testes aprovados; `test_prod_app_release_scope.py`: 11 aprovados.
- Políticas `test_production_release_workflow_policy.py` e `test_deploy_prod_web_policy.py`: aprovadas. OpenSpec strict e `git diff --check`: aprovados.
- Regressões locais de estado: a primeira execução delimitou dois problemas de fixture Windows (payload HTTP CRLF e caminho POSIX do overlay usado pelo Python nativo). Ambos foram corrigidos e os testes focados passaram. Nenhum gate de produção foi removido. A suíte completa Linux continua obrigatória no CI.
- Nova coleta real às 16:49:10 UTC confirma checkout, versões e 15 serviços saudáveis. Plano web passa sem autorização de release; plano Python retorna código 1 com oito bloqueios nominais e exclui migrate/seed-admin.
- Revisão manual do diff: contextos/COPY/includes, proveniência, autorização, snapshots, lock/rollback, workflows e arquivos sem versões alteradas. Não há mudança de dependências, Compose, Dockerfiles ou pins do wrapper. A tentativa do conector Code Review retornou `Connect your GitHub account to continue`; revisão externa por esse conector não foi realizada. A main exige seis checks, strict e enforce_admins; configuração exige zero aprovações humanas. Nenhum bypass será usado.
- PR de integração: https://github.com/conradodeita/markina-gallery/pull/256. Checks, revisões, SHA de merge e CI pós-merge são evidências externas consultáveis no próprio PR. As tarefas de integração/coleta final só podem ser concluídas depois desses eventos; a implementação não os presume.

Os testes de estado simulam fronteiras externas; a nova política possui testes separados com históricos Git reais e invocação real do helper shell. Os ajustes de fixture não mudam pins de produção. Resultados finais de CI/integração e comparação somente leitura serão registrados no PR antes do relatório final.

Manutenção proporcional: a comparação ampla de backend do web-only foi substituída pelo gate de proveniência explícito; gates de identidade, snapshot, lock e recuperação foram preservados. Não há remoção segura adicional na área afetada. Não sincronizar/arquivar specs sem revisão humana.
