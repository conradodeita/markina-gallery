# Design

## Decisões

1. `GalleryPreviewSettings` é a fonte de snapshot para os parâmetros das prévias públicas: copiar `strength` e `exposure_tenths`. Toda pasta pública nasce com ajuste ligado (`custom`), mesmo se o ajuste da galeria estiver desligado. Se ainda não existir configuração da galeria, usar 50% e 0,0 EV.
2. A configuração facial não possui um controle liga/desliga próprio da galeria. Novas pastas públicas começam com `facial_mode = on`; gates globais, rollout da galeria, autorização e privacidade permanecem inalterados.
3. Pastas públicas existentes recebem um snapshot aditivo na migration 0079, calculado dos parâmetros efetivos da galeria no momento da migration, e o ajuste fica ligado. Novas e existentes deixam de acompanhar alterações futuras da galeria.
4. Pastas privadas continuam usando as regras da change `automate-private-folder-processing`: face permitida e prévia ativa em 75%/0,0 EV por padrão; não copiam a configuração de prévia pública.
5. A API pública de pasta não oferece mais modo `inherit`. O painel apresenta a configuração efetiva da própria pasta e seus controles de forma explícita.
6. Alterar a configuração da galeria afeta apenas pastas criadas depois da alteração; não cancela nem agenda jobs de pastas existentes. Alterar a configuração de uma pasta continua isolado e invalida/reagenda somente trabalho daquela pasta conforme os contratos existentes.

## Migration

A migration `20261014_0079` deriva de `20261014_0078` e insere somente linhas ausentes em `folder_processing_settings` para pastas de conteúdo públicas (`audience_scope = 'all'` ou `NULL`) sem galeria derivada. Ela deriva intensidade e exposição de `gallery_preview_settings`, liga o ajuste (`custom`) e inicia face permitida (`on`), aplicando defaults de 50%/0,0 EV quando não houver configuração. Não modifica linhas já explícitas, linhas privadas, fotos, derivados ou estados de publicação. O downgrade preserva as linhas materializadas para evitar apagar configurações que possam ter sido editadas depois; a reversão do código não depende de remover essas configurações.

## Testes

Cobrir snapshot na criação pública com galeria configurada e sem configuração, ajuste sempre ligado, isolamento entre galeria e pasta, independência entre pastas, migration de registros públicos existentes e preservação do padrão privado.
