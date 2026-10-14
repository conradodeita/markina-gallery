# Design

## Decisões

- A atividade recente será a última visualização de prévia protegida registrada em `PhotoView.last_viewed_at` para a Galeria pública ou galeria privada correspondente, sempre filtrada pelo tenant atual.
- Quando não houver visualização, a data do vínculo (`ParentGalleryRegistration.created_at`) servirá como fallback. Clientes sem ambas as datas ficam ao final. Empates serão resolvidos pelo nome e identificador para manter a lista estável.
- A API devolverá `last_access_at` junto a cada cliente, calculada no servidor; o frontend apenas renderizará a ordem recebida.
- A grade terá uma coluna em qualquer largura. O estado aberto/fechado e o conteúdo do menu recolhível existente não serão alterados.

## Alternativas consideradas

- Ordenação por nome: não representa atividade recente.
- Atualização do schema para um timestamp de sessão: desnecessária, pois `PhotoView` já registra a última visualização protegida.

## Limites

A atividade representa a última prévia protegida solicitada, não apenas uma visita à página sem abrir prévias. Para clientes sem prévia visualizada, a ordem representa a criação do vínculo.
