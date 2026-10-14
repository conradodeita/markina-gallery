## Context

Veja `proposal.md`. A aplicação só possui referências `storage_key` de fotos; não há importação, processamento, volume de prévias ou endpoint de mídia. As mudanças de galerias derivadas exigem prévias protegidas para cliente e prévias administrativas para conferência.

## Goals / Non-Goals

**Goals:**
- Criar derivados locais privados, idempotentes e vinculados à foto.
- Aplicar proteção no arquivo entregue ao cliente e autorização no backend para cada requisição.
- Permitir ampliação de conferência administrativa sem expor ou baixar originais.

**Non-Goals:**
- Armazenar RAWs, editar imagens, servir Google Drive como CDN ou disponibilizar URLs públicas.
- Garantir impossibilidade de captura de tela, servir originais ou automatizar entrega por Google Photos.

## Decisions

### Derivados em volume local exclusivo

Miniaturas e prévias serão gravadas em volume dedicado da Markina Gallery, separado de banco e de qualquer outro projeto. O original não será exposto pelo servidor web. Google Drive permanece cópia/arquivo frio, não rota de entrega.

### Variantes por papel e resolução

O processamento criará miniatura e prévia protegida para cliente, com marca d'água efetivamente incorporada ao bitmap. A prévia administrativa terá limite de resolução próprio e não receberá marca d'água, mas será acessível somente a sessão admin. Isso preserva conferência sem transformar a interface em download de original.

### Autorização antes de abrir o arquivo

Endpoints recebem identificador de foto, derivam o papel da sessão e verificam associação à galeria derivada antes de localizar qualquer path. Paths não serão aceitos do navegador. O acesso é auditado sem registrar URL ou conteúdo da imagem.

### Processamento em fila

Geração e regeneração serão jobs idempotentes; a interface exibe estado processando/indisponível em vez de tentar servir arquivo parcial. Uma implementação síncrona foi descartada para evitar bloquear APIs e tornar importações frágeis.

## Risks / Trade-offs

- [Disco local insuficiente] → derivados limitados, medição de capacidade e bloqueio preventivo conforme política do produto.
- [Acesso administrativo indevido] → autenticação de papel, auditoria e nenhuma URL pública.
- [Proteção visual insuficiente] → aviso de direitos autorais e comunicação de que captura de tela não pode ser impedida totalmente.
- [Falha de job] → estado explícito, retentativas e processamento idempotente.

## Migration Plan

Criar metadados aditivos para derivados e jobs, adicionar volume exclusivo ao Compose da Markina Gallery e validar com imagens sintéticas. Em homologação, apresentar inventário de volumes, tamanho, portas e impacto zero antes de qualquer alteração no servidor; reverter removendo apenas serviços/volume identificados da Markina sem apagar originais ou dados de outros projetos.
