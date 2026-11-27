# Design

## Decisions

- Novos pedidos de autoatendimento recebem 30 dias no serviço de recuperação; a API mantém o campo legado para replays idempotentes e clientes em atualização. Uma duração curta recebida em um pedido novo é recusada antes de criar operação ou reservar créditos. Retentativas operacionais herdam o prazo do pedido original; o lote administrativo de encerramento mantém seu contrato.
- O prazo vigente é calculado na conclusão transacional já existente. Históricos e operações em curso mantêm o valor persistido no pedido. Não é necessária migration.
- Reutilizar a transação de renovação do lease para registrar a contagem de objetos com conteúdo já verificado, e os checkpoints de etapa para exibir o estado do trabalho. A projeção usará contagem agregada e a etapa conhecida. Exibir progresso indeterminado enquanto se aguarda fila, preparação ou finalização; a barra só indica conclusão após a confirmação transacional da disponibilização e do débito aplicável.
- Atualizar o modelo editável de termos para futuras publicações pelo proprietário. A recuperação e a publicação de termos continuam seguindo os fluxos existentes.
