# Design

## Context

O painel já identifica saldo insuficiente e a área de Créditos já apresenta o catálogo autorizado pelo servidor. O bloqueio não deve expor como o backend consulta ou reserva créditos. O título “Ritual de publicação” nomeia uma lista existente no painel, sem alterar suas ações.

## Decisions

1. **Mensagem orientada à ação:** na Visão Geral e em Créditos, manter o título “Saldo insuficiente para novos uploads”; remover a explicação técnica e apresentar um link “Adquira um pacote →” para `/admin/credits#credit-packages`. Um `CreditShortfallNotice` compartilhado mantém as duas superfícies consistentes. A página de Créditos continua responsável por mostrar disponibilidade e conteúdo comercial.
2. **Rótulo da seção:** usar “Prática de publicação” no cabeçalho do dashboard. A lista e os critérios atuais permanecem inalterados.
3. **Acessibilidade e compatibilidade:** usar link interno sem abrir nova aba, manter nome acessível explícito e ancorar a navegação no título da seção de pacotes.
4. **Escopo:** nenhuma regra financeira, API, publicação, reserva, upload ou ledger muda. Revisar somente os componentes e estilos diretamente envolvidos; não há limpeza geral elegível.

## Risks / Trade-offs

- Se não houver pacote ativo, o link ainda leva ao catálogo, que informa a indisponibilidade sem prometer compra.
- O texto curto não explica o cálculo interno do saldo, como desejado; os detalhes técnicos continuam nos registros e ferramentas operacionais, não no fluxo do fotógrafo.
