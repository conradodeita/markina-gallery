## 1. Capa limpa e horizontal

- [ ] 1.1 Validar JPEG horizontal após orientação EXIF antes de escrita/seleção/enqueue, inclusive seleção legada; testar horizontal, vertical, quadrado, EXIF e preservação da capa anterior/fotos comuns.
- [ ] 1.2 Entregar derivado limpo somente nos contextos de capa autorizados; testar capas existentes, ausência do derivado, acesso indevido e manutenção da proteção da mesma foto no acervo.
- [ ] 1.3 Atualizar orientação/mensagens da etapa 03 e layout de capa integral responsiva; validar erros de upload, título e proporção com testes direcionados e inspeção visual mobile/desktop.

## 2. Aparência global

- [ ] 2.1 Implementar preferência Claro/Escuro/Sistema no topo, persistência e aplicação antes da pintura; testar recarga, sistema, armazenamento indisponível e integração com PWA.
- [ ] 2.2 Revisar tokens, CSS compartilhado e módulos para os dois temas sem alterar mídias/QR; verificar contraste e ausência de overflow nas telas de entrada, dashboard, editor, biblioteca, galeria, carrinho, pagamento e diálogos em 360/390/768/1440 px.

## 3. Validação e documentação

- [ ] 3.1 Executar testes direcionados, lint/typecheck/build e OpenSpec estrito; registrar evidências e limites, atualizar documentação/mandato sobre exceção de capa e revisar diff sem suíte completa local.
- [ ] 3.2 Entregar implementação local e registrar dependência da publicação anterior e revisão humana; nenhum deploy, backfill ou alteração de dados reais sem aprovação operacional específica.
