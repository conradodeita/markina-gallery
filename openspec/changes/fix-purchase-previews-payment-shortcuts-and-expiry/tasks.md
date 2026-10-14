## 1. Prévias de compras

- [x] 1.1 Reproduzir o erro de encaminhamento em fixture autenticada e corrigir resolução de URL para miniatura/ampliação de Compras; validar caminhos históricos e operacionais, prefixo `/api` único e imagem efetivamente decodificável, sem fallback original/administrativo.
- [x] 1.2 Tratar prévia nula/falha e conservar grid/identificação; executar testes focados de biblioteca e API cobrindo pedido comunicado/confirmado, histórico retido após expiração, mídia ausente e cliente de outra identidade, sem relaxar autorização nem ocultar a compra.

## 2. Atalhos financeiros administrativos

- [x] 2.1 Disponibilizar na projeção dos cards dados mínimos por pedido/comunicação e capacidades autoritativas, reutilizando regras de Vendas e pagamentos; validar isolamento por cliente/galeria, múltiplos pedidos e consultas agrupadas sem dashboard inteiro/N+1 por card.
- [x] 2.2 Reutilizar controle compartilhado de decisão/correção nos cards da pública (ficha e resumo do editor) e da privada; testar confirmação explícita, identificação/valor do pedido, ausência de ações sem comunicação, duplo clique, conflito e erro, preservando as ações existentes em Vendas e pagamentos.
- [x] 2.3 Atualizar cards/contagens/ações após decisão e correção; validar com transportes simulados que falha WhatsApp/push não reverte pagamento e correção não envia mensagem, sem transação financeira real em homologação.

## 3. Prazo efetivo e contagem

- [x] 3.1 Conferir herança/data autoritativa e propagar campos mínimos às superfícies cliente/admin faltantes; testar privada independente/derivada, clientes com datas diferentes, ausência de data e reabertura sem reescrever prazos persistidos nem inventar vencimento global.
- [x] 3.2 Implementar apresentação compartilhada de data/hora e restante na galeria de seleção, biblioteca, ficha privada e cards administrativos; validar com relógio controlado prazo futuro/próximo/expirado, carrinho vazio, troca de prazo, refoco e transição sem números negativos ou polling de rede por segundo.
- [x] 3.3 Validar vencimento com página aberta e seleção já congelada: backend bloqueia alterações/checkout vencidos, fluxo existente de reabertura permanece e compras/prévias históricas continuam acessíveis; registrar testes focados de integração e nenhuma alteração de estado financeiro por timer.

## 4. Qualidade e entrega

- [x] 4.1 Validar visualmente em 390/768/1440 px e temas claro/escuro os três ajustes, com fotos sintéticas locais, foco/teclado, ações legíveis, grid 2/4 e sem overflow; registrar evidência sem fotos reais ou artefatos de teste no Git.
- [x] 4.2 Executar lint, typecheck/build aplicáveis e testes direcionados dos arquivos tocados, OpenSpec estrito e revisão do diff; registrar resultados preservando mudanças locais anteriores e sem suíte completa local.
- [ ] 4.3 Com autorização aplicável, publicar somente a change via PR/CI; após push encerrar execução e aguardar o proprietário conferir Actions. Registrar link/SHA sem polling nem automação; merge/deploy só após checks e inventário/plano autorizado, com verificação pontual de versão/saúde e preservação dos terceiros.
- [ ] 4.4 Após deploy autorizado, solicitar aceite humano da compra reportada, atalhos financeiros e prazo em dispositivo real; registrar resultado ou bloqueio sem efetuar decisões financeiras nem enviar notificações reais por conta própria. Não sincronizar/arquivar antes da revisão humana.
