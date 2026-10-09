# Execução da campanha remota

## Runner e comandos

Os workflows executam em runner hospedado e não iniciam backend, frontend, banco ou worker. Um runner autorizado também pode executar k6 diretamente, desde que use `v0.54.0`, passe o preflight, defina todos os limites abaixo e envie tráfego somente para `https://markina-homolog.duckdns.org`. Não é necessário iniciar uma cópia local da aplicação.

O proprietário confirmou que o ensaio A+B foi encerrado e autorizou finalizar as ações nos dois perfis sem registrar seus resultados. Portanto, trate o gate A+B como fechado para futuras campanhas independentes; não consulte nem registre resultados daquele ensaio. O smoke read-only anterior consumiu seu limite de três requests. Um novo teto baixo para o perfil health foi aprovado e configurado no ambiente protegido `homolog-tests`; não amplie-o após falha.

No repositório GitHub, depois de configurar e aprovar os gates abaixo, iniciar o smoke com:

```powershell
gh workflow run remote-test-smoke.yml
```

O workflow realiza sequencialmente uma consulta Vitest a `/api/health`, uma navegação Playwright a `/api/health` em contexto efêmero e uma consulta pytest a `/healthz`. O limite total configurado é exatamente três requests read-only. Se uma etapa falhar, as etapas seguintes não são iniciadas.

Depois de smoke aprovado em execução autorizada e limites do perfil aprovados, iniciar carga de health endpoints com:

```powershell
gh workflow run remote-test-capacity.yml -f profile=expected
```

O perfil `peak` só deve ser escolhido quando seus limites próprios estiverem aprovados. O workflow k6 não autentica usuários e não mede galerias, seleções nem capacidade multi-tenant. Seu relatório registra métricas de servidor como indisponíveis até que a integração read-only seja autorizada e implementada.

## Configuração de homologação

O ambiente protegido GitHub `homolog-tests` foi criado com revisores requeridos conforme governança do repositório. Credenciais sintéticas e limites ficam ali, separados de `homolog`; não copiar valores de credenciais para `vars`, arquivos ou logs. O ambiente `homolog` e seus secrets de deploy não foram modificados.

Variáveis para o workflow smoke:

- `PYP_REMOTE_TARGET_URL`: origem exata `https://markina-homolog.duckdns.org`.
- `PYP_SMOKE_AUTHORIZED`: `1` somente após autorização operacional do smoke.
- `PYP_SMOKE_AUTHORIZATION_REFERENCE`: referência não secreta da autorização.
- `PYP_AB_TEST_CLOSED`: `1` somente após confirmação de que o ensaio A+B terminou.
- `PYP_SMOKE_MAX_REQUESTS`: `3`.

Variáveis do perfil k6, definidas somente após aprovação para cada execução/perfil:

- `PYP_CAPACITY_APPROVED`: `1` após autorização operacional.
- `PYP_CAPACITY_AUTHORIZATION_REFERENCE`: referência não secreta da autorização.
- `PYP_CAPACITY_MAX_VUS`, `PYP_CAPACITY_MAX_RPS`, `PYP_CAPACITY_TARGET_RPS`, `PYP_CAPACITY_DURATION_SECONDS`, `PYP_CAPACITY_RAMP_UP_SECONDS` e `PYP_CAPACITY_RAMP_DOWN_SECONDS`: limites aprovados; o alvo não pode ultrapassar o teto, e o tempo somado tem teto técnico de 1200 segundos.
- `PYP_CAPACITY_THRESHOLDS_JSON`: objeto JSON com arrays de thresholds k6. Cada threshold aborta a execução após avaliação de um segundo.
- `PYP_AB_TEST_CLOSED`: `1` somente depois do ensaio A+B.

Os workflows falham fechados quando variável obrigatória falta ou não corresponde ao gate. A confirmação de encerramento de A+B já foi recebida, mas isso não substitui autorização/teto para uma nova execução, não fornece contas sintéticas nem autoriza carga.

## Identidades e mídia

Os workflows smoke e capacidade consultam somente health endpoints e não precisam de conta. Dois fotógrafos sintéticos independentes foram provisionados, e suas senhas/TOTP estão no secret store `homolog-tests`. O sink OTP de uso único está implementado localmente, mas continua desligado e não publicado no servidor; jornadas autenticadas permanecem bloqueadas até autorização operacional para configurar segredo/allowlist e implantar o código em homologação.

Para reproduzir o perfil k6 atual a partir de um runner autorizado, com k6 v0.54.0 instalado e sem gravar segredos em histórico:

```powershell
$env:PYP_REMOTE_TARGET_URL = 'https://markina-homolog.duckdns.org'
$env:PYP_REMOTE_ENVIRONMENT = 'homolog'
$env:PYP_PROFILE = 'expected'
$env:PYP_OWNER_APPROVED = '1'
$env:PYP_AUTHORIZATION_REFERENCE = '2026-10-08-synthetic-health-profile'
$env:PYP_AB_TEST_CLOSED = '1'
$env:PYP_MAX_VUS = '1'
$env:PYP_MAX_RPS = '1'
$env:PYP_TARGET_RPS = '0.5'
$env:PYP_DURATION_SECONDS = '30'
$env:PYP_RAMP_UP_SECONDS = '5'
$env:PYP_RAMP_DOWN_SECONDS = '5'
$env:PYP_THRESHOLDS_JSON = '{"http_req_failed":["rate==0"],"checks":["rate==1"],"dropped_iterations":["count==0"],"http_req_duration":["p(95)<1500","p(99)<3000"]}'
$env:PYP_SOURCE_REVISION = (git rev-parse HEAD).Trim()
$env:PYP_SOURCE_WORKTREE_DIRTY = '1'
k6 run .\k6\remote-campaign.js
```

O perfil atual planeja no máximo 19 requests. Uma execução concluiu 18; repetições recentes pararam automaticamente por `dropped_iterations`. Esse resultado mede somente health endpoints, não capacidade máxima nem multi-tenant.

O diretório de mídia candidato contém 36 arquivos que correspondem ao fixture sintético conhecido e 36 sem proveniência confirmada. Usar somente os 36 validados depois que um fluxo de mídia estiver aprovado; nunca transmitir o restante. Os hashes devem ser recalculados antes do uso e comparados ao manifesto fornecido na validação.

Para revalidar a pasta sem iniciar serviços e sem modificar arquivos, a partir de `backend/`:

```powershell
python -m tests.synthetic_media <pasta-de-midia>
```

O comando imprime apenas contagens, MIME, dimensões, hash agregado e indicador de preservação. O manifesto em memória contém hashes por arquivo apenas para o código consumidor e não escreve arquivos auxiliares na pasta de origem.
