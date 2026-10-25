# Design

## Context

Base isolada: origin/main cef5bdf8, aposentadoria InfinitePay consolidada. Checkout inicial com trabalho divergente foi preservado. Análise e fontes estão em analysis.md. A missão do proprietário autoriza preparação e implementação sequenciais, sem a pausa de planejamento do fluxo opcional propose. Aplicação usa openspec-apply-change.

## Goals / Non-Goals

Disponibilizar Checkout Transparente Orders em desenvolvimento com segurança financeira e tenant explícito. Preservar PIX manual, seleção sem cobrança, preço progressivo, autenticação OTP e entrega manual já existentes. Não implementar split/comissão, Checkout Pro, Payments API, armazenamento de cartão ou refatoração geral.

## Decisions

### Contas e autorização

Cada fotógrafo usa sua própria aplicação e credenciais Orders, verificadas no servidor por GET /users/me. OAuth foi avaliado: o contrato de marketplace/split consultado documenta Payments API e não comprova o fluxo Orders pedido. Portanto esta change usa credenciais individuais, sem presumir split ou OAuth Orders. Token e assinatura ficam em tabela dedicada de envelopes AES-GCM, com AAD de ambiente/tenant/UUID e chave mestra externa já suportada. Versões antigas são mantidas para reconciliar compras antigas. Mudança exige senha, OTP, sessão, tenant, versão e origem; reenvio usa os limites existentes. API de leitura expõe apenas dados públicos e indicadores. Credencial revogada impede novas cobranças; nunca troca silenciosamente a conta de uma tentativa.

PIX e Mercado Pago têm flags independentes, com defaults true/false. Desabilitar afeta somente emissão nova e não impede consulta/cancelamento/conciliação de tentativas antigas. Sem método disponível, manter seleção e apresentar indisponibilidade. O sistema não permite pagamentos reais por padrão: contas não identificadas como teste exigem gate operacional explícito do servidor, não habilitado nesta execução.

### Snapshot e concorrência

Uma tentativa Mercado Pago tem UUID próprio, referência externa e chave de idempotência persistida antes do POST. Seus SaleOrders/itens usam o snapshot/cotação existente e FK exclusiva, sem converter ProviderPayment legado nem PaymentGroup PIX. Dados do navegador nunca definem valor/tenant/recebedor/fotos cobradas.

Preparação persiste tentativa, revisão e total locais, sem criar SaleOrders até o submit. Submit revalida a revisão autoritativa e cria/congela os snapshots completos antes da rede, mantendo uma única tentativa ativa por cliente. O estado preparado não é uma cobrança e pode ser substituído ao editar. Depois de envio, resultado incerto bloqueia nova emissão; consulta por ID ou busca exata por external_reference reconcilia resultado perdido. Ausência na busca não prova inexistência nem autoriza recriação.

Fotos de uma tentativa submetida ficam reservadas pelo contrato de pedido congelado. Retorno para edição exige cancelamento confirmado quando a tentativa ainda pode cobrar; recusa/expiração confirmadas liberam a seleção. Fotos adicionais podem ser escolhidas sem alterar a tentativa. Novas tentativas após falha recebem token novo, UUID e snapshot novos. Aprovação tardia só confirma as fotos/valor daquela tentativa; se houver compra concorrente confirmada sobre as mesmas fotos, registrar exceção de duplicidade para revisão, sem aplicar confirmação a uma seleção diferente.

### Contrato oficial

POST /v1/orders, type online, processing_mode automatic, total_amount e payment.amount em decimal textual de duas casas, external_reference UUID e X-Idempotency-Key durável. Cartões coletados pelo Card Payment Brick de MercadoPago.js segundo a documentação específica Orders atual; a referência genérica da skill que limita Bricks a Payments está superada para esse contrato. Cartão em uma parcela; Pix via payment_method id pix/type bank_transfer. Não usar issuer_id no payment_method. Nunca persistir/logar token de cartão, CPF, PAN/CVV ou corpo bruto.

GET /v1/orders/{id} confirma estado, referência, valor, método e conta da credencial congelada. GET /v1/orders com begin_date/end_date/external_reference recupera ID perdido. Cancelamento POST /v1/orders/{id}/cancel somente é elegível em estados externos `created` e `action_required` (internos `initiated` e `pending`), conforme a referência oficial: https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-api/cancel-order/post. Se a reconciliação encontrar `processing`/`in_review`, a tentativa e seu snapshot continuam ativos e bloqueados para edição, sem chamada de cancelamento; a interface orienta aguardar o resultado. Reembolso é reconhecido por conciliação, sem botão de movimentação financeira nova nesta missão. O histórico exibe estorno e parcial confirmados.

### Estados

Entidades externas mantêm status/detail independentes. Somente order processed/accredited e pagamento processed/accredited coerentes com valor/referência/método confirmam. created -> initiated; processing/in_review -> processing; action_required -> pending; failed -> rejected (ou expired pelo detalhe); canceled -> canceled/expired; refunded -> refunded; processed/partially_refunded -> partially_refunded; charged_back -> charged_back. Estado desconhecido/inconsistência -> verification_required. Não inferir rejeição financeira de timeout/5xx/429.

SaleOrder usa confirmed somente para aprovação comprovada. Reembolso integral cancela a liberação; parcial/contestação suspendem entrega em hold, preservam timestamps/snapshots e expõem o estado financeiro exato para revisão. Nunca distribuir reembolso parcial arbitrariamente por foto. Notificação antiga não rebaixa confirmação; timestamp/revisão externa e transições financeiras conservadoras impedem regressão. Refund/chargeback confirmados são eventos posteriores válidos.

### Webhook e recuperação

Tópico online é order (singular). Roteamento por UUID opaco da conta no endpoint, sem usar user_id do corpo como autorização. HMAC-SHA256 sobre data.id da query em minúsculas, x-request-id e ts; exigir correspondência de ID query/corpo, validar user_id quando presente. Receber apenas corpo limitado e metadados permitidos. Persistir inbox durável antes de ACK 200, com digest por notificação/assinatura/request-id; não deduplicar somente ID da order pois isso perderia atualizações. Worker consulta recurso do provedor, aplica sob locks na ordem conta/cliente/tentativa e confirma atomicamente pedido/evento. Backoff, contador e lease suportam falha transitória e reinício. Poll autenticado também permite conciliar; nunca aceita status informado pelo frontend.

### UI e projeções

Solicitação adicional do proprietário: opções do cliente exibem thumbnails de Pix e Mercado Pago com texto explícito. Usar assets SVG locais provenientes dos sites do provedor/participante, sem scripts/referências externas, sem redesenhar, distorcer ou aplicar filtros aos símbolos. O thumbnail tem base branca e área de respiro comum, inclusive no tema escuro. No carrinho, a opção Mercado Pago mantém o CTA Orders e PIX aponta para o bloco de pagamento existente; no checkout, os rádios preservam os nomes acessíveis e a tokenização oficial. Não substituir o PIX manual nem confundir Pix processado pelo Mercado Pago com conferência manual.

Seguimento solicitado pelo proprietário: refinar somente o card Meios de pagamento com tokens visuais existentes, hierarquia clara, opções de PIX/MP independentes e hints acessíveis junto aos campos. Dicas detalham onde obter Public Key/Access Token/assinatura, o uso do mesmo ambiente e evento Order; nenhum segredo salvo é exibido. Copiar URL usa a própria origem da instalação e o caminho retornado da conta autenticada. Layout de uma coluna no celular, foco visível, campos de 44px e confirmação senha/OTP preservada. Cada fotógrafo continua configurando sua própria aplicação pela UI; o gate de teste do ensaio não substitui essa configuração.

CTA no carrinho, sob o total e junto ao PIX atual, leva a /library/checkout. Detector bundled não reconheceu JSX existente; o local concreto foi resolvido pelo objetivo explícito de integrar o carrinho e pelo componente existente. Tela própria mostra resumo, total, método, loading/erro/pendência, formulário oficial e retorno seguro. Instância do componente é desmontada ao sair. Compras e dashboard identificam Mercado Pago, ID de compra/pedido, método, status externo e situação financeira. Manual PIX continua manual; nenhuma ação administrativa de confirmação PIX pode confirmar Mercado Pago. CSV respeita filtros e colunas adicionais.

Consulta automática que altera estado/atividade também notifica a navegação para recarregar a quantidade do carrinho. Isso mantém a contagem coerente quando a resposta do submit se perde e o polling recupera uma aprovação. Não há reemissão nessa recuperação.

### Mínimo de compra Mercado Pago

Decisão do proprietário em 25/10/2026: aplicar piso uniforme de R$ 1,00 (100 centavos) a novas tentativas Mercado Pago, sem configuração por fotógrafo e sem alterar o PIX manual existente. A UI deve explicar o piso e não montar o Card Payment Brick para carrinho abaixo dele. Backend revalida em preparação e imediatamente antes de congelar pedidos/enviar à Orders API, preservando a seleção em recusas. O mínimo dinâmico de cada meio/bandeira informado pelo Mercado Pago continua aplicável quando for superior ao piso do produto; a integração não presume que R$ 1,00 substitui limites do provedor.

## Risks / Trade-offs

Integração do inventário: os quatro itens novos (SDK, JS, ferramenta temporária e assets) elevam a contagem reconciliada de 68 para 72. O consumidor `scripts/third_party_report.py` mantém validação estrita de sequência/contagem; atualizar sua expectativa e os testes ao atualizar o inventário, sem relaxar o contrato ou os gates de release.

Credenciais de teste e webhook HTTPS externos não são pressupostos. Testes locais simulam contratos, não comprovam aprovação real do provedor. Não acessar produção. Segurança da coleta é delegada ao SDK oficial carregado diretamente. Chave mestra e conta do provedor permanecem pré-requisitos operacionais explícitos.

## Migration Plan

Seguimento operacional aprovado em 25/10/2026: o proprietário aceitou explicitamente a janela de manutenção apresentada em release-plan.md. Implementar procedimento pontual `scripts/orders_pilot_release.py`, sem ampliar os executores/allowlists antigos nem criar deploy automático. Separar inventário somente leitura, preparação sem substituir serviços ativos e aplicação sob lock/fingerprint. A preparação constrói candidatos a partir das imagens ativas, adicionando somente mercadopago 3.6.0 ao backend e compilando frontend com Node atual/lockfile; compara distribuições para recusar deriva. Preserva APP_ENV staging/cofre existente. Backup customizado e cópia protegida do cofre permanecem no host; restauração/migration são ensaiadas em PostgreSQL temporário sem rede externa, antes da janela. A aplicação exige candidato integrado/CI aprovado e inventário inalterado. API/worker geral usam SIGTERM sem escalada; workers especializados legados só podem receber SIGINT sob opt-in, imagem/command conferidos, filas quiescentes e estado de espera compatível. Código inesperado/timeout impede migration e recupera os mesmos containers antes de DDL. Não publicar código de parada novo nos workers especializados. Retomar esses mesmos containers/imagens após DDL; substituir somente API/web/worker. Depois de iniciar 0088, não retornar automaticamente ao binário 0087: manter manutenção e evidência para recuperação compatível. Recusar dados Orders preexistentes no primeiro release. Emissões ficam fechadas por padrão; o par do proprietário só pode ser fornecido por arquivo operacional fora do Git. Receiver/worker/conciliação permanecem ativos quando novas emissões são fechadas.

Reconciliação do CI integral: testes de catálogos históricos 0069/0070 SHALL continuar congelados, excluindo explicitamente tabelas/colunas introduzidas por 0088; não alterar migrations publicadas. Ensaios que exercitam o ORM/inventário atuais SHALL migrar até 0088. O reset proprietário também SHALL classificar conta/preferências Orders como configuração por tenant e tentativas/inbox como operacionais, preservando configuração do proprietário. Um predicado compartilhado com a limpeza integral SHALL impedir inventário/execução proprietários diante de tentativa enviada/inbox em qualquer tenant, com nova conferência após os locks na execução. Nenhum reset operacional é autorizado ou executado por esta correção.

0088 adiciona configuração, credenciais versionadas, tentativa e inbox, FK de SaleOrder e finalidade de challenge. Histórico anterior preservado. Ensaiar upgrade/constraints em banco descartável. Downgrade com dados financeiros novos SHALL recusar perda. Não executar em ambientes operacionais.

Dependências de lifecycle: inventário de exclusão de cliente inclui tentativas Orders, inclusive preparações locais, evitando erro tardio de FK. O reset integral de homologação classifica configurações/cofre como preservados e tentativas/inbox como operacionais, mas recusa a execução se existir qualquer tentativa enviada ou inbox financeira; não apagar evidência que ainda possa receber atualização remota. Esta missão não executa reset.

Compatibilidade CSV: o exportador padrão conserva exatamente quatro colunas, para preservar consumidores existentes. A ação CSV financeiro detalhado opta explicitamente pelas colunas de pedido/compra/provedor/método/estados e respeita os mesmos filtros.

## Open Questions

### Baseline após correção Pillow autorizada/publicada

Em25/10/2026 os seis especializados receberam somente Pillow13, com PR258/main3d2ac6e7 e CI40206489337 aprovados; fonte/modelos/pacotes restantes preservados, schema0087/digest financeiro iguais e15 serviços saudáveis. O overlay persistente `pillow-prepare-20261025-01/active.compose.json` SHALL integrar CONFIGS/EXTRAS Orders. Inventário confere o published.json privado/fingerprint autorizado, IDs exatos e hash do overlay; não confiar apenas no pin da fonte nem reiniciar imagens antigas. A integração de main na branch Orders produziu cbb2362fcc2c3277ff1a8e7c8c4de963ea125b02; diff de backend/frontend/docker versus47af72bd é exclusivamente `Pillow>=10.0`→`Pillow==13.0.0`. Fixar esse novo snapshot e manter igualdade estrita dos runtimes futuros, sem exceção genérica no gate. Refazer preparação/backup/restore e recibo; API anterior já carregava13 e continua admitindo somente SDKmercadopago adicional.

A publicação Pillow comprovou propagação assíncrona do nginx reload ([200,200,503]→[200,200,200]). Confirmar saúde pública por polling limitado15s antes de concluir publicação ou recuperação Orders;503 persistente continua bloqueando/remantendo manutenção. Não modificar o receiver financeiro nem usar sucesso do frontend como prova de pagamento.

### Validação final na instalação de produção — decisão do proprietário em 24/10/2026

Compras da conta de teste SHALL ser identificadas explicitamente no histórico/painel. Indicadores de receita e vendas reais e CSV padrão SHALL excluí-las; CSV detalhado SHALL mantê-las com descrição TESTE, preservando os contratos de quatro/doze colunas. A classificação vem da versão da conta verificada pelo servidor, não de flag do navegador. Não alterar status, snapshots ou IDs para simular remoção dos testes.

O proprietário informou não possuir homologação privada e escolheu validar no ambiente de produção com seu administrador e seu próprio cliente, usando exclusivamente credenciais de teste. Preparar revisão, PR e plano operacional está autorizado; inventário atual, aprovação concreta de publicação/migration e acompanhamento da autenticação permanecem prévios à execução. Não há autorização de cobrança real ou disponibilização do checkout de teste aos demais clientes.

`MERCADOPAGO_TEST_CUSTOMERS` SHALL conter JSON de pares `{tenant_id, client_id}` UUID fornecidos pelo servidor. Fora de `APP_ENV=development|test`, conta Mercado Pago identificada como teste SHALL negar novas preparações/envios por padrão. Uma configuração presente também restringe desenvolvimento, permitindo testar o gate. Valor vazio, malformado, excessivo ou sem o par autenticado SHALL negar, sem revelar identificadores. Carrinho e submit SHALL usar o mesmo gate; submit SHALL revalidá-lo depois da preparação. Retirada do par não impede reconciliação/cancelamento de compras já enviadas. A disponibilidade administrativa de meios de pagamento SHALL NOT contar um checkout de teste restrito como meio geral para publicar galerias pagas ou desligar o último PIX disponível.

O Compose SHALL entregar o binding de cofre já existente também ao worker financeiro, exclusivamente ao serviço `worker`, além da API, para que inbox/polling funcionem sem navegador. Os controles de emissão SHALL ser declarados na API com defaults fechados; nenhum arquivo de segredo ou configuração operacional será alterado nesta preparação. O plano SHALL inventariar/ensaiar esse binding e a retomada de filas antes de solicitar publicação.

Autenticação real de conta/comprador de teste e webhook HTTPS dependem de acesso externo. SDK oficial 3.6.0 autorizado e instalado. Registrar bloqueios individuais em validation.md sem bloquear implementação local independente.

### Reconciliação após finalização e rotação

Tentativas enviadas continuam elegíveis à consulta periódica mesmo inativas: a cada 24 horas após estado final/hold e a cada dois minutos enquanto potencialmente ativas. Inbox pode antecipar a consulta. Assim estorno e aprovação tardia não dependem exclusivamente de callback. Após rotação, uma notificação autenticada da nova versão pode consultar a order de uma tentativa antiga somente se ambos os registros tiverem o mesmo tenant e seller_id verificado; preserva-se a FK da versão original, IDs e snapshot. Não há fallback para outro recebedor. A credencial antiga revogada continua impedindo consulta por ela; a atualização por uma nova versão válida não altera o recebedor financeiro.

Cada ciclo processa no máximo uma entrada da inbox e uma consulta agendada, sem impedir a passagem pelas filas existentes de mídia, entrega e privacidade. Respostas inconsistentes também recebem backoff; não manter consulta imediatamente elegível em loop.
