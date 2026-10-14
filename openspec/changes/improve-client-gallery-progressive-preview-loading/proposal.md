## Why

Pastas grandes solicitam muitas prévias protegidas ao mesmo tempo quando são abertas, aumentando a espera e concentrando chamadas na API. Carregar imagens conforme se aproximam da área visível deve mostrar as primeiras fotos antes e distribuir as transferências durante a rolagem.

## What Changes

- Ativar carregamento tardio e decodificação assíncrona para as imagens da grade nas galerias autenticadas de cliente.
- Manter navegação de pastas, capa, visualizador ampliado, seleção, favoritos, filtros, URLs protegidas e comportamento administrativo existentes.
- Preservar a listagem e autorização atuais do backend; o escopo desta change é a transferência das imagens da grade no navegador.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/original-gallery-experience`: exigir que as prévias da grade da cliente sejam carregadas inicialmente perto da área visível e que outras sejam solicitadas conforme a rolagem.

## Impact

- Frontend Next.js: apresentação compartilhada das galerias e adaptadores das superfícies autenticadas pública e privada da cliente.
- Testes frontend dos contratos de apresentação e das páginas da cliente.
- Sem alteração de API, banco, rotas de mídia, arquivos de imagem ou configuração do servidor.
