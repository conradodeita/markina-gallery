# Design

## Context

Ver `proposal.md` para a motivação e `readiness.md` para a versão/evidência examinadas. A sessão resolve a conta no servidor. `global_pix_settings` e `checkout_pix` exigem `tenant_id`; `ownership_schema.py` escopa singletons e acrescenta FKs compostas. `PaymentGroup` representa PIX manual e contém campos PIX obrigatórios. O comércio inclui também pedidos canônicos de galeria + cliente, legados e finalização sem cobrança.

O checkout PIX prepara um rascunho editável e congela/remove seleções quando a cliente informa pagamento. Um link externo continua pagável depois que a cliente fecha a página. Por isso, a emissão de cartão precisa de snapshot imutável e reserva anteriores à chamada externa, sem depender do botão `Informar pagamento`.

A documentação pública não comprova assinatura de webhook, restrição de método por link, titularidade remota pela InfiniteTag, cancelamento/expiração ou todas as garantias de `payment_check`. Esses gates estão em `provider-contract.md`; sua ausência não autoriza implementar um contrato presumido.

Pesquisa complementar de 12/10/2026 em `research-review.md`: o cURL oficial de criação e o cliente WooCommerce examinado não acrescentam credencial; o painel oferece API Keys e seu teste usa endpoints internos autenticados. Nenhum desses fatos, isoladamente, define a autenticação de servidor externo por fotógrafo. O relatório do proprietário admite estudar verificação oficial alternativa à assinatura quando aplicável; a decisão concreta depende de comprovar essa alternativa e reconciliar o contrato de segurança afetado, sem copiar a autenticação de sessão do painel.

## Goals / Non-Goals

**Goals:** adicionar cartão ao comércio da conta proprietária, conservar o contrato do PIX manual, impedir efeitos cruzados e cobrança duplicada e manter evidência mínima para conciliação.

**Non-Goals:** modificar seleção sem pagamento, transportar dados de cartão, automatizar PIX bancário, replicar carteira do provedor, estimar taxa líquida, criar reembolso pela API ou criar novo serviço de infraestrutura nesta preparação.

## Decisions

### 1. Configuração por tenant e reautenticação local

Criar configuração específica `InfinitePaySettings`, uma por `tenant_id`, com versão, InfiniteTag canônica, estado inativo/pendente/ativo e metadados mínimos da verificação. O contexto vem de sessão/vínculo ativos; nenhuma rota aceita tenant do cliente como autorização. Aplicar FKs de proprietário e controle de versão nos desafios. Reutilizar o padrão de senha + OTP administrativo do PIX para mudança de recebedor, incluindo ativação/desativação; não editar o PIX. A ativação é uma autodeclaração explícita, vinculada ao desafio sensível, de que o fotógrafo conferiu a InfiniteTag recebedora na própria conta InfinitePay, habilitou Checkout Integrado e cartão, desligou PIX e conferiu um link de teste sem concluir a compra. Isso registra o que o titular declarou; não equivale a prova remota de titularidade nem a garantia do provedor.

InfiniteTag é identificador público e não comprova titularidade. Não usar senha do provedor nem inventar OAuth/API key. O onboarding apresenta o recebedor declarado e exige confirmação do fotógrafo sobre a tag e os meios de pagamento habilitados antes da ativação. Até existir contrato de verificação remota, não prometer associação automática comprovada. Segredos eventualmente exigidos vão para configuração segura externa, mediante autorização específica.

Alternativa rejeitada: uma InfiniteTag global ou associação por `admin_user_id` apenas; login não equivale à conta comercial proprietária.

Configuração: `GET /admin/settings/infinitepay`, `POST /challenge`, `/confirm` e `/resend` sob o mesmo prefixo. A proposta contém InfiniteTag, autodeclaração de configuração pronta ou remoção, controle explícito `card_enabled` e `expected_version`; fica cifrada no desafio. Confirmação recebe apenas UUID/código, sem aceitar configuração substituta. Locks da conta serializam emissão/confirmação/reenvio; sessão e vínculo são revalidados. Configuração pronta grava o perfil `infinitepay-public-v1` e timestamp de declaração; mudança da tag volta a pendente e desabilita novos checkouts até nova confirmação. `card_enabled` começa falso e só fica efetivo com uma configuração ativa e pronta. Desabilitá-lo oculta cartão de novos checkouts, sem cancelar ou esconder links de compras já emitidas; esses links continuam retomáveis até confirmação/conciliação, porque não há cancelamento remoto documentado. Nenhuma rota verifica titularidade remotamente nem armazena chave do provedor.

### 2. Porta de provedor limitada ao contrato verificado

Introduzir `PaymentProvider` para criação de checkout e consulta de status, com resultados tipados e estados explícitos de aceitação, recusa e incerteza. O adaptador InfinitePay usa HTTP no backend/worker, endpoint HTTPS fixo, validação TLS, limites de tempo/corpo e nenhuma URL de API controlada pelo browser. A porta expõe apenas capacidades oficialmente comprovadas; não cria cancelamento ou idempotência externa presumidos.

A documentação oficial atual fixa os endpoints `POST https://api.checkout.infinitepay.io/links` e `POST https://api.checkout.infinitepay.io/payment_check`. A página oficial de Checkout Integrado, consultada em 20/10/2026, diz que API Key é opcional para a criação simples por InfiniteTag, mas necessária para opções avançadas; a Central de Ajuda documenta `X-Api-Key` tanto na criação quanto em `payment_check`. Isso conflita com o entendimento anterior de que a consulta poderia ser feita sem chave. Nenhum segredo foi recebido ou configurado, e a integração atual não envia esse header. Portanto, confirmação operacional via `payment_check` permanece bloqueada até definir armazenamento seguro e validar o contrato de autenticação; não improvisar segredo global ou por tenant.

`order_nsu` é o UUID interno opaco da compra e a URL confiável de `redirect_url` permanece fixa; o retorno deve devolver o mesmo `order_nsu`, mais `transaction_nsu` e `slug` como candidatos. O backend carrega a compra por esse UUID, verifica a representação canônica do `order_nsu`, usa handle e total congelados e só confirma após `payment_check` retornar pago e compatível. Respostas não-2xx, timeout e JSON inválido são desconhecidos, nunca motivo para confirmar ou emitir de novo. O checkout retornado é aceito somente em `checkout.infinitepay.com.br` ou `checkout.infinitepay.io`, ambos por HTTPS. O webhook fica fora do caminho inicial porque não há contrato público de assinatura; poderá ser tratado como gatilho para a mesma consulta autoritativa após decisão de segurança. A configuração PIX desligada foi confirmada pelo proprietário; o fotógrafo deve conferir o link hospedado antes de aceitar pagamento real.

O fluxo PIX permanece com criação e confirmação manuais existentes. Nenhuma chamada externa é necessária para mostrar PIX ou finalizar seleção sem pagamento. SDK novo não é requisito; utilizar a biblioteca HTTP já adotada no backend.

### 3. Agregado de cartão separado do grupo PIX

Adicionar um agregado `ProviderPayment` por compra de cartão, com tenant/cliente, UUID opaco usado como `order_nsu`, revisão, total, snapshot da conta/versão, estado de emissão/verificação e identificadores externos. Acrescentar vínculo nullable dos `SaleOrder` integrantes, com FK composta tenant/cliente e exclusão mútua entre esse vínculo e `payment_group_id`. Não preencher campos PIX com valores fictícios nem mudar a semântica de `PaymentGroup`.

Adicionar tentativa durável de emissão e recibo/job de verificação, com tenant explícito e índices de idempotência. O identificador de transação, depois de verificado, só pode financiar uma compra; a exclusividade é conferida mesmo entre tenants. Adequar o inventário de ownership e os testes de catálogo/migration para todas as tabelas novas. Persistir somente campos financeiros necessários, não payload arbitrário.

Alternativa rejeitada: chamar `prepare_group` e reutilizar um grupo PIX para cartão, porque essa função exige PIX e permite recalcular o rascunho antes da comunicação.

Persistência local: `ProviderPayment` usa estados `creating`, `awaiting_payment`, `verification_required`, `confirmed`, `failed_before_issue`, `exception` e `hold`; a recusa comprovada antes da emissão permite falha local, enquanto recusa de cartão no checkout não comprova inutilização do link. `ProviderPaymentAttempt` registra `started/accepted/refused/unknown`, sem payload externo arbitrário. `ProviderPaymentReceipt` registra candidatos mínimos de transação/slug, digest e perfil de verificação, com `queued/processing/verified/ignored/failed`; não representa confirmação por si só. Cada filho exige FK composta do agregado/tenant/cliente. O NSU de transação confirmado é único globalmente por provedor; IDs de pedidos/cartões não substituem esse controle. A coluna nova em SaleOrder é nullable e mutuamente exclusiva com grupo PIX; registros anteriores continuam com NULL.

### 4. Freeze, reserva e emissão fora da transação de banco

Sob os locks comerciais existentes, validar revisão, prazo, fotos e cotação autoritativa da conta. Gravar snapshot/pedidos/reserva e tentativa `creating` numa transação curta; liberar locks antes de chamar a InfinitePay. O worker revalida tenant antes do efeito. Uma chave da mesma compra retorna o agregado existente; índices e locks impedem uma emissão concorrente de seus itens.

Itens reservados aparecem em uma compra `Aguardando pagamento`/`Verificando pagamento` e não são oferecidos em outro PIX/cartão. Novas fotos elegíveis continuam compráveis; nenhuma seleção fora do snapshot é consumida. Compras antigas, comunicadas ou já confirmadas não são recalculadas. A preparação de cartão recusa sobreposição com PIX comunicado e trata rascunho PIX não comunicado sob o mesmo lock, preservando snapshots/pedidos históricos.

Falha comprovada antes de emissão externa pode liberar a reserva de forma explícita e atômica, sem restaurar fotos já removidas/inelegíveis. Timeout possivelmente aceito fica `verification_required`, sem reenvio cego. Após link emitido, voltar à tela não cancela a cobrança. Cancelar/mudar de meio exige comprovação de que o link deixou de ser pagável; a ausência dessa capacidade mantém a compra em conciliação. TTL local não invalida link remoto.

Quando o adaptador retorna a recusa tipada `not_created`, o servidor restaura os itens elegíveis na seleção da cliente e encerra o agregado como `failed_before_issue`. A interface limpa a tentativa concluída e permite iniciar outra cobrança com os mesmos itens; uma nova chave de idempotência é gerada para essa nova emissão. Isso não é retry para `unknown`: timeout, resposta não-2xx, JSON inválido ou URL rejeitada continuam reservados e sem botão de reemissão.

Diagnóstico de emissão: `ProviderPaymentAttempt.error_category` tem capacidade existente para códigos normalizados curtos. Resposta HTTP não-2xx pode registrar o código HTTP; JSON inválido, resposta excessiva, ausência de URL e URL não permitida registram categorias fixas. Corpo, headers, URL de checkout e credenciais não serão copiados para esse campo. Todos esses casos continuam `unknown` até reconciliação autoritativa; categorias melhoram a investigação futura sem liberar a compra automaticamente.

Alternativa rejeitada: manter a mesma seleção livre para PIX enquanto um link de cartão imutável existe, pois isso permite dois pagamentos das mesmas fotos.

### 5. Crédito exclusivo e taxas administradas no provedor

A revisão oferece `PIX` e `Cartão de crédito` a partir de capacidades autorizadas da conta, com aviso do redirecionamento. Cartão não depende de PIX configurado. Checkout externo é hospedado pela InfinitePay, com cartão/parcelas/taxas nas condições da conta do fotógrafo. O sistema não define taxa ou parcela por parâmetro não documentado.

A configuração do app InfinitePay para desligar PIX é candidata ao gate de crédito exclusivo, ainda sem prova de aplicação aos links da API. Não usar campo presumido `payment_methods`. Uma confirmação `credit_card` é necessária, mas não substitui verificar que PIX está ausente antes do pagamento. Se o provedor não puder garantir crédito exclusivo, cartão permanece indisponível até revisão do contrato/escopo; não transformar recebimento inesperado de PIX em confirmação manual automática.

Comparar `amount` ao total-base congelado e interpretar `paid_amount` somente após verificar a semântica de acréscimos. Receita de fotos usa o valor comercial dos pedidos, sem somar taxas nem duplicar o agregado. Não inferir valor líquido de recebimento.

### 6. Retorno do checkout e consulta autoritativa

O fluxo inicial não depende de webhook. O `redirect_url` construído pelo servidor inclui o UUID do ProviderPayment como parâmetro privado de correlação; a InfinitePay acrescenta `order_nsu`, `transaction_nsu` e `slug` após o comprador clicar em “Continuar”. O endpoint aceita somente identificadores com limites estritos, compara `order_nsu` à compra e trata todos os demais parâmetros como entrada não confiável.

O servidor carrega o agregado pelo `order_nsu`, lê `handle_snapshot` e `total_cents` e chama `payment_check` no endpoint fixo. Só a resposta do provedor pode confirmar: exige sucesso/pago, `credit_card`, `amount` igual ao snapshot e vínculo com handle, compra, slug e transação. `receipt_url`, `capture_method` e outros parâmetros do browser são apenas pistas e não são seguidos nem usados como prova.

Falha de transporte mantém a compra em verificação e permite reabrir a página de retorno com os mesmos candidatos, sem reemissão. `paid=false` não confirma nem libera seleção automaticamente. A documentação não informa recuperação quando o comprador paga e fecha a página sem clicar em “Continuar”; essa compra permanece em conciliação manual. O webhook, que seria mais eficiente para esse caso, só será adicionado após contrato de assinatura ou decisão de segurança; se usado, ele apenas dispara a mesma consulta autoritativa.

### 7. Aplicação financeira atômica e reconciliação

Concentrar confirmação em serviço de domínio, reutilizando regras de status, fotos elegíveis, receita, notificações e entrega. PIX mantém a decisão manual; cartão exige evidência verificada do provedor e não usa `Informar pagamento`. Gravar transação confirmada, agregado e todos os pedidos juntos, sem contabilizar duas vezes.

Adaptar Compras, consulta administrativa e atalhos para distinguir o agregado de cartão do PIX. A mesma compra gera um evento lógico de confirmação por canal habilitado; falha de transporte não desfaz pagamento. Uma correção financeira autorizada grava hold/versionamento, conserva a evidência e suspende entrega conforme a regra atual. Replay antigo não remove esse hold. Reembolso/chargeback não serão inferidos de ausência de webhook ou `paid=false`; tratamento operacional e eventual estorno no app dependem de evidência/autorização próprias.

Estado histórico antes da integração da rota: a aplicação de evidência tipada fica em `provider_confirmation.py` e exige perfil/método/valor/compra/conta/tag/slug/NSU compatíveis. A rota de retorno adicionada posteriormente chama esse serviço somente após `payment_check`. Uma transação confirma o agregado e todos os pedidos, grava recibo mínimo e cria um único evento de cliente com revisão financeira no event key; o consumidor confere o agregado e a revisão de novo imediatamente antes do aviso. Correção autorizada fica append-only em `ProviderPaymentCorrection` (revision 0077), conserva o NSU e põe agregado/pedidos em hold/pending; avisos queued/processing são invalidados, e a verificação de revisão bloqueia qualquer aviso que já esteja no fluxo. Testes de domínio são sintéticos; o teste externo real permanece pendente.

## Revisão do contrato autenticado — 20/10/2026

A decisão anterior de 12/10/2026 de usar `/payment_check` sem API Key foi substituída pelo proprietário em 20/10/2026 após revisão da Central de Ajuda vigente. O proprietário escolheu um cofre de segredos por fotógrafo; nenhum valor será compartilhado no Git, frontend ou chat. O repositório já aplica configuração secreta do servidor por UUID→alias e `CREDENTIAL_ENV` em `add-small-multi-photographer-pilot`; InfinitePay usará binding próprio, sem credencial em tabela comercial e com injeção somente no container API.

O binding InfinitePay seguirá o padrão de configuração server-side `TENANT_BINDINGS` + alias único + `CREDENTIAL_ENV` + `API_KEY`, com um arquivo raw de ambiente opcional dedicado à API (não reutilizar o arquivo WhatsApp, consumido por workers). A resolução é pelo tenant autenticado/compra persistida; não aceita alias do frontend, não tem fallback cruzado e esconde estado/valor secreto em logs e respostas. Sem binding/chave compatível com `APP_ENV`, checkout por cartão fica indisponível antes de reservar fotos. O proprietário provisionará valores somente pelo cofre/canal operacional seguro fora desta mudança.

O cliente HTTP enviará `X-Api-Key` em `/links` e `/payment_check`. Em `/links`, enviará opções avançadas oficialmente documentadas `payment_methods_enabled: ["credit_card"]` e `single_payment: true`, mantendo o contrato de negócio de cartão exclusivo e impedindo reutilização do mesmo link para pagamentos duplicados. InfinitePay só será considerada disponível para checkout quando a chave por tenant estiver configurada no servidor. Ausência ou binding inválido falha fechado antes de reservar/emissão. A chave permanece fora de logs, respostas e frontend. Não se adiciona chave ao modelo `InfinitePaySettings` nem migration de banco.

A mesma documentação permite `["credit_card", "pix"]` em um link, mas o domínio atual trata pagamento PIX apenas como `PaymentGroup` manual e confirma `ProviderPayment` somente como cartão. PIX integrado não será habilitado nesta correção; essa mudança exigiria uma decisão de produto e uma revisão dos estados/receita/relatórios. Webhook ainda não será consumido como prova: tipos de eventos são publicados, assinatura/autenticidade não.

### 8. Privacidade e feature inativa por padrão

Descrições comerciais neutras, UUID opaco e quantidades/valores bastam no payload inicial. Não enviar fotos, nomes de arquivo, nomes de menores, biometria, links privados, endereço ou contatos opcionais. Não versionar evidências de conta/comprovantes reais. Logs usam IDs internos/categorias de erro, sem tokens, dados de cartão, URLs com segredos ou payload completo.

Integração inicia inativa. Mocks/fixtures sintéticos podem comprovar o comportamento local depois do aceite; não provam contrato externo. Habilitação por conta depende da autodeclaração vinculada do fotógrafo e da conferência de link sem pagamento em sua conta, sem apresentar nenhuma delas como prova remota de titularidade ou suporte a webhook assinado.

## Risks / Trade-offs

### Autorização operacional definitiva — 21/10/2026

O proprietário autorizou merge/release supervisionado, indisponibilidade, interrupção graciosa de workers e rollback por identidade, além dos quatro pins Python nos consumidores com imagens homologadas. Essa autorização substitui os bloqueios de escopo operacional anteriores, mas não dispensa CI, candidaturas, preservação de Python 3.13.16/distribuições restantes e callbacks financeiros. PR #262 permanece fora do candidato porque não há provisão/migration/keyring/homologação operacional; #261 não é necessário ao bootstrap autorizado.

Corrigir o executor existente, sem criar outro fluxo: manifesto identifica baseline API e web separadas e hashes exatos de dependências/Compose; classificador só admite app quando o gate completo aceitar esses inputs. O build API deriva da imagem ativa preservada, instala somente os quatro wheels sem resolver dependências e copia código Git aprovado; compara todas as distribuições e Python e ensaia startup isolado/network none/tmpfs antes de recriação. Assim não depende de rebuild com requirements abertos que possa atualizar Python ou outras distribuições. O caminho legado permanece para manifestos sem o contrato emergencial; Python-security operacional genérico permanece recusado até ter executor/candidatos dos demais consumidores.

Primeiro concluir gates, backup, binding pelo titular e integração; depois janela curta de manutenção API/web, conservando estado financeiro ambíguo. Capturar agregados e identidades persistidas antes/depois. Retorno InfinitePay é browser→consulta autoritativa, sem webhook financeiro consumido; manter as tentativas pendentes e seus IDs para retorno repetível/reconciliação. Não criar link ou pagamento pelo executor. Workers sem imagem homologada permanecem nas identidades existentes e não atrasam o cartão.

### Correção restrita dos gates — 21/10/2026

Autorização atual permite somente inventário Oracle de leitura, correção local dos gates, testes e CI do PR #260. Merge, deploy, restart, migration, provisionamento e alterações financeiras estão proibidos nesta missão. Os PRs #261/#262 permanecem fora do escopo.

O inventário identifica API `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f` e web/checkout `27e1b8ffa0917b4dc2120bd4a26e09c6cae47e0f`. A API instalada conserva quatro versões Python anteriores ao commit #254, já presente na main. Portanto a baseline histórica continua correta para a API e não pode ser substituída pelo checkout ou pela main. A correção independente admite somente os dois módulos omitidos no manifesto, com hashes exatos. Dependências não publicadas e gates de Compose/preflight permanecem bloqueios; não ampliar allowlists para forçar um GO. Evidência por serviço e menor próxima intervenção ficam em `release-gates-20261021.md`.

### Preservação de workers fora do escopo

O deploy desta change SHALL preservar os estados de processamento facial e RAW já operacionais. O workflow não passa flags para ligar/desligar facial: o script preserva o valor de `FACIAL_PROCESSING_ENABLED` do `.env.homolog`. Para RAW, o script usa o modo `auto`, detecta se o worker do projeto está ativo antes de preparar o Compose e somente inclui/reinicia o overlay RAW se já estiver ativo. Assim o rollout de cartão não inicia consumidores de dados de outra finalidade nem desativa um módulo existente.

- [Webhook sem contrato público de assinatura] → manter webhook fora do primeiro fluxo; usar a consulta `payment_check` autorizada para o retorno. Não confiar no payload de evento até revisar contrato com o provedor.
- [Checkout API oferecer PIX apesar da escolha cartão] → comprovar G1 por conta/ambiente antes de ativar; não aceitar captura PIX nem simular restrição por validação posterior.
- [Recebedor digitado incorretamente] → mudança sensível, prévia/conferência do recebedor e snapshot imutável; não afirmar titularidade pela sintaxe da tag.
- [Timeout gerar cobrança desconhecida] → tentativa durável, reserva e conciliação sem reemissão; validar recuperação G4 antes do uso real.
- [Assinatura/perfis mudarem depois da ativação] → registrar versão do contrato, desabilitar novas emissões quando invalidado e conservar compras/evidências antigas.
- [Bloqueios do piloto multitenant ainda abertos] → reconciliação explícita da dependência D1; testes locais não concluem o ensaio/revisão remotos.

## Migration Plan

1. Revisar esta proposta e reconciliar a base multitenant/D1. Fixar o head Alembic da implementação; não reservar número de revision antecipadamente.
2. Acrescentar tabelas/coluna nullable/constraints de cartão sem remover dados nem converter grupos PIX. Ensaiar PostgreSQL vazio e legado sintético, FKs A/B, snapshots, rollback transacional e comparação de contagens/valores.
3. Publicar código compatível com cartão inativo; preservar leitura de PIX/legados/seleção sem pagamento. Ajustar projeções, workers e APIs com testes de isolamento e concorrência.
4. Concluir gates de contrato e testes de mocks/ambiente real autorizados. Preparar inventário, portas/subdomínio, backup, escritores próprios e reversão compatível. Nenhum push/merge que dispare deploy é implícito nesta preparação.
5. Após autorização específica, liberar apenas recursos Pick-your-Pic e ativar somente a conta autorizada. Verificar o recebedor, crédito exclusivo, aprovação/negativas/replay e efeitos de entrega na versão publicada.
6. Reversão preferencial desativa novas emissões e mantém versão capaz de retomar/conferir transações existentes. Binário antigo só retorna após prova de compatibilidade; downgrade com transações existentes ou restauração exigem plano/autorização próprios. Após aceite humano, sincronizar a nova spec e arquivar.

### 9. Projeções da compra de cartão

O histórico da cliente agrupa os pedidos do mesmo `ProviderPayment` numa compra, mantendo os pedidos PIX e compras antigas no formato atual. A consulta sempre filtra pelo tenant e cliente autenticados. Só o estado `awaiting_payment` pode expor o link hospedado; após confirmação, verificação, exceção ou hold, não retorna URL de checkout. O NSU e recibos internos nunca fazem parte da projeção pública.

A fila administrativa continua calculando valores por `SaleOrder`, pois a soma do agregado sobre esses mesmos pedidos duplicaria a receita. Ela acrescenta método/estado e filtra os agregados pelo tenant. Estatísticas e atalhos de itens vendidos também leem os pedidos confirmados, portanto acompanham a confirmação atômica sem um segundo lançamento. Os eventos de pagamento são por compra/revisão e o consumidor valida o estado vigente antes do envio, inclusive contra uma correção que ponha a compra em hold.

### 10. Inventário e limpeza restrita de homologação

`InfinitePaySettings` é configuração da conta do fotógrafo e permanece preservada junto ao PIX global quando a limpeza exclusiva de homologação remove clientes/galerias. Compras de cartão, tentativas, recibos e correções seguem as tabelas de pedidos/transações operacionais dessa limpeza; a ordem gerada pelas FKs remove filhos antes do agregado e do cliente. A matriz fechada deve nomear as cinco tabelas para impedir limpeza com schema desconhecido. Isso vale apenas para a operação explicitamente autorizada de homologação; nenhuma limpeza operacional/produção é feita nesta change.
