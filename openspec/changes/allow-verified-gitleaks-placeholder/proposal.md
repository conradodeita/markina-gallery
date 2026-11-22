# Exceção precisa para placeholder da varredura de segredos

## Contexto

A varredura histórica local encontrou o literal `REDACTED` em um recibo de validação antigo. O detector o classificou como `generic-api-key`, embora o texto seja um marcador de redação e não um valor de credencial. O achado está em um commit de outro branch e não no histórico do candidato SaaS, mas a CI consulta o histórico completo.

## Mudança proposta

- Registrar somente a impressão digital exata desse achado em `.gitleaksignore`.
- Documentar que a entrada foi verificada como o placeholder literal `REDACTED`.
- Manter todas as outras regras e achados da varredura ativos.

## Fora de escopo

- Ignorar regras inteiras, arquivos, diretórios ou padrões genéricos.
- Reescrever histórico Git ou alterar credenciais.
- Tratar qualquer outro achado como falso positivo sem revisão individual.

## Critérios de conclusão

- A exceção corresponde apenas ao commit, arquivo, regra e linha verificados.
- O scanner da CI, sem opções especiais, deixa de reportar esse falso positivo.
- A varredura histórica e as validações OpenSpec passam sem novos achados.
