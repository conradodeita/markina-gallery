# Validação — 26/10/2026

## Diagnóstico e implementação

O wrapper antigo inferia prontidão pela existência do controlador, não por onReady; controlador resolvido sem onReady evitava a mensagem de timeout. Espera pelo script não tinha limite. O callback onSubmit também estava na lista de dependências do effect de montagem.

Agora a espera de vinte segundos começa na montagem; onReady sinaliza prontidão; atraso/erro oferece recarga explícita da página, sem submit. Mudança de callback atualiza ref sem recriação. Mudança de tentativa/chave pública/valor usa componente interno com key própria e limpeza serializada da instância anterior. Não foi adicionada retentativa automática de pagamento nem coleta própria de cartão.

A regra global do tema escuro alcançava os campos DOM do SDK. Tema oficial default foi declarado e o wrapper limita estilos de input/select/textarea a fundo claro e texto escuro, inclusive placeholders. Não usa classes internas geradas nem tenta estilizar conteúdo de iframes.

## Evidências locais

- 14 testes focados em dois arquivos aprovados: checkout existente e quatro casos novos para controlador antes de onReady, script lento, onReady tardio, callback atualizado sem remontagem, limpeza e troca de tentativa com callback antigo ignorado.
- Ensaio de contraste com CSS real global/appearance/module e formulário sintético: falha anterior reproduzida no tema escuro; quatro casos corrigidos (390/1265 px, claro/escuro), contraste mínimo do texto 17,92:1. Não substitui a inspeção do SDK real.
- SDK MercadoPago.js oficial montado em fixture local usando apenas a chave pública de Teste já autorizada, sem expor seu valor e sem acessar o token. POSTs bloqueados e onSubmit desabilitado no ensaio: nenhum token de cartão ou pagamento criado. onReady ocorreu em 2,245 s no desktop e 1,343 s no mobile. Campos DOM: texto rgb(26,26,26), fundo branco. Captura desktop inspecionada após desabilitar animações de entrada; a primeira captura durante transição não foi usada como aceite.
- Scripts/capturas/relatórios ignorados em `.codex-tmp/brick-colors-qa*` e `.codex-tmp/brick-live-render*`, fora do Git. Chave pública não persistida nos artefatos.
- ESLint e TypeScript passaram após substituir reset síncrono de estado no effect por ciclo de componente com key. Build final aprovado: compilação, TypeScript e 23 páginas estáticas. OpenSpec estrito e diff check aprovados.
- Fonte oficial: [tema](https://www.mercadopago.com.br/developers/pt/docs/checkout-bricks/additional-content/set-theme), [customização Card Payment Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/additional-settings/websites/visual-customizations), [montagem/limpeza](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/cards).

## Limites e coordenação

Os ensaios locais corrigem defeitos comprovados; não demonstram causa única da intermitência observada durante controle remoto. Não declarar ausência futura de falhas de rede/SDK. A recuperação explícita protege a experiência sem liberar nova cobrança.

Leitura remota encontrou checkout c1944189 limpo e 13 serviços saudáveis. Esse inventário reduzido não é recibo de publicação. A main local de base db839cc6 contém migration 0090 do outro chat; nenhum backend/migration foi publicado por esta change. Publicação e inspeção autenticada dos campos/layouts PR295 ainda exigem candidato/CI e coordenação operacional atuais.

Revisão de manutenção: alteração limitada ao wrapper e CSS consumidores; nenhuma remoção geral, mudança de API/banco/PIX/credenciais/isolamento. Evidências manuais financeiras do proprietário foram consolidadas em external-validation.md da change Orders existente.
