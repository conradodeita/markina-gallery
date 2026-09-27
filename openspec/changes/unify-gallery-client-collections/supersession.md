# Reconciliação de mudanças OpenSpec ativas

Esta change substitui somente os requisitos de criar, navegar e operar uma galeria privada derivada para **novas** jornadas. Migrations, rotas e snapshots legados permanecem para leitura/compatibilidade; dados fora da limpeza pontual de homologação exigem migração inventariada própria. Tarefas antigas ainda abertas não devem ser retomadas se recriarem a derivação.

| Change ativa anterior | Parte substituída | Parte ainda aplicável |
| --- | --- | --- |
| `add-derived-client-galleries`, `complete-private-gallery-operations-and-sales` | Criação/entrada de derivada e editor privado como fluxo novo | Leitura histórica e proteção de pedidos já criados |
| `consolidate-shared-private-galleries-and-progressive-sales` | Membros de derivada como audiência de fotos novas | Preço progressivo, snapshots e isolamento de compras |
| `unify-gallery-presentation` | Segunda tela operacional “Minha galeria” | Apresentação mobile de duas colunas na Coleção |
| `align-admin-gallery-wizard-and-folder-ownership` | Criação de pasta particular em editor privado | Etapa Imagens para pastas comuns e pipeline de JPEG |
| `unified-client-cart-and-pix` | Dependência de ID derivado em novo pedido | Carrinho único, PIX, revisão e pagamento por grupo |
| `improve-gallery-and-client-data-lifecycle` | Derivada como novo contêiner obrigatório | Proteção de histórico e exclusão inventariada fora da limpeza autorizada |
| `productionize-facial-search` e `integrate-private-facial-filter` | Criação de derivada pela primeira seleção facial | Consentimento aplicável, isolamento do snapshot e resultados apenas no acervo autorizado |

O contrato final está nos delta specs desta change. Antes de implementar qualquer tarefa remanescente das changes listadas, comparar seu comportamento com esses delta specs e com `ROADMAP_ARQUITETURA.md`; não arquivar nem marcar tarefas antigas por efeito desta nota. A sincronização das specs principais e o arquivamento desta change aguardam revisão humana após a validação completa.
