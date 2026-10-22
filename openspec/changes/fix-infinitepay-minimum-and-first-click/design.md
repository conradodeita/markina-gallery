# Design

## Context

Escopo funcional autorizado diretamente pelo pedido do proprietário em 21/10/2026. Base publicada: `21b89c332c6937b7079679888d52bd6a8aefe25d`. O PR #262 permanece preservado em worktree separada, sem inclusão nesta correção.

Fontes consultadas em 21/10/2026:
- https://www.infinitepay.io/checkout-documentacao — POST `/links`, valores em centavos e redirecionamento após obtenção da URL; não explicita mínimo.
- https://ajuda.infinitepay.io/pt-BR/articles/10766888-como-usar-o-checkout-integrado-da-infinitepay — opções por link; `assured_installments` representa absorção de taxas e não escolha das parcelas do comprador; não explicita mínimo.
- https://www.infinitepay.io/checkout-tap — mínimo de 100 centavos e por parcela explícitos para integração Tap por deeplink. Não aplicar seu contrato ao Checkout Integrado por inferência.

## Decisions

### Piso local somente para novas reservas por cartão

O backend calcula o total inteiro autoritativo depois dos locks e da revisão atual. Recusa total menor que 100 centavos antes de criar ProviderPayment/Attempt, alterar PIX ou consumir seleções. O retorno idempotente de tentativa existente ocorre antes desse novo requisito: nenhuma emissão histórica será convertida, liberada ou recusada retroativamente por seu valor.

O limite incide no total das galerias com cobrança, não no preço individual. Fotos de poucos centavos podem compor um total válido. PIX manual e finalização sem cobrança conservam as regras existentes. Não alterar `PaymentProvider` nem os payloads da InfinitePay: as parcelas continuam sendo escolhidas no gateway, sem interpretar `assured_installments` como limite de parcelas.

### Carrinho e navegação

Na seleção atual abaixo de R$ 1,00, mostrar orientação junto à ação de cartão e impedir seu envio. A guarda no servidor continua obrigatória contra chamadas diretas ou revisão obsoleta. PIX segue disponível conforme configuração própria. Compras antigas pendentes continuam exibidas e protegidas pelo fluxo publicado.

Ao receber `awaiting_payment` com URL HTTPS da origem de checkout permitida, a ação explícita inicia navegação na mesma aba com `location.assign`, sem popup dependente de ativação após `await`. Só navegar para URL utilizável. Manter o link de retomada e a compra no estado reservado se a navegação não ocorrer. GET/foco/remontagem nunca iniciam redirecionamento automático. Falha clara, falta de URL, resposta incerta e estados terminais não navegam nem liberam reservas.

### Compatibilidade e manutenção proporcional

Reutilizar o mutex de UI e a chave por revisão. Validar duplo clique, erro de rede e retomada sem emissão nova. A área afetada possui consumidores ativos; não remover módulos, CSS ou projeções históricas. Não flexibilizar gates operacionais nem incluir cofre/migration no release API/web.

### Preparação exata para revisão, sem operação remota

Após o proprietário pedir para concluir o roadmap, preparar no próprio PR o manifesto da correção: baseline observado `21b89c3`, novos blobs exatos de `provider_checkout.py`, `cart/page.tsx` e `cart/checkout-navigation.ts`. Incluir somente o novo arquivo de navegação na lista de runtime e seu teste na lista exata de operações; classificar os três caminhos como API/web. Manter revisão0084, pins de dependências, imagem base, gates de autenticação/aprovação/fingerprint e recusa de qualquer cofre, migration, worker ou arquivo não listado. Essa preparação local é revisável e não autoriza merge/deploy. Provar aceitação de blobs exatos e recusa de adulteração/arquivo semelhante não listado. A autorização operacional do release anterior não se estende ao novo candidato.

### Metadado de falso positivo do scanner

O CI780 de #262 detectou o indicador público de comparação de distribuições do recibo do release anterior como chave genérica. A ocorrência pertence ao cherry-pick histórico b7f2090e, não a uma API Key. O scanner padrão atravessa refs do repositório; uma nova execução de #266 também pode encontrá-la depois do envio de #262. Reutilizar somente a fingerprint imutável já reproduzida e validada com gitleaks8.24.3 e canário independente em #262. Não alterar regras, regexes, workflow de varredura ou histórico para ocultá-la. Admitir `.gitleaksignore` como arquivo exato de metadados não runtime no gate API/web, com regressão que recusa arquivo semelhante não listado. Essa admissão não inclui qualquer arquivo de cofre/migration; o restante da política e os blobs permanecem fixados.

## Validation

Regressões primeiro: recusa por API/domínio antes de qualquer efeito, fronteira de 100 centavos e itens baratos com total válido; UI de mínimo com PIX e seleção preservados; navegação após um clique e uma emissão; não navegação em incerteza/erro/GET; idempotência e concorrência existentes. Executar testes direcionados e gates pertinentes, registrando resultados efetivos em `validation.md`.

### CI ARM64 nativo após timeout comprovado

CI781/39699038564, job119563500858, atingiu30min no build frontendARM64 sob QEMU. Reutilizar somente a matriz nativa já existente na branch262:ubuntu-latest/amd64 e ubuntu-24.04-arm/arm64, com conferência de uname, fail-fast false, mesmos builds/versões/lockfile e limite30min. Não aumentar timeout, omitir arquitetura, trocar dependências ou publicar imagens. O agregador continua exigindo runtime-images integral. A validação remota é necessária; política local e inspeção YAML não provam build remoto.
