## 1. Contratos direcionados

- [ ] 1.1 Adicionar teste da galeria e da biblioteca da cliente para exibir o prazo somente quando houver seleção editável sem pagamento comunicado; verificar os estados com seleção, pagamento informado e sem seleção.
- [ ] 1.2 Adicionar teste da prova administrativa com tamanho válido acima de 32 px; verificar que o estilo representa o valor configurado e mantém os limites 10–96.

## 2. Prazo da seleção privada

- [ ] 2.1 Confirmar em teste backend que a criação da galeria privada converte o prazo padrão da Galeria pública em data absoluta autoritativa, sem data móvel ou override privado implícito.
- [ ] 2.2 Condicionar a apresentação do prazo na galeria e na biblioteca à seleção corrente editável; verificar que pedido congelado usa apenas o estado comercial e que a expiração preserva histórico e reabertura.

## 3. Tamanho da marca-d’água

- [ ] 3.1 Remover o teto visual de 32 px da prova administrativa e manter o intervalo validado pelo frontend/backend em 10–96 px; verificar os extremos e um valor intermediário acima de 32.
- [ ] 3.2 Confirmar que o ajuste não reprocessa mídia existente nem altera o gerador servidor; verificar por diff e pelos testes direcionados de Configurações.

## 4. Validação e entrega

- [ ] 4.1 Executar somente testes frontend/backend focados, TypeScript, lint dos arquivos alterados, OpenSpec estrito e `git diff --check`; registrar evidências e reservar a suíte completa e escalabilidade para solicitação posterior.
- [ ] 4.2 Preparar inventário zero-impact sem migration, mídia ou dados; solicitar autorização específica antes de push, merge e deploy em homologação.
