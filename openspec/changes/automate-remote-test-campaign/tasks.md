# Tasks

## 1. Revisão e prontidão remota

- [x] 1.1 Revisar e aceitar os artefatos desta change antes de código ou execução. Evidência: em 08/10/2026 o proprietário autorizou a campanha, provisionamento sintético, secret store, OTP isolado e limites baixos; a autorização de deployment continua separada.
- [x] 1.2 Confirmar acesso read-only ao host de homologação por canal seguro e a versão/schema vigentes sem revelar credenciais. Evidência: SSH autorizado, revisão publicada `d4d000de3b41d4b2c7c96197cfea28b7940c5aea`, Alembic `20261001_0071 (head)`, serviços Markina saudáveis e portas de DB/Redis/Evolution não publicadas; nenhum valor de credencial foi exibido.
- [ ] 1.3 Provisionar ou identificar contas e registros sintéticos independentes, sem reutilizar contas/sessões do ensaio A+B.
- [x] 1.4 Confirmar a origem e o hash do diretório sintético candidato; validar MIME/dimensões e preservar os arquivos de origem. Recusar lotes de proveniência não confirmada. Evidência: o verificador read-only aceitou 36 arquivos byte a byte compatíveis com `pilot_fixture.py` e recusou 36 sem correspondência; todos os aceitos são JPEG 256×192. Manifesto agregado SHA-256 `58f2bacb360d463267a3ea6ddc2cbc177c7fd3ef5d634d32cbc2ed3a86d2b8d0`; 15 testes de mídia e policy passaram, e o teste de symlink foi ignorado por indisponibilidade de criação de symlink no host. Nenhum original foi modificado.
- [x] 1.5 Aprovar e preparar secret store separado para credenciais TOTP e runner; não registrar credenciais nos artefatos. Evidência: ambiente GitHub `homolog-tests` separado de `homolog`, com proteção de reviewer/branch; duas credenciais independentes de fotógrafos sintéticos foram geradas e salvas como secrets do ambiente. Valores não foram impressos nem registrados.
- [ ] 1.6 Aprovar canal de OTP sintético, isolado do provider real e com leitura de uso único; documentar falha fechada e desativação.
- [x] 1.6.1 Implementar o sink efêmero, criptografado, tenant-allowlisted, disabled-by-default e de consumo atômico, sem provider/fallback externo. Evidência: `remote_test_otp.py` usa AES-GCM, TTL Redis de 600 s, `GETDEL` por geração do challenge, segredo compare-digest, `APP_ENV=homolog` e allowlist; reenvio invalida a geração anterior; chamadas normais não ativam o sink. 6 testes unitários e `py_compile` passaram.
- [ ] 1.6.2 Configurar segredo/allowlist no secret store de homologação e publicar o código após autorização operacional explícita; verificar em servidor que o fluxo não cria entrega WhatsApp.
- [x] 1.7 Definir limites por perfil para smoke e carga gradual, thresholds, duração, rampas e condições de parada; manter estresse/soak bloqueados até autorização específica. Evidência: perfil exclusivamente read-only configurado com 1 VU, teto 1 req/s, alvo conservador 0,5 req/s, 30 s estáveis, rampas 5 s, máximo planejado 19 requests e parada automática para erro, checks, dropped iterations e p95/p99 acima dos limites. Stress/soak seguem inelegíveis.

## 2. Harness funcional remoto

- [ ] 2.1 Reaproveitar pytest, Vitest e Python Playwright, separando fixtures, identidades e sessões por conta.
- [x] 2.2 Bloquear hosts fora da allowlist de homologação e verificar no preflight que nenhum serviço de aplicação local será iniciado. Evidência: `remote_campaign_policy.py` valida a origem exata; os workflows rodam em runner hospedado sem iniciar serviços; 14 testes unitários de policy passaram em 08/10/2026.
- [ ] 2.3 Implementar jornadas de login OTP/TOTP, leitura de galerias/pastas/prévias, seleção/desmarcação e negativas cruzadas somente com dados sintéticos.
- [ ] 2.4 Reutilizar apenas a mídia sintética validada, executar envio apenas quando previsto e verificar preservação do hash de origem.
- [x] 2.5 Bloquear pagamentos, mensagens externas, exclusões, configurações, biometria e demais operações não autorizadas antes do request. Evidência: o allowlist remoto só admite `GET /healthz` e `GET /api/health`; policy recusa auth, pagamentos, mutações, biometria e query strings; Playwright aplica a validação de URL completa antes de continuar a rota, e k6 só usa GET nos dois health endpoints.
- [ ] 2.6 Produzir screenshot, logs e traces sanitizados em armazenamento temporário protegido; verificar ausência de segredos/PII nos artefatos publicados.

## 3. Harness de carga HTTP/API

- [x] 3.1 Fixar versão do k6 e adicionar cenários para os fluxos HTTP/API aprovados. Evidência: runtime v0.54.0 obtido em área temporária, versão verificada e `k6 inspect` validou o cenário read-only. Execuções remotas limitaram-se a health endpoints; fluxos autenticados seguem bloqueados pelo gate OTP.
- [ ] 3.2 Implementar um perfil separado por VU/identidade, cookie jar isolado, allowlist de host e limites definidos em configuração revisável.
- [ ] 3.3 Implementar smoke, carga esperada, pico, estresse e estabilidade, mantendo inelegíveis os perfis sem limites ou autorização.
- [ ] 3.4 Adicionar thresholds e parada automática para erros, latência, healthcheck e recursos/filas cobertos; nunca elevar limites após falha.

## 4. Relatórios, execução e encerramento

- [ ] 4.1 Integrar leituras `capacity-report/v1` antes/durante/depois por operador autorizado, registrando cache e timestamps sem dados por fotógrafo.
- [ ] 4.2 Integrar métricas host somente por fonte read-only autorizada e escopada à Markina; marcar indisponibilidades explicitamente.
- [x] 4.3 Gerar relatório por execução com SHA, ambiente, perfil, VUs, duração, operações/s, p50/p95/p99, erros, checks, métricas, evidências, limitações e recomendação. Evidência: gravador/agregador smoke sanitizado e resumo k6 passam testes Vitest; o runtime v0.54.0 foi validado e gerou resumos remotos efêmeros sem segredos. Um perfil completou 18 requests a 0,5 req/s com p50/p95 válidos; p99 foi corretamente sinalizado ausente e as execuções intermitentes pararam por thresholds. O agregador agora inverte corretamente a Rate `http_req_failed`, informa VUs descartados, versão e estado dirty.
- [x] 4.4 Executar primeiro preflight remoto read-only; aguardar fim informado do ensaio A+B antes de qualquer request de campanha. Evidência: inventário SSH read-only identificou versão/schema e isolamento de portas; o proprietário confirmou fechamento do A+B antes de tráfego da campanha.
- [ ] 4.5 Executar smoke remoto aprovado, diagnosticar a automação em caso de falha e repetir somente etapas seguras; avançar gradualmente dentro dos limites aprovados.
- [ ] 4.6 Revisar relatório, diff, segredos e artefatos; registrar aprovação humana final antes de sincronizar specs ou arquivar.
