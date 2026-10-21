# Gates do release emergencial InfinitePay — 21/10/2026

## Autorização e limites

O proprietário autorizou correção restrita dos gates do PR #260, inventário Oracle somente leitura, testes e novo CI. Esta missão não autoriza merge, deploy, restart, migration, provisão de credenciais ou mudança de pagamentos. Não modificar #261/#262. A autorização anterior de operação foi substituída por estes limites.

## Inventário observado, sem alteração remota

Consultas SSH com chave local e host verificado; `git status` com locks opcionais desabilitados; Docker inspect com saída filtrada; leitura dos recibos; consulta Alembic current e metadados de pacotes com bytecode desabilitado. Nenhuma variável secreta foi exibida. Não houve fetch, checkout, build, arquivo remoto criado, restart ou escrita de banco.

| Identidade | Valor observado |
|---|---|
| Host/projeto | `clearbudget-vnic`, `/opt/markina-gallery`, `markina-gallery` |
| Checkout limpo e web publicada | `27e1b8ffa0917b4dc2120bd4a26e09c6cae47e0f` |
| API APP_VERSION / app-last-healthy | `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f` |
| API imagem | `markina-gallery-api`, `sha256:afc54e0ff0b008ac7bcc2ab28095f279da6213aaa5bec1ac98fae8269fc0715c` |
| Web imagem | `markina-gallery-web`, `sha256:768698a20b7042cf63a6e56df74fdea18a8e86b7086bbaa6c5bb8ba79d59250d` |
| Schema | `20261017_0084 (head)` |
| APP_ENV API | `staging` (valor real da instalação, não presumir `production` pelo domínio) |
| Hash Compose API | `307747f98ce953fb2f4e5af938710df4544eabd628c54477a67f479f48d493c2` |
| Hash Compose web | `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05` |

Todos os containers do projeto listados estavam `healthy`, inclusive API, web, Nginx, banco, Redis e workers. Não havia marcador `*in-flight*` no diretório de estado. Isso não comprova ausência de requisições/pagamentos em andamento nem substitui preflight operacional atualizado.

`web-current.identity` confere origem, ID e hash web acima. O recibo anterior é `4b464f081dfa2451472848622853460398834e6d`, imagem `sha256:6aef1935d8a4ba4bfc125a1bf5bea52ae6e26db361ef4942a1fedc55c4efc20a`. Esses recibos não foram alterados e não autorizam rollback.

## Causa exata e deltas por serviço

O PR #260 no SHA inicial `0959c64f00c60e6674675a9d90b43f0d7f9428b7` parte da main `1de04f84a63d20a9b43ccd2573da652b4d149167`. Dois runtimes do próprio PR estavam ausentes do gate: `backend/app/infinitepay_settings.py` e `backend/app/payment_availability.py`.

Além disso, a main contém #254 (`48e87784`, correções de dependências Python), #256 (`27e1b8ff`, publicação web isolada) e #257 (`1de04f84`, preparação do release Python). O checkout foi avançado pela publicação web; a API não foi reconstruída. A base histórica `fe1f3bc6` continua sendo a versão real da API. Avançá-la para main/checkout ocultaria atualizações Python pendentes.

O blob `requirements-push.txt` lido dentro da API é `5e4107da35e10fb49520f8a2781eb905920ccf56`; no checkout/candidato é `2e23bf84e3eae38396218bada0ee37d3da722843`. Metadados dos pacotes instalados confirmam:

| Pacote | API ativa | Candidato |
|---|---|---|
| aiohttp | 3.14.3 | 3.14.4 |
| multidict | 6.8.0 | 6.9.1 |
| urllib3 | 2.7.0 | 2.8.0 |
| yarl | 1.24.5 | 1.25.1 |

O Dockerfile da API copia esse arquivo e instala `requirements.txt`, que o inclui. Portanto reconstruir API no candidato publicaria essas quatro mudanças. Não são mudanças do PR #261, mas continuam expressamente fora da autorização InfinitePay.

**API efetiva:** seis módulos de checkout/configuração/binding/retorno, `requirements-push.txt` e testes; Compose acrescenta arquivo secreto somente à API, mantendo a configuração equivalente dos workers. Nenhuma migration ou Dockerfile mudou.

**Web efetiva:** somente `frontend/app/admin/settings/infinitepay-panel.tsx` e seu teste. Os manifests npm do candidato são idênticos aos da web já publicada; o delta npm visto desde `fe1f3bc6` é histórico, não uma nova atualização web.

## Manifesto corrigido, sem ampliar escopo

Acrescentados somente:

- `backend/app/infinitepay_settings.py`: `b96f5abfa6434305c751fbece1dcc65e10b4478d`.
- `backend/app/payment_availability.py`: `78ba7b53f4f3d32e5974e3f3bc91ad3d2f065aba`.

`production_baseline_sha` permanece `fe1f3bc6...` por evidência da API; schema permanece 0084. Não acrescentar dependências, migrations, cofre, diretórios genéricos ou arquivos da manutenção à allowlist. O manifesto único não descreve uma nova publicação conjunta de API/web; a distinção observada está nesta evidência e conserva o bloqueio.

Com o manifesto corrigido, o gate contra a base Git do PR retorna `app_release_ready=true / somente_api_web`; contra a base API publicada retorna `false / arquivo_fora_do_escopo`. A primeira comparação comprova a correção da omissão, não prontidão operacional. O classificador oficial continua `release_scope=protected`.

## Bloqueios restantes e menor próxima intervenção

1. **Candidato API inclui dependências não autorizadas.** Necessário um candidato isolado que preserve os inputs de dependências da API ativa enquanto aplica o delta InfinitePay, com estratégia de integração/build revisada. Não reverter silenciosamente fixes de segurança da main nem chamar o checkout web de baseline API. A outra alternativa é uma autorização separada de publicação das dependências; ela não foi presumida e esta missão não modifica a manutenção Python.
2. **Compose permanece protegido em duas fronteiras.** `classify_prod_release.py` classifica mudanças em `docker/` como `protected`; `deploy-prod-app-services.sh` recusa qualquer diff em Docker/Compose antes do gate de blobs. O manifesto já contém o blob do Compose API-only, mas isso sozinho não libera essas fronteiras. Após isolar o candidato, a menor correção operacional é admitir somente esse blob/efeito revisado em ambas, conservando recusa dos demais arquivos e validação dos serviços não afetados. Não abrir essas fronteiras enquanto o candidato exige dependências proibidas.
3. **Wrapper remoto ainda pinado à versão anterior.** SHA-256 instalado `253f9407a322822122d8339216ea9895482e386749b795c6724d524de4f8bfb2`, correspondente ao wrapper anterior com pin app `6767d0ba...`; candidato requer `e53a09dd453a7dd0353ce35ce42a56f6e2c3fc1e`. Nenhum wrapper foi instalado/alterado. Preparação de objetos e eventual atualização do wrapper exigem operação autorizada própria, antes de um preflight real do futuro SHA integrado.
4. **API Key ainda não provisionada.** Binding por UUID do tenant, alias exclusivo e `CREDENTIAL_ENV` igual ao APP_ENV observado; arquivo raw externo/ignorado injetado somente na API. O proprietário deve inserir o valor por canal operacional seguro, nunca chat/Git/CI. Não foi consultado valor de segredo, configurado binding, habilitado cartão ou criado checkout.

Pré-flight completo do candidato não foi executado: exige SHA final na main e objetos preparados no host; merge e preparação remota estão proibidos. Testes sintéticos de preflight/rollback não são ensaio operacional. O rollback continua sem alteração de código; não foi declarado pronto para executar nem acionado.

## Validação e decisão

O teste de regressão dos dois módulos falhou antes da correção, uma falha por módulo. Após a correção, a suíte verifica aceitação somente dos blobs revisados e recusa individual de manifests Python/npm, Dockerfile, módulo de cofre e migration 0085.

Validações locais: 14 testes do manifesto (incluindo os dois novos contratos), 13 do classificador, 4 contratos de preflight, política de workflow, OpenSpec estrito, compileall e diff check aprovados. Suíte adicional de estado/rollback em acompanhamento. Resultados adicionais e CI do head final serão consolidados no corpo do PR #260 antes da entrega. A evidência final do CI deve identificar o SHA exato; CI aprovado não converte os bloqueios operacionais acima em GO. Não gerar commit adicional apenas para inserir o próprio SHA e disparar validação recursiva.

**NO-GO para retomar merge/release emergencial do candidato atual.** A omissão dos módulos foi corrigida, mas o release exclusivo de pagamentos não está isolado das dependências da API. Nenhum merge, deploy, restart, migration, provisionamento, chamada financeira ou alteração de #261/#262 foi executado. Compra `e2194ce5` permanece intocada.
