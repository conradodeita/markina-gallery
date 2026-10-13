# Evidências de aplicação

## Base e autorização

Base `0ef80fd`, branch `feature/enforce-gallery-payment-availability`, worktree própria. O proprietário aprovou a proposta com “Sinal verde! Prossiga.”. Nenhuma alteração de configuração, pagamento ou operação real.

## Fronteiras inventariadas

| Fronteira | Contrato afetado |
| --- | --- |
| `PUT /admin/parent-galleries/{id}/sales` | Ao salvar cobrança obrigatória, validar meios locais da conta antes de preço/campos |
| `POST /admin/photo-folders/{id}/publish` e `/release` | Exigir recebimento da galeria paga antes de liberar fotos |
| `POST /admin/parent-galleries/{id}/publish-ready` | Mesma exigência, sem publicação parcial de lote |
| `media.generate_derivatives` | Liberação automática após derivados também depende da capacidade; processamento não deve perder os derivados quando falta recebimento |
| `/admin/settings/pix/challenge` e `/confirm` | Recusar remoção nova e desafio de remoção legado, preservar substituição |
| `/admin/settings/infinitepay/challenge` e `/confirm` | Revalidar proteção do último meio efetivo na confirmação |
| `unified_checkout`, `provider_checkout` e revisão cliente | Expor meios da própria conta, revalidar meio escolhido e preservar snapshots/reservas |

Serialização planejada: lock do registro `Tenant` da própria conta antes de locks de galeria/configuração. InfinitePay já usa esse lock; PIX atualmente usa somente `AdminUser` e precisa entrar na mesma ordem. Nenhum registro estrangeiro contará como recebimento.

## Regressão antes da correção

`python -m pytest tests/test_payment_availability.py -q --tb=short --basetemp C:/codex-data/test-runs/payment-baseline-20261013`, com `DATABASE_URL` SQLite sintética fora do Git: **6 falharam / 3 passaram**, 38,71 s. Falhas por ausência de HTTPException no salvamento pago (nenhum meio, PIX estrangeiro, cartão estrangeiro) e nos três caminhos publish/release/publish-ready. Casos válidos de PIX/cartão e jornada sem cobrança passaram. Nenhuma falha de fixture.

## Ambiente de validação

Dependências Python existentes e instalação npm conforme lockfile, sem mudanças de dependências. PostgreSQL de concorrência novo e exclusivo: `pyp-payment-availability-test-20261013`, PostgreSQL 17-alpine, `127.0.0.1:15471`, DB `pyp_payment_test`, tmpfs, 1 CPU/512 MiB. Porta 15470 preexistente foi preservada. Fixture aceita somente host/porta/DB de teste e cria/remove schemas `payment_availability_<uuid>` próprios. Nenhum recurso de outro projeto alterado.

## Projeção de meios (1.3)

`payment_methods` da resposta comercial e `pix_available`/`card_available`/`default_method` do carrinho são calculados apenas a partir das configurações do tenant autenticado. PIX depende da mesma validação do checkout; cartão depende do perfil ativo/pronto e do switch individual. `default_method` é PIX quando utilizável, cartão quando for o único disponível e nulo sem meios. Sem consulta ao provedor. Seis testes de capacidade própria/estrangeira, ambas válidas, PIX inválido e cartão desligado passaram (23,76 s).

## Evidências intermediárias de aplicação

- Jornada/publicação: 20 testes passaram em 71,48 s; guarda 422 no salvamento e 409 na publicação, derivados `ready`/job `completed` preservados quando falta recebimento.
- Editor: 59 testes passaram; bloqueio sem meios e avanço no modo externo. TypeScript aprovado.
- Sem cobrança: sete regressões backend de finalização/receita/histórico/entrega/carrinho misto passaram; dois casos PostgreSQL ignorados em SQLite, sem alegação de concorrência. 16 testes iniciais de carrinho passaram.
- PIX: 18 testes backend passaram em 74,44 s e três do painel passaram. Nova remoção recusa 422 antes de emitir desafio; confirmação de remoção legada recusa 409 e mantém configuração/desafio. Migration histórica 0046 continua usando `normalize_configuration(None)`; a recusa ocorre em proposta/aplicação interativas.
- Último meio: 21 casos de configuração InfinitePay/isolamento passaram em 71,80 s, incluindo recusa de desligar/remover/trocar tag sem PIX em galeria paga liberada e permissão com PIX/modo externo/rascunho.
- Concorrência PostgreSQL: dois casos passaram em 11,05 s. `pg_stat_activity` confirmou espera por lock antes da transação líder concluir; publicação versus desligamento, nas duas ordens, recusa a segunda operação e conserva cobertura. Quatro casos de reativação passaram em 24,60 s.
- Carrinho: 19 testes frontend passaram; PIX padrão, somente cartão sem preparar PIX, nenhuma ação financeira sem meios e finalização sem etapa financeira. Três regressões de API cartão-only/perfil inválido/replay passaram em 34,87 s.
- A projeção do cartão e sua preparação agora usam o mesmo perfil público pronto. Isso revelou fixture de retorno que devolvia perfil sintético diferente do snapshot público; a evidência da fronteira foi corrigida para o perfil documentado, e o teste passou em 12,05 s. Não houve alteração da confirmação financeira.
- Frontend completo: **60 arquivos / 511 testes aprovados**, 94,62 s. Lint sem erros, 31 avisos existentes. Build Next.js 16.3.2 concluído, incluindo TypeScript e geração de rotas.

Estas evidências não correspondem a homologação InfinitePay nem a publicação. O checkpoint final identifica o diff e os testes repetidos após ajustes de integração.

## Checkpoint final de integração (13/10/2026)

- `backend/tests/test_payment_availability.py`: **34 passaram** no PostgreSQL 17 descartável; inclui os dois ensaios concorrentes reais contra PostgreSQL.
- Respostas comerciais e capacidade PIX/cartão após corrigir a localização de `payment_methods` para `GET .../sales`: **3 passaram** no PostgreSQL.
- Integração backend executada com `DATABASE_URL=sqlite:///C:/codex-data/test-runs/payment-integration-final.sqlite`: **94 passaram, 6 skips, 1 falhou** em 431,87 s. A falha foi `test_media_remains_available_when_facial_configuration_is_invalid`, cuja cópia do módulo havia sido carregada antes da atualização da fixture que declara explicitamente a galeria sem cobrança. Com o arquivo atual, o módulo facial completo passou (**10 testes**) e o caso isolado repetido passou (**1 teste**, 1,21 s). Os seis skips são cenários que exigem PostgreSQL nessa execução SQLite; os casos concorrentes passaram no PostgreSQL separado.
- Testes backend de mídia/acervo no checkpoint anterior: **69 passaram**; duas falhas iniciais eram premissas antigas de fixture (galerias de processamento/acesso restrito sem PIX tratadas como pagas). As duas foram alinhadas à jornada sem cobrança e passaram no rerun. Teste adicional de publicação adiada e fila facial existente: **2 passaram**.
- Após posicionar a projeção em `/sales`, as respostas focadas foram repetidas contra PostgreSQL (**3 passaram**); após incluir o caso de cartão-only no editor, editor final: **60 passaram** e TypeScript aprovado.
- Frontend completo: **60 arquivos / 511 testes passaram**. Lint: zero erros, 31 avisos já existentes. Build Next.js 16.3.2 passou, incluindo typecheck/rotas.
- `ruff check app tests --output-format concise`: aprovado; `git diff --check`: aprovado. `npx --yes @fission-ai/openspec@1.14.0 validate --all --strict`: **98 itens passaram, zero falhas**. O CLI emitiu notas informativas de deltas arquiváveis/specs preexistentes, sem falhar a validação.
- Revisão final cobre todos os caminhos modificados/adicionados no backend, frontend e change OpenSpec. O diff contém somente a implementação desta change; não contém `.env`, credenciais reais, banco local, cache ou artefatos de execução. Nenhuma dependência/lockfile alterada.
- Limites: não houve transação real InfinitePay, confirmação de webhook, validação em homologação ou deploy. A sincronização e o archive foram executados somente depois da revisão/autorização humana registrada abaixo.

## Sincronização e archive após revisão humana


## Correções após CI do PR #169 (13/10/2026)

- O CI do merge-base `0ef80fd` passou integralmente antes do PR. No commit inicial da change, o CI do PR reportou **20 falhas, 1.540 aprovações e 23 skips**.
- Seis falhas de confirmação de cartão compartilhavam a mesma causa: o helper `verified_result` usava a evidência `synthetic-only`, enquanto a fixture atualiza o snapshot para `infinitepay-public-v1`. A fixture agora emite evidência sintética com o perfil do snapshot e ainda permite overrides incompatíveis nos testes negativos. Nenhuma validação financeira de produção foi relaxada.
- Falhas de mídia, processamento de pastas e publicação usavam galerias pagas sem configurar meios, embora esses testes não avaliem a regra de cobrança. As fixtures que exercitam mídia/isolamento sem vendas agora declaram `payment_required=False`; a integração facial continua exercitando galeria paga e configura PIX sintético válido. Os dois testes de publicação exercitam o fluxo com cobrança desativada.
- A suíte focada que reproduziu as falhas reportadas foi repetida com `DATABASE_URL` SQLite sintético fora do Git: **35 passaram, zero falhas**, em 221,04 s. `ruff check backend/app backend/tests` e `git diff --check` passaram. O rerun integral do CI ainda é necessário antes do merge; nenhuma publicação ou deploy decorreu desse checkpoint.
