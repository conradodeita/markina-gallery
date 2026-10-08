# Design

## Context

AuthEntry apresenta a mensagem do desafio/reenvio e identifica o campo como código enviado por WhatsApp. O backend mantém resposta neutra, inclusive quando suprime o envio por falta de vínculo. Não é possível anunciar bloqueio específico sem revelar elegibilidade.

## Decisions

Mensagem condicional fixa na UI de cliente para solicitação e reenvio aceitos, independente de elegibilidade. Falhas HTTP conservam tratamento atual. Campo continua presente com rótulo Código de acesso. TOTP, recuperação administrativa e seus textos permanecem próprios. Não modificar o backend nem acrescentar indicador de elegibilidade.

## Validation

Regressões com componente real e fronteira fetch simulada comprovam mesma orientação na solicitação/reenvio, preservação do contexto do link e ausência de promessa incondicional. Rodar suíte AuthEntry e controles integrados do pacote; revisão humana de homologação após deploy.
