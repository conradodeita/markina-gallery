# Validação — carregamento de imagens privadas

## Diagnóstico

- O upload privado registra o arquivo em `PhotoAsset`, usa o mesmo endpoint de fonte e `enqueue_derivatives` das pastas públicas. `generate_derivatives` cria uma `client_preview` protegida, limitada a 1600 px de largura no caminho comum ou 1980 px no caminho de alta resolução; salva JPEG sem EXIF. Portanto, a galeria privada não serve o JPEG original na grade.
- Ambas as grades administrativas da privada e os cards da apresentação da cliente usavam a URL dessa prévia em imagens sem `loading="lazy"`. Isso pede todas as imagens renderizadas, inclusive fora da tela. O tamanho real dos JPEGs e a economia em uma pasta de homologação não foram medidos; nenhum arquivo ou dado real foi acessado.

## Alteração e evidência

- Os dois grupos de fotos do painel privado usam `loading="lazy"` e `decoding="async"`.
- `GalleryPresentation` aceita `deferGridImages`; somente a rota da galeria privada ativa a opção, tanto na grade principal quanto na revisão do pedido. O padrão da apresentação pública permanece inalterado. O diálogo ampliado continua usando a URL de prévia e sem carregamento tardio.
- Testes direcionados de apresentação compartilhada, galeria cliente e painel administrativo: 4 arquivos, 60 testes aprovados. Cobrem atributo nos cards, continuidade da ampliação e padrão público.
- `npm run lint`: 0 erros, 28 avisos preexistentes. `npm run build`: compilação, TypeScript e 22 páginas estáticas aprovados. `openspec validate defer-private-gallery-image-loading --type change --strict --no-interactive` e `git diff --check`: aprovados.

## Limites e escopo

- O navegador decide quais fotos estão próximas o suficiente para pré-carregar; esta mudança não promete número fixo de requisições ou economia de bytes.
- Cada prévia continua na resolução e qualidade atuais. Reduzir o peso individual exigiria variante protegida menor ou uma política de compressão adicional, com especificação, compatibilidade e validação próprias. A ampliação e a segurança atuais foram preservadas.
- Sem migration, API, alterações em arquivos de mídia, dados, backend ou deploy. O worktree isolado evita incorporar mudanças locais em andamento no checkout principal.
