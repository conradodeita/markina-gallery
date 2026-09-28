# Design

## Context

`ClientCollection` monta `FolderProcessingPanel` apenas depois de abrir uma pasta, mas o painel inicia recolhido. A grade administrativa da etapa Imagens já possui um diálogo para ampliar prévias. No Acervo, o upload é sequencial, depende de submit e usa `uploadJpeg` por `fetch`, sem progresso de bytes. A criação da pasta restrita já grava uma atribuição para a cliente do card; o endpoint separado de grant permite outras atribuições. O backend autoriza prévias pelo papel e pela pasta.

## Goals / Non-Goals

**Goals:** reduzir cliques no Acervo, mostrar progresso fiel, permitir conferência ampliada e impor exclusividade às novas atribuições sem revogar acessos preexistentes.

**Non-Goals:** alterar o fluxo de upload da etapa Imagens, entregar originais, modificar o processamento de derivados, converter ou apagar pastas compartilhadas, mudar vínculos comerciais ou executar limpeza em homologação.

## Decisions

### 1. Abertura contextual do processamento

Adicionar ao painel um modo embutido usado somente no Acervo, com cabeçalho informativo sem segunda ação de recolhimento. A etapa Imagens continua recolhida. Como o painel é montado apenas dentro da pasta aberta, os efeitos de consulta e polling existentes funcionam sob demanda e são cancelados ao desmontar. Abrir não aciona PATCH ou enqueue.

### 2. Ampliação protegida

Extrair o diálogo administrativo de prévia da etapa Imagens ou usar um componente equivalente compartilhado com foco inicial, Escape, botão Fechar e retorno ao acionador. A miniatura do Acervo e as duas imagens do comparativo usam seus próprios endpoints de prévia já autenticados em tamanho maior, sem rota para original. O layout conserva `object-fit: contain` e limita a altura à viewport. Evitar duas implementações de modal com semântica divergente.

### 3. Upload automático e medição

Capturar o lote no `onChange` do input e zerar o valor após capturar os objetos `File`, para que a mesma escolha possa ser repetida. Manter envio sequencial e chave derivada do conteúdo para preservar backpressure/idempotência. Estender o utilitário de upload com uma variante de transporte que reporte bytes enviados pelo navegador; manter o caminho `fetch` atual para chamadas sem callback, preservando o fluxo da etapa Imagens. Durante hashing, mostrar “Preparando”; durante PUT, progresso por bytes e arquivo atual; em 503, mostrar espera e retentar o mesmo ativo. Registrar arquivos concluídos/falhos e oferecer ação explícita para retentar somente falhas. Impedir envio concorrente e ignorar atualização de estado após desmontagem.

### 4. Exclusividade sem migration de dados

A criação no Acervo já grava exatamente um `FolderClientGrant`. No endpoint de grant, bloquear uma nova cliente quando a pasta restrita já possui qualquer atribuição; uma repetição idempotente da atribuição existente pode continuar. O mesmo bloqueio vale para pastas legadas compartilhadas quanto a novas clientes; grants antigos continuam válidos e a remoção explícita existente continua disponível. Retirar do card o seletor e a ação de adicionar; se uma pasta legada aparecer no card, mostrar as destinatárias existentes e a opção de remover acesso, sem sugerir novo compartilhamento. Não há alteração de schema ou conversão em massa.

## Risks / Trade-offs

- [Transferência sem comprimento mensurável] → exibir estado indeterminado de envio, sem percentual inventado; contagem de arquivos continua verdadeira.
- [Falha parcial ou 503] → manter lista de falhas e chave estável; retentativa explícita não reenvia arquivos concluídos.
- [Diálogo aberto em troca de pasta] → fechar ao desmontar e restaurar foco quando o acionador ainda existir.
- [Pasta compartilhada legada] → preservar acesso e histórico; negar somente novas atribuições, sem limpeza silenciosa.

## Migration Plan

Implementar frontend e guarda backend com testes sintéticos. Nenhuma migration ou operação de banco é necessária. Validar lint, typecheck, testes, build e OpenSpec; publicar via PR/CI e deploy autorizado. Reversão de código mantém os grants existentes intactos.
