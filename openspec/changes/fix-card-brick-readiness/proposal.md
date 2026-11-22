## Why

O piloto supervisionado identificou campos do Card Payment Brick ilegíveis no tema escuro e carregamento intermitente sem recuperação clara. O timeout existente testa a presença do controlador, embora o SDK possa retornar controlador antes de onReady.

## What Changes

- Isolar o formulário oficial em superfície clara legível, preservando o tema do restante da página.
- Basear prontidão em onReady, limitar a espera inclusive pelo script e oferecer recarga explícita sem enviar pagamento.
- Evitar remontar o Brick apenas porque mudou a referência do callback de envio.
- Consolidar evidências dos testes manuais já concluídos e verificar o resultado publicado sem novas cobranças.

## Capabilities

### New Capabilities
- `card-brick-readiness`: prontidão e recuperação do formulário seguro.

### Modified Capabilities

Nenhuma mudança de contrato financeiro.

## Impact

Frontend checkout, testes focados e OpenSpec. Base main db839cc6 inclui PR295 e PR296/0090. Nenhuma alteração backend/schema/credencial. Publicação serializada com o outro chat; nunca publicar backend antigo nem executar migration nesta correção.
