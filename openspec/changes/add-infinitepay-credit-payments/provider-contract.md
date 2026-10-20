# Contrato externo e gates — 12/10/2026

## Escopo confirmado

InfinitePay exclusivamente para cartão de crédito. PIX manual permanece no Pick-your-Pic, isolado por fotógrafo. Inicialmente o titular gerou um link pelo botão Testar API e compartilhou a resposta. Posteriormente autorizou explicitamente o executor a reproduzir esse teste para observar a rede: um clique no painel, HTTP 200, sem pagamento. Nenhuma credencial, conta ou webhook foi criado/alterado. A pesquisa complementar não emitiu novos checkouts nem modificou código.

Resultado atualizado: `research-review.md` compara fontes oficiais, os dois repositórios indicados pelo proprietário e os testes de rede. Em ensaio complementar autorizado às 18:54 BRT, uma única chamada pública `/links` sem chave/token/cookies retornou HTTP 200 e URL. A página oficial https://www.infinitepay.io/checkout publica o mesmo padrão com Content-Type JSON e sem header de autenticação. Criação sem chave foi comprovada nessas condições; finalidade das chaves do painel, autenticação da consulta e autorização individual de vendedores continuam pendentes. Canal técnico oficial identificado: `parcerias@cloudwalk.io`, publicado em https://www.infinitepay.io/desenvolvedores.

## Evidência pública

Fontes oficiais consultadas em 12/10/2026:

- [Documentação do Checkout Integrado](https://www.infinitepay.io/checkout-documentacao): `POST https://api.checkout.infinitepay.io/links`, handle/InfiniteTag, itens com preço em centavos, order_nsu, redirect_url/webhook_url; `POST https://api.checkout.infinitepay.io/payment_check` com handle/order_nsu/transaction_nsu/slug. O exemplo retorna success/paid/amount/paid_amount/installments/capture_method. A página descreve webhook de aprovação e reenvio após HTTP 400, sem contrato de assinatura/headers de autenticação apresentado.
- [Como usar o Checkout Integrado](https://ajuda.infinitepay.io/pt-BR/articles/10766888-como-usar-o-checkout-integrado-da-infinitepay): habilitação do recurso no app/web pelo titular, mesmos endpoints/schema e resposta exemplo com `checkout.infinitepay.com.br`; orienta consultar a documentação para configurar credenciais, sem indicar header/formato da API Key. Nenhum segredo deve ser solicitado no Pick-your-Pic enquanto seu uso não for definido.
- [Configurar pagamentos aceitos no site](https://ajuda.infinitepay.io/pt-BR/articles/14497696-como-configurar-os-pagamentos-aceitos-em-meu-site): o app oferece Checkout → Configurações → Meios de Pagamentos para ativar/desativar PIX/cartão e escolher assumir/repassar taxas. O artigo trata do produto Site; sua aplicação aos links da API precisa de confirmação, não pode ser inferida apenas desse menu.

O primeiro texto avulso copiado da internet foi descartado por falta de fonte confiável; não embasa o contrato nem a implementação. O segundo texto coincide com o artigo oficial [Como usar o Checkout Integrado](https://ajuda.infinitepay.io/pt-BR/articles/10766888-como-usar-o-checkout-integrado-da-infinitepay): confirma `POST https://api.checkout.infinitepay.io/links`, itens `quantity`/`price`/`description`, `customer.name`/`email`/`phone_number`, retorno `url`, `payment_check` e webhook. O artigo orienta consultar a documentação para configurar credenciais, mas não especifica onde enviar a chave ou seu formato; isso reforça a pendência da API Key sem fechar o protocolo. A URL de checkout mostrada pelo artigo é `checkout.infinitepay.com.br`; a chamada de teste anterior desta conta retornou `checkout.infinitepay.io`. O adaptador aceita somente esses dois hosts exatos HTTPS, ambos documentados ou observados; não aceita subdomínios arbitrários.

Consequência: o contrato público é suficiente para implementar localmente o cliente HTTP de criação e consulta com fixtures, sem inventar headers. O painel oferece API Keys, porém o proprietário decidiu expressamente testar este fluxo sem a chave; a chamada pública `/links` observada e o exemplo oficial não enviam credencial. Este perfil não cria campo de chave, não armazena segredo e não presume `Authorization: Bearer`. A chave do painel fica registrada como contexto, não como requisito do primeiro fluxo.

O texto recebido sugere confirmar pagamento com base no `order_nsu` do webhook. Isso não é evidência de pagamento: o payload é remoto e não assinado na documentação pública consultada. O servidor deve localizar a tentativa por ID próprio, comparar o `order_nsu` congelado e então consultar `payment_check`; somente a resposta autoritativa que passar validação pode alimentar a aplicação financeira. O webhook oficial usa `invoice_slug` no exemplo, que deve ser mapeado para o campo `slug` da consulta, sem confiar em `amount`, `paid_amount` ou `capture_method` do webhook.

Os endpoints antigos da ajuda encontrados na investigação anterior não devem substituir os endpoints da página atual. Identificadores recebidos no browser/webhook são dados não confiáveis até a verificação autoritativa vinculada ao snapshot.

## Gates pendentes

### Informação adicional do titular — chave do Checkout Integrado

Em 12/10/2026, o proprietário informou possuir uma chave/token criada em **API/keys**, na tela **Gerencie as chaves do checkout integrado**. Nenhum valor da credencial foi solicitado, recebido, armazenado ou utilizado. Isso complementa a investigação baseada inicialmente em InfiniteTag e exige identificar o contrato correspondente antes de definir o campo de credencial e sua utilização.

A documentação pública e o artigo oficial acima foram consultados novamente após esse relato: os exemplos de `/links` e `/payment_check` continuam identificando a conta por `handle`, sem campos ou headers de API Key. Em 12/10/2026, o proprietário decidiu explicitamente prosseguir para ensaio usando o contrato documentado sem configurar API Key; o adaptador não solicita nem persiste chave. Esta decisão vale para o fluxo atual; se o provedor recusar uma chamada, registrar a resposta sem expor segredos e reavaliar com evidência oficial, sem improvisar autenticação.

### Informação adicional do titular — seletor PIX da conta

Em 12/10/2026, o proprietário confirmou que desligar PIX nas configurações do Checkout Integrado de uma conta também remove essa modalidade dos links criados via API. O onboarding por fotógrafo orientará habilitar cartão, desligar PIX na própria conta e informar a InfiniteTag correspondente no PickYourPic. Essa confirmação resolve a orientação operacional pretendida; continua prevista uma verificação visual de link hospedado sem pagar antes de liberar cobrança real. Isso não resolve os demais gates de autenticação, confirmação, recuperação ou testes operacionais.

O objetivo de configuração autônoma por fotógrafo permanece pela InfiniteTag própria no tenant. A API Key não integra esta implementação porque o proprietário decidiu seguir com o fluxo público sem chave. Nenhum valor foi solicitado, recebido, armazenado ou incluído no projeto. Se evidência oficial futura demonstrar que uma credencial é necessária no servidor, a feature deverá voltar a ficar indisponível até autorizar e implementar armazenamento seguro isolado, rotação/revogação e leitura sem revelar o valor.

### Inspeção direta do Checkout Integrado — 12/10/2026

O titular anexou o texto da documentação interativa e uma resposta de Testar API contendo `url` sob `https://checkout.infinitepay.io/<handle>/<identificador>`. A inspeção do link existente confirmou página hospedada pelo provedor, recebedor exibido e item de exemplo de R$ 10,00. A etapa seguinte exige telefone, e-mail e nome; nenhum dado foi preenchido. A existência da página não comprova pagamento, autenticação da chamada de criação ou exclusividade de crédito. Identificadores e dados reais não foram copiados para fixtures/Git.

Na aba autenticada já aberta pelo titular, `https://app.infinitepay.io/external-checkout#configuracoes`, foram observados:

- **Meios de pagamento:** controles separados Cartão/Pix e botão Salvar, com Pix habilitado. A descrição do painel vincula a escolha ao Link. Essa é evidência específica do Checkout Integrado, mais forte que o artigo anterior sobre Site; ainda falta ensaio do efeito nos links API, escopo sobre links anteriores/outros usos e confirmação de crédito exclusivo. Nenhum seletor foi alterado nem salvo.
- **API Keys:** a própria tela informa que as chaves autenticam o Checkout Integrado; há ações de criação/exclusão. Não foi criado, excluído, copiado ou usado segredo. A tela não apresentou contrato de header/parâmetro ou documentação de assinatura. Portanto a existência/finalidade geral da chave está confirmada na UI; seu uso exato continua pendente.
- **Documentação autenticada:** mantém exemplos por handle, sem instrução de autenticação por chave ou assinatura de eventos. Não presumir que o botão Testar API reproduza a autenticação exigida de um servidor externo.

Próxima ação externa concreta: encaminhar ao suporte técnico humano as perguntas de `support-request.md`. Essa mensagem está preparada, não enviada. A preparação local independente continua autorizada; não há necessidade de fornecer a chave no chat.

| Gate | Evidência necessária | Estado e alcance |
|---|---|---|
| G1 — exclusivo crédito | Contrato oficial ou ensaio autorizado mostrando que cada link API da conta oferece cartão e não oferece PIX; efeito das configurações e eventual abrangência sobre outros usos da conta | Relato do proprietário (12/10/2026): desligar PIX na configuração da conta também o remove dos links Checkout criados pela API. O fluxo por fotógrafo exigirá cartão ligado e PIX desligado na própria conta. Registrar como confirmação operacional do titular; antes de liberar cobrança real, comprovar em link hospedado sem concluir pagamento e verificar que ele não oferece PIX. |
| G2 — origem e verificação | Chamada de retorno correlacionada ao pedido e consulta `payment_check` server-to-server; webhook assinado se vier a ser usado | O fluxo inicial selecionado usa os parâmetros do retorno apenas como candidatos, carrega a compra por UUID/order_nsu e chama `/payment_check` com handle e os IDs do provedor; somente resposta compatível confirma. Webhook fica fora do fluxo até documentar assinatura. O ensaio prático autorizado deve provar que `/payment_check` aceita os identificadores da compra e rejeita transação/método/valor incompatíveis. |
| G3 — recebedor e resposta | Conferência da conta do fotógrafo, habilitação integrada, schema/URLs válidos de criação, tipos e significado exato de amount/paid_amount/taxas | Parcial: schema básico, resposta `url` e campos de status estão documentados. A InfiniteTag é a identificação declarada pelo fotógrafo; a UI a mantém como autodeclaração e `ownership_verified=false`, sem alegar prova remota de titularidade. O proprietário confirmou que desligar PIX no Checkout Integrado remove essa modalidade dos links API. O ensaio deve conferir recebedor e métodos no link hospedado. A comparação usa `amount` igual ao total comercial; taxas adicionais de `paid_amount` não são contabilizadas como receita. |
| G4 — recuperação | Idempotência externa, timeout na criação, retorno ausente, expiração/cancelamento e pagamentos tardios | Parcial. Uma resposta conhecida permite seguir o link; timeout na criação nunca será repetido automaticamente. A documentação diz que o comprador deve clicar em “Continuar” para retornar; se pagar e fechar a página, sem webhook assinado conhecido o sistema não recebe os IDs para consultar. A compra permanece em conciliação, sem liberar as fotos nem duplicar cobrança. |
| G5 — validação operacional | Conta/ambiente de teste disponíveis, limites, testes de transação autorizados, acompanhamento de estorno/chargeback e evidências de homologação | O proprietário autorizou o ensaio com sua conta e forneceu sua InfiniteTag. A execução ainda depende de preparar/publicar a versão validada em homologação com autorização operacional própria, combinar carrinho e valor e conferir o link antes de pagar. Mock não prova recebimento real, taxas, estorno nem chargeback. |

## Solicitação de esclarecimento preparada

Estas perguntas estão prontas para o titular consultar no suporte oficial; não foram enviadas em seu nome:

1. O proprietário confirmou que desligar PIX em Checkout → Meios de Pagamento vale para links API. Confirmar o alcance sobre links anteriores e outros canais da conta e se existe controle por link.
2. Se webhook for usado, há assinatura? Qual é o contrato de headers, algoritmo, segredo, timestamps, replay e retentativas? Como configurar sem expor segredo ao comprador?
3. `payment_check` garante que a transação foi paga à handle informada e corresponde ao order_nsu/slug informados? Quais respostas retornam para cada identificador incorreto e para conta estrangeira? Qual a definição de amount/paid_amount quando o vendedor assume ou repassa taxas?
4. `/links` é idempotente por order_nsu? Como recuperar após timeout sem receber URL/slug/NSU? Links são únicos, reutilizáveis ou expiram? Como invalidar uma cobrança e tratar pagamento tardio?
5. Há ambiente de testes e perfil autorizado para plataforma com vários vendedores recebendo diretamente em contas próprias? Há eventos/consulta de estorno e chargeback aplicáveis ao Checkout Integrado?

## Decisão para o fluxo inicial

O proprietário autorizou prosseguir sem API Key, usando os exemplos públicos, e a confirmação via retorno mais `/payment_check`, alternativa explicitamente documentada para verificação sem webhook. O callback do navegador não é prova; a aplicação financeira depende apenas do resultado da consulta autenticada pela relação handle/order_nsu/transaction_nsu/slug e das verificações locais de valor/método/tenant.

Não implementar webhook sem contrato de assinatura. A confirmação via retorno não cobre o caso em que a cliente paga e fecha a página sem clicar “Continuar”; esse cenário permanece pendente para conciliação, até obter assinatura ou operação de recuperação documentada. Testes locais não ativam conta nem substituem o ensaio prático autorizado.

## Revalidação de documentação e incidente de produção — 20/10/2026

A [Central de Ajuda oficial do Checkout Integrado](https://ajuda.infinitepay.io/pt-BR/articles/10766888-como-usar-o-checkout-integrado-da-infinitepay), atualizada no dia da consulta, agora documenta `X-Api-Key` em `POST /links` e `POST /payment_check`. A mesma página diz que a chave é opcional para criação básica por InfiniteTag e necessária para opções avançadas; para `payment_check`, o exemplo inclui a chave. A [documentação oficial do Checkout](https://www.infinitepay.io/checkout-documentacao) ainda mostra exemplos por handle sem header e não resolve a divergência. A integração local envia ambas as chamadas sem API Key, e nenhuma credencial foi lida, recebida ou armazenada. Não há evidência local de que a consulta atual esteja autenticada conforme o contrato vigente; o ensaio oficial de pagamento permanece bloqueado até esclarecimento e caminho de segredo por tenant aprovado.

Inspeção de produção somente leitura, filtrada pela referência curta `e2194ce5`: o registro é um `ProviderPayment` de 5 centavos em `verification_required`, associado a um `SaleOrder` ainda `pending`. A URL de checkout, NSU de transação e confirmação local estão ausentes; a tentativa está `unknown` com categoria padrão `transport_unknown`; não há recibo registrado, e os logs da API não contêm o UUID completo. Esses fatos descrevem somente o estado persistido. Eles não provam que `/links` falhou antes da criação remota. O código define o estado incerto antes da chamada e não persiste resposta HTTP, mensagem técnica ou URL inválida; qualquer resultado não aceito fica com a categoria genérica. Por isso a causa externa exata permanece desconhecida e a compra deve continuar protegida até consulta no painel/suporte InfinitePay pelo titular.

O valor informado pela interface não foi normalizado nem corrigido: o banco contém `total_cents=5`, compatível com R$ 0,05. A documentação consultada não declara um mínimo para `/links`; o mínimo de R$ 1 documentado em outra página é para InfiniteTap, outro produto, e não permite concluir que esse pedido foi recusado por valor. Não reemitir esse pedido nem alterar seu meio com base nessa hipótese.

**Ação externa pendente:** o titular deve localizar no painel InfinitePay a compra pelo `order_nsu` ou consultar o suporte oficial e obter confirmação se o link foi criado, se houve pagamento e qual foi a resposta da criação. Não enviar mensagem em nome do titular nem efetuar consulta/cobrança remota neste trabalho.
