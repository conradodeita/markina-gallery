## Why

Os testes em homologação confirmaram que o carregamento de fotos funciona, mas a etapa Imagens ainda não oferece controles suficientes ao fotógrafo e o resumo não abre uma visualização fiel da galeria. Esta mudança transforma a revisão administrativa e a visualização compartilhada em um fluxo compreensível e configurável.

## What Changes

- Adicionar hint persistente ao campo de descrição administrativa.
- Permitir configurar texto, tipografia, cor, tamanho e direção da marca-d’água.
- Permitir exclusão em massa de fotos ainda elegíveis.
- Fazer “Carregar fotos” abrir o seletor local e enviar os JPEGs na mesma ação.
- Corrigir o link não listado para abrir a galeria com autenticação e contexto adequados.
- Permitir abrir a galeria pelo resumo em modo de visualização administrativa, com aviso explícito.
- Configurar visualização individual ou sequencial das pastas e título sobre a capa.

## Capabilities

### New Capabilities

- `gallery-visualization-and-watermark-controls`: configurações visuais da galeria, marca-d’água e modos de exibição.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: ações textuais, link não listado funcional e visualização administrativa da galeria.

## Impact

- FastAPI, modelos, migrations e processamento de derivados.
- Editor administrativo Next.js, resumo e galeria compartilhada.
- Testes de API, componentes e fluxo visual.
- Não inclui WhatsApp real, reconhecimento facial ou pagamentos.
