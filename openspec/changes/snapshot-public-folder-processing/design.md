# Design

## Decisões

1. Toda pasta nova de conteúdo recebe uma linha `FolderProcessingSettings` própria na mesma transação da criação, com `preview_mode = custom` e `facial_mode = on`.
2. Pastas públicas começam em 50%/0,0 EV; pastas privadas começam em 75%/0,0 EV. Nenhuma configuração de galeria ou de outra pasta é copiada na criação.
3. Gates globais, rollout da galeria, autorização e privacidade facial continuam aplicáveis às pastas públicas. Pastas privadas mantêm reconhecimento facial permitido por pasta e ajuste sempre ativo.
4. Pastas públicas existentes recebem um snapshot aditivo na migration 0079, calculado dos parâmetros efetivos da galeria no momento da migration, e o ajuste fica ligado. Esse backfill único não cria herança para futuras pastas.
5. A API de configuração da pasta não oferece modo `inherit`. O painel apresenta a configuração efetiva da própria pasta e seus controles explicitamente.
6. Alterar a configuração da galeria não modifica nenhuma pasta existente nem os defaults usados na criação. Alterar uma pasta continua isolado e invalida/reagenda somente trabalho daquela pasta conforme os contratos existentes.

## Migration

A migration `20261014_0079` deriva de `20261014_0078` e insere somente linhas ausentes em `folder_processing_settings` para pastas de conteúdo públicas (`audience_scope = 'all'` ou `NULL`) sem galeria derivada. Ela deriva intensidade e exposição de `gallery_preview_settings`, liga o ajuste (`custom`) e inicia face permitida (`on`), aplicando defaults de 50%/0,0 EV quando não houver configuração. Não modifica linhas já explícitas, linhas privadas, fotos, derivados ou estados de publicação. O downgrade preserva as linhas materializadas para evitar apagar configurações que possam ter sido editadas depois; a reversão do código não depende de remover essas configurações.

## Testes

Cobrir defaults próprios na criação pública e privada mesmo quando a galeria tem parâmetros diferentes, ajuste sempre ligado, isolamento entre galeria e pasta, independência entre pastas, migration de registros públicos existentes e preservação do padrão privado.
