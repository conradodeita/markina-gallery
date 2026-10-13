# Esclarecimentos técnicos — Checkout Integrado InfinitePay

Mensagem preparada para encaminhamento pelo titular ao suporte técnico humano. Não enviada pelo executor. Não anexar chave/token, dados de cartão ou comprovantes reais.

Destinatário técnico publicado em https://www.infinitepay.io/desenvolvedores: **parcerias@cloudwalk.io**. Assunto sugerido: **Checkout Integrado — contrato de API Key e autorização por vendedor em SaaS**.

Estamos integrando um sistema de venda de fotografias. Cada fotógrafo receberá diretamente na própria conta InfinitePay e configurará sua integração individualmente. Usaremos o Checkout Integrado somente para cartão de crédito, pois o sistema já possui PIX separado.

Conseguimos gerar um link no botão Testar API. Em Checkout Integrado → Configurações há seleção Cartão/Pix e API Keys, mas a documentação interativa mostra apenas handle nos exemplos de `/links` e `/payment_check`. Precisamos do contrato técnico dos seguintes pontos:

Também encontramos um cURL em https://www.infinitepay.io/checkout enviando somente Content-Type JSON e handle/itens, sem autenticação mostrada. O artigo oficial atual da Central de Ajuda diz “consulte a documentação para configurar as credenciais”, sem mostrar header/formato. No teste do painel, o navegador chama `/api/session/write-token` e depois `/api/checkout/links` em `app.infinitepay.io`, usando Authorization e cookies. Não estamos usando esses endpoints internos no SaaS. Precisamos confirmar como um backend externo deve chamar `api.checkout.infinitepay.io` e como essa autenticação se relaciona às API Keys da conta.

1. **Autenticação:** em quais endpoints a API Key é obrigatória, em qual header/parâmetro e com qual formato? Podem fornecer um exemplo oficial de requisição de servidor, com chave fictícia? A chave fica vinculada à conta, usuário, aplicação ou handle? Quais as permissões e efeitos de revogação/rotação, e há diferenças entre teste e produção? Se o endpoint público dispensa chave, qual a finalidade das chaves disponíveis no painel?

   Evidência adicional de 12/10/2026: uma chamada direta a `/links` com Content-Type JSON, handle, items e order_nsu exclusivo, sem Authorization, API Key ou cookies, retornou 200 e URL `checkout.infinitepay.io/<handle>?lenc=...`. Não realizamos pagamento. Esse fluxo sem chave é o contrato suportado para servidores SaaS? Em que situação as chaves do painel são utilizadas?
2. **Somente crédito:** o proprietário decidiu orientar cada fotógrafo a manter cartão ligado e Pix desligado na própria conta, pois o PickYourPic já tem PIX separado. Desligar Pix no Checkout Integrado garante que links criados por `POST https://api.checkout.infinitepay.io/links` não ofereçam PIX? Afeta todos os links, inclusive antigos, e outros produtos da conta? Existe configuração exclusiva por link?
3. **Confirmação segura:** os webhooks têm assinatura verificável? Qual o contrato de header, algoritmo, segredo, timestamp e replay? `payment_check` verifica conjuntamente handle, order_nsu, transaction_nsu e slug e recusa combinações de contas/pedidos diferentes? Como interpretar amount e paid_amount quando há repasse de taxas?
4. **Timeout e duplicidade:** repetir `/links` com o mesmo order_nsu devolve a mesma cobrança? Se a resposta se perder, como recuperar a cobrança sem emitir outra? Qual a regra de reutilização, validade e cancelamento do link e de pagamento tardio?
5. **Homologação:** há sandbox, cartões de teste ou procedimento oficial para validar aprovação, recusa e notificações sem cobrança real? Há restrições para uma plataforma com fotógrafos independentes usando suas próprias chaves/contas? Como consultar estornos/chargebacks aplicáveis a esse checkout?

Solicitamos documentação técnica ou encaminhamento à equipe de integrações. A documentação pública consultada é https://www.infinitepay.io/checkout-documentacao.
