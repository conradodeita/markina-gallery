## 1. Contratos direcionados

- [x] 1.1 Adicionar teste da galeria e da biblioteca da cliente para exibir o prazo somente quando houver seleção editável sem pagamento comunicado; verificar os estados com seleção, pagamento informado e sem seleção. Evidência: contratos parametrizados reproduziram a exibição indevida nos estados sem seleção e pagamento informado, preservando o caso com carrinho editável.
- [x] 1.2 Adicionar teste da prova administrativa com tamanho válido acima de 32 px; verificar que o estilo representa o valor configurado e mantém os limites 10–96. Evidência: contrato confirmou `min=10`, `max=96` e reproduziu o teto indevido ao solicitar 64 px.

## 2. Prazo da seleção privada

- [x] 2.1 Confirmar em teste backend que a criação da galeria privada converte o prazo padrão da Galeria pública em data absoluta autoritativa, sem data móvel ou override privado implícito. Evidência: teste direcionado compara a data persistida com as duas respostas autenticadas antes/depois da alteração do padrão público e passou (`1 passed`).
- [x] 2.2 Condicionar a apresentação do prazo na galeria e na biblioteca à seleção corrente editável; verificar que pedido congelado usa apenas o estado comercial e que a expiração preserva histórico e reabertura. Evidência: galeria exige prazo vigente e carrinho positivo; biblioteca exige seleção positiva e privada ativa; contratos cobrem seleção, pagamento informado, vazio, expiração e reabertura e passaram no conjunto direcionado.

## 3. Tamanho da marca-d’água

- [x] 3.1 Remover o teto visual de 32 px da prova administrativa e manter o intervalo validado pelo frontend/backend em 10–96 px; verificar os extremos e um valor intermediário acima de 32. Evidência: a prova usa diretamente `watermark_size`; teste direcionado passou para 10, 64 e 96 px e confirmou os atributos de limite.
- [x] 3.2 Confirmar que o ajuste não reprocessa mídia existente nem altera o gerador servidor; verificar por diff e pelos testes direcionados de Configurações. Evidência: diff altera somente a prova React e testes; `backend/app/media.py`, jobs, derivados e armazenamento permanecem intactos.

## 4. Validação e entrega

- [x] 4.1 Executar somente testes frontend/backend focados, TypeScript, lint dos arquivos alterados, OpenSpec estrito e `git diff --check`; registrar evidências e reservar a suíte completa e escalabilidade para solicitação posterior. Evidência: frontend direcionado `3 files/38 passed`; backend direcionado `1 passed`; TypeScript aprovado; ESLint focado com `0` erros e seis avisos preexistentes de `<img>`; Ruff, OpenSpec estrito e `git diff --check` aprovados. Nenhuma suíte completa ou carga foi executada localmente.
- [ ] 4.2 Preparar inventário zero-impact sem migration, mídia ou dados; solicitar autorização específica antes de push, merge e deploy em homologação.
