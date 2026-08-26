## 1. Contratos e componentes de validação

- [x] 1.1 Implementar resumo administrativo autenticado e identificador não sensível de ambiente/versão; verificar testes de autorização e ausência de telefones, originais e dados de terceiros.
- [x] 1.2 Criar componentes reutilizáveis para cabeçalho de ambiente, cartões de estado, listas/grids e estados de carregamento, vazio e erro; verificar lint do frontend.

## 2. Superfície do fotógrafo

- [x] 2.1 Evoluir `/admin` para painel visual backend-driven com atalhos, resumo operacional e orientação de validação; verificar renderização com e sem dados autorizados.
- [ ] 2.2 Refinar a operação de galerias e importações com estados visuais de processamento, sucesso e falha; verificar importação JPEG sintética em homologação sem URL de original.

## 3. Superfície da cliente

- [x] 3.1 Evoluir `/library` para biblioteca visual backend-driven de galerias ativas e histórico, com estados claros; verificar autorização e estado vazio.
- [x] 3.2 Evoluir `/gallery/[galleryId]` para grade responsiva com prévias protegidas, seleção, favoritos, comentários e prazo; verificar que permissões e bloqueios vêm do backend.

## 4. Qualidade e entrega

- [ ] 4.1 Cobrir contratos de resumo e os fluxos visuais críticos com testes backend/frontend adequados; verificar `pytest backend/tests -q` e `npm run lint`.
- [ ] 4.2 Validar build, OpenSpec e os dois papéis com dados sintéticos em homologação; verificar ambiente/versão visíveis e registrar resultado operacional.
