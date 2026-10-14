## Context

A biblioteca não projeta capa embora já existam rotas autenticadas de capa pública e privada. O seletor compartilhado de pastas é textual. A correção financeira já registra estados anteriores, autor, idempotência, locks e escopo de PIX único; atualmente exige comunicação e pedido confirmados.

## Decisions

1. Remover somente botão e handler de rejeição da página cliente. APIs e feedback histórico permanecem; nenhuma mudança de ranking ou de consentimento.
2. Acrescentar `cover_preview_url` à jornada somente quando houver destino autorizado e capa pronta. Usar as rotas existentes de capa, nunca endpoint administrativo ou original. Sem capa/falha, placeholder mantém nome e navegação. Capa abre o mesmo destino de “Ver fotos”; galeria indisponível não ganha acesso pelo card.
3. Pastas em modo individual recebem primeira prévia já autorizada daquela pasta como imagem clicável no próprio botão. Manter nome, contagem, ordem, teclado, seleção ativa e modo sequencial. Não criar configuração de capa por pasta nem buscar outras fotos fora do payload autorizado. Imagens lazy, proporção horizontal e proteção de conteúdo preservada.
4. Aceitar os pares `confirmed/confirmed` e `refused/cancelled` para correção, validando todos os pedidos do grupo antes da mutação. Registrar status anterior em `PaymentConfirmationCorrection`, evento de auditoria específico de recusa e retornar a `pending_review/pending` (`reported` no grupo). Nunca confirmar automaticamente. Correção não gera evento de mensagem; decisão posterior segue versão/idempotência existentes. UI usa “Corrigir pagamento não localizado” para recusas e mantém “Corrigir confirmação” para confirmações.
5. Preservar total, itens, snapshots, cliente e histórico. Locks e escopo explícito do grupo permanecem; chamada por cliente é recusada. Nenhuma migração, exclusão, alteração de entrega ou canal financeiro novo.

## Risks / Trade-offs

Capas podem ser removidas ou ficar indisponíveis: tratar falha visual sem inventar acesso. Reabrir revisão não prova pagamento nem resolve duplicidade bancária; conferência continua manual, igual à correção existente. Não consultar endpoint de fotos inteiro por card. A capa da jornada herda o destino público/privado autorizado e a validação de mídia existente.

## Migration Plan

Implementar em branch própria baseada em develop, com testes locais e CI. Publicar PR e aguardar confirmação humana do CI; merge/deploy somente após autorização específica. Homologação visual e operação real ficam para publicação autorizada. Sem sync/archive antes da revisão humana.
