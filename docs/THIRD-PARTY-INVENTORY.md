# Pick-your-Pic — inventário reconciliado de componentes externos

**Revisão:** 19/10/2026 · base de código `d06dcc7460b69188833a79e39a7b05fa694410ea` (confirmada com `git ls-remote origin refs/heads/main`).
**Escopo:** documentação e evidência datada. Nenhuma consulta remota ou alteração de produção foi realizada nesta change.

## Resumo executivo copiável

Foram organizados **72 itens rastreáveis** em unidades explícitas (pacotes, runtime, serviços, modelos, ferramentas e integrações). O primeiro inventário registrava 43 grupos mais agregados; a reconciliação de 19/10 tinha 68 itens. Em 24/10 foram acrescentados SDK, JS, ferramenta temporária e assets da integração Orders. A diferença numérica não equivale à criação de novos serviços.

| Área | Principais itens | Prioridade |
|---|---|---|
| Serviços que podem afetar acesso/cliente | Next/React, FastAPI, PostgreSQL, Redis, Nginx, Evolution, SMTP e push | Muito alta; Dependabot semanal em PR e alerts de segurança nativos assim que habilitados. |
| Motores e mídia | YuNet/SFace/OpenCV; EmbeddingGemma 2 + stack PyTorch; LightCraft/RawTherapee/Pillow | Revisão humana especializada. Sem PR/atualização automática de pesos ou recomendação de renderer. |
| Build e desenvolvimento | runtimes Python/Node, npm/pip/apt, Actions e tags/digests Docker | Dependabot agrupado semanal; validar lockfiles, reprodutibilidade, arquitetura e supply chain. |
| Oracle/runtime | evidências abaixo datadas; inspeção atual não realizada | Estado posterior à última observação fica não confirmado. Nunca inferir versão runtime somente de tag. |

### Gemma reconciliado

O inventário anterior estava incorreto ao descrever Gemma apenas como proposta. O código atual contém `backend/Dockerfile.gemma`, `gemma-requirements.txt`, modelo `google/embeddinggemma-2` na revisão `914f7f89142e33e77833254d9c9b90c3cef7303b`, service `face-gemma-index-worker` e configuração de monitoramento.

- **11/10/2026, evidência operacional de homologação em `openspec/changes/evaluate-embeddinggemma-face-search/validation.md`:** worker explicitamente iniciado, `healthy`, assets e marcador da revisão verificados, heartbeat/monitor recentes. A configuração global era SFace; havia zero jobs `index_gemma`/`search_gemma` e zero vetores Gemma. Portanto, essa evidência comprova runtime preparado e serviço saudável, **não** inferência nem adoção de Gemma.
- **19/10/2026, registro da publicação web-only em `openspec/changes/remediate-frontend-dependency-vulnerabilities/production-publication-2026-10-19.md`:** o inventário da Oracle listou 15/15 serviços ativos saudáveis, incluindo `face-gemma-index-worker`; a operação mudou somente `web` e preservou os IDs dos containers não web. Isso sustenta a presença/saúde histórica do serviço nesse host naquele horário, não estado posterior nem uso do modelo.
- `GemmaFaceEmbeddingProvider` carrega o modelo sob demanda na primeira chamada de embedding. O worker verifica arquivos/pesos locais na inicialização; o status `healthy` ou nome do container não prova que PyTorch carregou pesos na RAM ou executou uma inferência.
- O código bloqueia startup Gemma para `APP_ENV=prod|production`, enquanto o registro de produção acima lista o serviço no host chamado de produção. Registros anteriores identificam o host como `staging`/homologation. A configuração efetiva e a interpretação de ambiente não foram reconsultadas: há uma **divergência que precisa de leitura remota atual** antes de afirmar como o gate foi aplicado. Nenhum dado indica uso de Gemma por clientes.
- A inspeção atual da Oracle ficou pendente: não havia sessão SSH local apropriada. O workflow `inventory-homolog-readonly.yml` não verifica versão/runtime/modelo Gemma e ainda executa um container transitório de inventário; não foi acionado para não exceder a consulta estritamente observacional solicitada.

## Inventário técnico

`Declaração` vem do checkout/lockfile/configuração. `Produção` refere-se somente às evidências datadas acima; o runtime atual não foi consultado.

### A — Serviços críticos de produção e integrações

| # | Componente | Versão/declarado e fonte | Uso, criticidade e atualização |
|---:|---|---|---|
| 01 | PostgreSQL principal | `postgres:17-alpine`, Compose | Banco de negócio; crítico. Tag móvel sem digest; patch exige backup/smoke, major exige plano de upgrade. Oracle atual não confirmado. |
| 02 | PostgreSQL Evolution | `postgres:15-alpine@sha256:fe0737…`, Compose | DB isolado do WhatsApp. Fixado por digest, preservar schema compatível com Evolution. |
| 03 | Redis principal | `redis:7-alpine`, Compose | Filas/cache críticos; tag móvel. Compatibilidade/persistência e retomada de jobs antes de atualizar. |
| 04 | Redis Evolution | `redis:7-alpine@sha256:ff02b5…`, Compose | Cache/sessão do adaptador; digest declarado. |
| 05 | Nginx | `nginx:1.27-alpine`, Compose | Entrada pública/proxy. Tag sem digest; validar roteamento, TLS/body-size e healthchecks. |
| 06 | Evolution API | `evoapicloud/evolution-api:v2.3.7@sha256:1bd8af…`, profile `whatsapp-real` | Transporte WhatsApp/OTP. API, sessão e webhooks exigem regressão; perfil ativo só por evidência remota. |
| 07 | FastAPI | `>=0.115`, `backend/requirements.txt` | API de autenticação/negócio; faixa sem lock; atualização pode alterar contrato. |
| 08 | Uvicorn | `uvicorn[standard]>=0.30` | Servidor ASGI da API; testar ciclo de vida, timeouts e shutdown. |
| 09 | Next.js | range `^16.3.8`; lock `16.4.0`; imagem produção em evidência `16.4.0` | Frontend crítico. Produção confirmada no registro de 19/10; atualização exige CI web completo e release web-only autorizado. |
| 10 | React | `19.2.8`, npm lock | Renderização/UI; compatível com Next. Atualizar em conjunto e cobrir navegação/sessões. |
| 11 | React DOM | `19.2.8`, npm lock | Hidratação/renderização; risco de incompatibilidade com React/Next. |
| 12 | SMTP | `smtplib` stdlib + provider configurável | Verificação/recuperação. Servidor e versão do fornecedor não estão no Git; TLS/entrega devem ser verificados sem expor endereço/credenciais. |
| 13 | Adaptador WhatsApp | HTTP stdlib em `backend/app/messaging.py`; Evolution/API configurável | OTP e avisos. Provedor/runtime externo sem versão confirmada no checkout. |
| 14 | Web Push/VAPID | pywebpush e endpoints de browsers | Avisos por dispositivo; política do gateway/browser varia. Chaves não são inventariadas. |
| 15 | PIX/provedor | PIX manual | Pagamento por conferência manual; nenhum SDK de pagamento foi identificado no fluxo atual. |
| 16 | Google Photos | link manual por pedido | Entrega é link inserido pelo fotógrafo; sem API/álbum automatizado. |

### B — Motores especializados

| # | Componente | Versão/declarado e fonte | Uso, criticidade e atualização |
|---:|---|---|---|
| 17 | YuNet detector | `face_detection_yunet_2023mar.onnx`; OpenCV Zoo commit `47534e27…`; SHA-256/licença no manifest | Detector facial; atualização altera detecção e exige calibração. |
| 18 | SFace recognizer | `face_recognition_sface_2021dec.onnx`; mesmo commit; SHA-256, Apache-2.0 | Embeddings SFace; troca requer reindexação/avaliação e versão própria. |
| 19 | OpenCV Zoo | Pesos por URL de commit fixo em `backend/facial-assets/model-manifest.json` | Origem upstream dos pesos; avanço de `main` não implica candidato seguro. |
| 20 | OpenCV Headless | `4.12.0.88`, imagem facial | Runtime de inferência em CPU; ABI/ARM e precisão exigem teste específico. |
| 21 | NumPy | `2.2.6`, imagem facial | Base numérica do motor; ABI/performance ligada a OpenCV/PyTorch. |
| 22 | EmbeddingGemma 2 | `google/embeddinggemma-2`, 768 dimensões | Modelo experimental de embedding facial; não recomendar troca de SFace sem benchmark anotado autorizado. |
| 23 | Revisão dos pesos Gemma | `914f7f89142e33e77833254d9c9b90c3cef7303b`, constante no provider e marcador asset | Revisão imutável Hugging Face. Somente acompanhar drift; nunca PR automático de pesos. |
| 24 | PyTorch CPU | `torch==2.14.1`, instalação explícita no Dockerfile Gemma | Inferência CPU, alto uso de RAM/CPU; atualização requer smoke isolado e teste de segurança. |
| 25 | Torchvision | `0.29.1`, Dockerfile Gemma | Processor de imagem Gemma; manter par compatível com PyTorch. |
| 26 | sentence-transformers | `6.1.0`, `gemma-requirements.txt` | Carregamento/embedding Gemma; alto impacto e licença/dependências transitivas. |
| 27 | Transformers | `5.19.0`, `gemma-requirements.txt` | Runtime de modelo; major/minor exigem inferência e compatibilidade do processor. |
| 28 | Hugging Face Hub | `1.31.0`, `gemma-requirements.txt` | Aquisição de pesos no build; runtime fica offline. Mudança de revisão não é atualização de biblioteca. |
| 29 | LightCraft | `0.6.0`, SHA-256 por arquitetura no Dockerfile RAW | Conversão RAW opt-in; alteração de cor/formato/câmera e comportamento CLI requer corpus/comparação visual e licença. |
| 30 | RawTherapee RAW | `5.9-1+b1`, pin apt no worker RAW | Conversor RAW alternativo; validar formatos/câmeras, render e rollback. |
| 31 | RawTherapee preview | pacote `rawtherapee` sem pin em `Dockerfile.preview-adjustment` | Ajuste opcional de prévia; apt móvel e saída visual podem variar. |
| 32 | Pillow | `Pillow>=10.0` | Derivados, EXIF e imagem; faixa aberta, atualizar com teste de bytes/dimensões/metadados. |
| 33 | Fontes DejaVu | pacote apt `fonts-dejavu-core` | Render de texto/previews; licença e métricas alteram output. |

### C — Dependências e runtimes da aplicação

| # | Componente | Versão/declarado e fonte | Uso e cuidado |
|---:|---|---|---|
| 34 | Python | `3.13-slim`; workers também `3.13-slim-bookworm`; CI Python 3.13 | API/worker. Pin de minor, tag de imagem mutável; confirmar patches e wheel/ARM. |
| 35 | Node.js | `node:24-alpine`; runner produção Node `v24.22.0` em 19/10 | Frontend; tag não fixa patch/digest; versão runtime confirmada só naquela evidência. |
| 36 | SQLAlchemy | `>=2.0` | ORM/persistência/locks; compatibilidade transacional e migrations. |
| 37 | psycopg[binary] | `>=3.2` | Driver PostgreSQL; compatibilidade SSL/ARM. |
| 38 | Pydantic Settings | `>=2.7` | Configuração/env; mudanças de parsing afetam boot/secrets. |
| 39 | Alembic | `>=1.14` | Migrations; atualização não autoriza executar migration; validar cadeia separadamente. |
| 40 | cryptography | `>=44.0` | Segredos e cifragem; wheel/OpenSSL/ARM e formatos criptográficos. |
| 41 | argon2-cffi | `>=23.1` | Hash de senha; parâmetro/custo e wheel precisam manter compatibilidade. |
| 42 | pyotp | `>=2.9` | TOTP; preservar vetores/protocolo. |
| 43 | qrcode[pil] | `>=8.0` | QR do PIX; geração/export. |
| 44 | redis-py | `>=5.2`; worker facial `6.4.0` separado | Cliente Redis; versões diferentes entre imagens precisam ser rastreadas. |
| 45 | pytest | `>=8.3` | Testes backend. |
| 46 | httpx | `>=0.27` | Cliente/testes de API. |
| 47 | Ruff | `>=0.9` | Lint Python. |
| 48 | pywebpush | `2.5.0` | Envio push; dependência pinada. |
| 49 | py-vapid | `1.9.4` | Assinatura VAPID; compatibilidade criptográfica. |
| 50 | http-ece | `1.2.1` | Cifragem push. |
| 51 | requests | `2.34.2` | Transporte Web Push. |
| 52 | aiohttp | `3.14.3` + transitivos fixados | Transporte async push; cadeia transitiva monitorada no requirements. |
| 53 | TypeScript | `6.0.3`, npm lock | Tipagem; verificar Next/React. |
| 54 | ESLint / eslint-config-next | `9.39.5` / `16.4.0`, lock | Lint; integrar majors compatíveis; alertas de dev não devem induzir downgrade. |
| 55 | Vitest / jsdom / Testing Library | `4.1.11`, `30.0.1`, faixas package.json e lock | Teste frontend; runtime de desenvolvimento. |
| 56 | @fontsource-variable | 4 famílias `5.3.0`, npm lock | Tipografia embarcada no frontend. |

Outros pacotes diretos backend e todos os lockfile transitivos continuam representados nas fontes de inventário (`requirements*.txt`, `package-lock.json`); esta tabela destaca os componentes por criticidade e agrupamento funcional, não duplica centenas de transitivos.

### D — Infraestrutura e desenvolvimento

| # | Componente | Versão/declarado e fonte | Uso e cuidado |
|---:|---|---|---|
| 57 | actions/checkout | `@v4` | Checkout CI; tag major móvel, Dependabot abre PR sob revisão. |
| 58 | actions/setup-python | `@v5` | Runtime CI Python 3.13. |
| 59 | actions/setup-node | `@v4` | Runtime CI Node 24. |
| 60 | GitHub-hosted runner | `ubuntu-latest` | CI e monitor; imagem do runner é móvel, sem snapshot runtime. |
| 61 | Docker Engine/Buildx/Compose | usado por CI/scripts | Build e operação; versão local/Oracle atual não confirmada. Não executar docker no workflow de monitoramento. |
| 62 | npm | lock v3 e `npm ci` | Resolução frontend; atualizar manifest + lock com testes. |
| 63 | pip | instala `requirements*.txt` sem lock do app | Pode resolver versões diferentes em rebuild; candidato a lock/SBOM futura, fora deste upgrade. |
| 64 | apt / Debian Bookworm | pacotes de sistema sem snapshot global | APT sem pin pode mudar imagem nativa; conferir ABI/licenças por arquitetura. |
| 65 | Alpine Linux | sufixo de imagem Nginx/Node | Base móvel; tags/digest e patches entram pela atualização Docker. |
| 66 | curl/procps | pacotes apt nos Dockerfiles | Healthchecks e gerenciamento de processo; cadeia OS. |
| 67 | DigiKam/XMP | protocolo/export do fotógrafo e parser interno | Nenhum cliente/versão do DigiKam declarados; cobrir variantes XMP nas fixtures. |
| 68 | Google Drive/OCI/GitHub APIs | backup/arquivo previstos, host Oracle e APIs de monitoramento | Não foi encontrado SDK Google Drive no app; serviço real e agent/CLI OCI não confirmados. API GitHub usada pelo relatório só leitura. |

### Adição em desenvolvimento — 24/10/2026

Esta adição da change `add-mercadopago-orders-checkout` acrescenta dois componentes de integração, uma ferramenta temporária de desenvolvimento e assets de identificação ao inventário anterior de 68 itens, totalizando 72. Não altera a evidência histórica de produção acima.

| ID | Componente e origem | Versão / licença / ativação | Consumidor e validação |
|---|---|---|---|
| 69 | [SDK Python oficial Mercado Pago](https://github.com/mercadopago/sdk-python), distribuição PyPI `mercadopago` | `==3.6.0`, MIT, versão estável conferida em 24/10/2026; instalação autorizada pelo proprietário. | Orders API e consulta de conta no backend. Instalado apenas no venv isolado; transporte limitado, timeout 15s, sem retries de criação. Contratos locais e operações externas com credencial verificada de teste: criação/GET/busca/cancel/refund. Nenhuma execução em produção. |
| 70 | [MercadoPago.js V2](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/cards) em `https://sdk.mercadopago.com/js/v2` | Versão pública V2 do serviço, conteúdo móvel do provedor; termos Mercado Pago e aplicação própria por tenant; sem cópia local de código do provedor. | Card Payment na tela Next.js /library/checkout. Montagem/tokenização oficiais comprovadas em Edge 390 px, com APRO/FUND/CONT e resposta perdida. Matriz visual 390/768/1440 claro/escuro permanece explicitamente sintética. Evidência: external-validation.md da change. |
| 71 | [cloudflared 2026.10.3](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.3), ferramenta temporária de desenvolvimento | Origem oficial Cloudflare, Apache-2.0; SHA-256 `76b2805253d0d6ffacb092a7acfbee99e7af6917835c0c5410e23f3ef5052da2` confrontado com o digest oficial do release. Binário local ignorado, sem instalação de serviço/ativação produtiva. | Somente ensaio externo Orders em 24/10/2026, autorizado pelo proprietário. Gateway restrito ao callback de teste, duas entregas genuínas comprovadas. Túnel encerrado; não integra imagens/runtime da aplicação nem cria DNS/firewall. URL efêmera, sem SLA; nunca reutilizar como endpoint de produção. |
| 72 | Assets de identificação Pix/Mercado Pago; fontes primárias do provedor/participante em `frontend/public/payments/README.md` | SVGs estáticos originais, obtidos em 24/10/2026; direitos de marca dos titulares, uso limitado à identificação de pagamentos; sem biblioteca ou serviço novo. | Thumbnails locais no carrinho e nos métodos do checkout; preservadas proporções, contraste/base branca e texto acessível. Sem scripts, eventos ou referências externas. 24 capturas locais sem overflow/imagens ausentes; não interfere em autorização/estado financeiro. |

Pagamentos são críticos: upgrade futuro exige contratos Orders, SDK, HMAC, idempotência, migração e regressão de PIX/tenant. Chave mestra permanece externa; nenhum segredo ou teste de cobrança real faz parte deste inventário. Verificação de alerts de segurança das contas/registries não foi executada nesta adição.

## Evidência runtime e proveniência conhecida

| Data/ambiente | Evidência | O que comprova / não comprova |
|---|---|---|
| 11/10/2026, homologação privada | `openspec/changes/evaluate-embeddinggemma-face-search/validation.md`: worker Gemma healthy, assets da revisão fixada verificados, monitor/heartbeat recente, engine global SFace, zero jobs e vetores Gemma. Imagem dedicada reportada `sha256:0fc14ad1…`. | Preparação e processo healthy. Não prova inferência Gemma; código carrega o encoder sob demanda. |
| 19/10/2026 08:08 BRT, host descrito como produção | `openspec/changes/remediate-frontend-dependency-vulnerabilities/production-publication-2026-10-19.md`: 15/15 serviços saudáveis; serviço Gemma e RAW/preview/Evolution presentes; somente `web` substituído. Node `v24.22.0`, Next `16.4.0`, sharp `0.35.5`, web image `sha256:6aef1935…`, checkout web `4b464f081dfa2451472848622853460398834e6d`. | Runtime web e serviço enumerado naquele horário. Não prova versões de binários de outros serviços, uso do Gemma ou que o estado permaneça igual depois da observação. |
| 19/10/2026, HEAD atual de `main` | `d06dcc7460b69188833a79e39a7b05fa694410ea`, remote confirmado; includes documentação adicional à revisão de publicação web. | Linha de código atual. Não prova qual SHA está atualmente em execução na Oracle. |

**Estado presente da Oracle:** não confirmado. Nenhuma consulta remota foi iniciada porque não há sessão SSH local; não foram lidos tokens/secrets. A API de Dependabot do repositório também respondeu em 19/10 que Dependabot alerts estão desabilitados; requer ação do proprietário nas configurações de Security. A configuração de atualização semanal pode abrir PRs após integração, mas alertas de segurança e seus security PRs só funcionarão após habilitação. Não contornar escopo/token nem chamar endpoint de escrita.

## Fontes e políticas de acompanhamento

- npm/pip/Dockerfile/Compose/GitHub Actions: Dependabot nativo semanal, grupos minor/patch e major, limite de PRs, sem automerge.
- Dependabot alerts/security updates: fonte GitHub, consulta nativa de segurança mais frequente/acionada por advisory. Status atual desabilitado; pendência de owner action.
- LightCraft e RawTherapee: GitHub Releases consultado semanalmente; só relatório/avaliação manual, sem PR automático de motor.
- EmbeddingGemma: Hugging Face model metadata revision consultada semanalmente; drift vira candidato de revisão, nunca PR automático de pesos.
- Toda falha, fonte não disponível, falta de permissão ou lista vazia fica distinguível no job summary. O relatório não assume que ausência de PR significa ausência de updates no upstream ou que uma tag corresponda ao runtime.
