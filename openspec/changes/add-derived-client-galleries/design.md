## Context

Veja `proposal.md`. O sistema atual ainda é um scaffolding de autenticação; a mudança introduz relações persistentes entre acervo, cliente, fotos e pedido.

## Goals / Non-Goals

**Goals:**
- Representar galeria derivada como referências privadas ao acervo-mãe.
- Isolar dados e interações por cliente e fornecer métricas reproduzíveis ao fotógrafo.

**Non-Goals:**
- Duplicar JPEGs, expor acervo coletivo, implementar biometria, checkout ou envio real de mensagens.

## Decisions

### Referência, não cópia

Uma galeria derivada conterá relações para fotos do acervo-mãe. Isso evita custo e divergência de mídia; a autorização sempre parte da galeria derivada, nunca do acervo-mãe.

### Interações por cliente e foto

Seleções, favoritos e comentários terão chaves de cliente, galeria derivada e foto. Comentários não terão destinatário público; somente autor e admin podem ler/remover.

### Receita baseada em estado congelado

As métricas usarão pagamentos confirmados e valores congelados do pedido; seleção não comprada será calculada por foto dentro do filtro atual. Agregações serão feitas no backend, com paginação para listas e TXT UTF-8 gerado sob autorização admin.

### Histórico por papel e mídia protegida

Cliente e fotógrafo consultarão o mesmo histórico de compras da galeria derivada. O cliente receberá somente a representação protegida disponível à sua sessão; o fotógrafo autenticado poderá abrir uma prévia sem marca-d'água para conferência, inclusive em ampliação. A mídia administrativa será servida por autorização de backend de curta duração, nunca por URL pública nem incluída em exportações.

### Filtro e exportação operacional

As estatísticas aceitarão filtro por cliente além de período, evento, acervo-mãe e galeria derivada. A tela HTML é a superfície estruturada de consulta; TXT UTF-8 permanece a exportação inicial de identificador e nome de arquivo. PDF e CSV não pertencem a esta entrega, podendo ser propostos depois conforme necessidade operacional.

## Risks / Trade-offs

- [Mudança da foto-mãe] → preservar histórico comercial e indicar indisponibilidade sem conceder acesso ao acervo.
- [Listas grandes] → filtros obrigatórios, paginação e exportação em fila quando exceder limite operacional.
- [Comentário abusivo] → remoção pelo fotógrafo e auditoria, sem visibilidade cruzada.

## Migration Plan

Criar migrations aditivas, testar autorização e agregados com dados sintéticos, ativar a UI administrativa e cliente, e reverter somente serviços/migration da Markina conforme checklist.
