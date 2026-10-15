# Design

## Context

O upload de pasta privada usa `register_folder_photo_asset`, o endpoint comum de fonte e `enqueue_derivatives`, igual ao fluxo público. `generate_derivatives` cria `thumbnail`, `client_preview` protegida e `admin_preview`, limitando dimensões e retirando metadados. As grades em `frontend/app/admin/galleries/[galleryId]/page.tsx` e `GalleryPresentation` usam a URL de `client_preview` em cada `<img>` sem indicação de carregamento tardio.

## Goals / Non-Goals

**Goals:** evitar que fotos abaixo da área visível sejam transferidas antes de o usuário se aproximar delas; preservar ampliação e autorização.

**Non-Goals:** mudar a resolução/qualidade de cada JPEG, regenerar derivados existentes, alterar cache HTTP, gerar novas variantes ou alterar o fluxo de upload.

## Decisions

- Nas duas listas de fotos do painel privado, usar `loading="lazy"` e `decoding="async"` nas imagens.
- Em `GalleryPresentation`, introduzir opção explícita para adiar somente as imagens dos cards da galeria privada. A rota da cliente privada ativa essa opção; a apresentação pública mantém seu comportamento atual. O modal ampliado continua usando a URL existente e não recebe `loading="lazy"`.
- A solução usa mecanismo nativo do navegador, sem nova dependência ou chamadas de API de mutação. Não promete um limite de downloads exato: o navegador decide a distância de pré-carregamento.

## Risks / Trade-offs

- [Uma imagem ainda pode carregar antes de entrar na tela] → comportamento normal de `loading="lazy"`; validação deve conferir o atributo e a navegação, não afirmar economia fixa.
- [Conexão lenta pode exibir foto somente ao aproximar-se dela] → manter dimensões/estrutura do card e conferir a apresentação ampliada.

## Migration Plan

Sem migration ou alteração persistente. Deploy depende de gate próprio de homologação.
