## 1. Capa limpa e horizontal

- [x] 1.1 Validar JPEG horizontal após orientação EXIF antes de escrita/seleção/enqueue, inclusive seleção legada; testar horizontal, vertical, quadrado, EXIF e preservação da capa anterior/fotos comuns. Evidência: casos direcionados de orientação aprovados no pytest; execução conjunta de capas teve 14 aprovados e um fixture legado sem dimensões, em correção.
- [x] 1.2 Entregar derivado limpo somente nos contextos de capa autorizados; testar capas existentes, ausência do derivado, acesso indevido e manutenção da proteção da mesma foto no acervo. Evidência: cenários privados (com/sem derivado) aprovados; público autenticado/capability, ausência de arquivo e mesma foto protegida aprovados; 2 cenários administrativos legados aprovados.
- [x] 1.3 Atualizar orientação/mensagens da etapa 03 e layout de capa integral responsiva; validar erros de upload, título e proporção com testes direcionados e inspeção visual mobile/desktop. Evidência: testes do editor incluem rejeição 422 sem trocar capa e retry; apresentação compartilhada preserva proteção do acervo. QA local nas quatro larguras confirmou proporção 1600:900 e object-fit contain.

## 2. Aparência global

- [x] 2.1 Implementar preferência Claro/Escuro/Sistema no topo, persistência e aplicação antes da pintura; testar recarga, sistema, armazenamento indisponível e integração com PWA. Evidência: 4 testes de theme-control aprovados e 3 de instalação preservados; bootstrap e storage sem dados pessoais.
- [x] 2.2 Revisar tokens, CSS compartilhado e módulos para os dois temas sem alterar mídias/QR; verificar contraste e ausência de overflow nas telas de entrada, dashboard, editor, biblioteca, galeria, carrinho, pagamento e diálogos em 360/390/768/1440 px. Evidência: 48 combinações página/tema/largura sem overflow ou erro JS, mais PIX/consentimento/visualizador em cada combinação. Contraste direcionado sem violações nos textos amostrados após correções de badges/links; QR conserva superfície branca.

## 3. Validação e documentação

- [x] 3.1 Executar testes direcionados, lint/typecheck/build e OpenSpec estrito; registrar evidências e limites, atualizar documentação/mandato sobre exceção de capa e revisar diff sem suíte completa local. Evidências e comandos em validation.md.
- [x] 3.2 Entregar implementação local e registrar dependência da publicação anterior e revisão humana; nenhum deploy, backfill ou alteração de dados reais sem aprovação operacional específica. Continuidade reconciliada; publicação/revisão humana pendentes, sem bloquear o rebrand local autorizado.
