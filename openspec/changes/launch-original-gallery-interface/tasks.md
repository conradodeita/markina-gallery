## 1. Lotes, pastas e contratos backend-driven

- [x] 1.1 Modelar pasta/lote com estado de preparação, liberação, contagens e ordem; criar migration aditiva e verificar upgrade/downgrade em banco SQLite sintético.
- [x] 1.2 Implementar contratos administrativos paginados para listar, criar, renomear e consultar pastas/lotes de um acervo; verificar autorização administrativa e ausência de URLs de originais.
- [x] 1.3 Implementar upload validado de JPEG para pasta em preparação, com estado por arquivo e resposta de progresso/erro; verificar MIME, limite e isolamento em testes FastAPI.
- [x] 1.4 Implementar liberação idempotente de pasta para galerias privadas autorizadas e bloqueio de inclusão posterior; verificar que cliente não vê lote em preparação e que nova rodada exige outra pasta.
- [x] 1.5 Expor resumos mínimos de dashboard, galerias, pastas e cliente necessários às telas, sem transferir dados de terceiros; verificar contratos e autorização por papel.

## 2. Fundamentos da interface original

- [x] 2.1 Criar tokens e componentes internos reutilizáveis para navegação, botão, campo, badge, cartão, diálogo de confirmação, estados de sistema e feedback acessível; verificar testes de componente e lint.
- [x] 2.2 Criar casca administrativa responsiva com navegação e contexto de ambiente, preservando sessão e destinos controlados pelo backend; verificar desktop, tablet e estado sem dados.
- [x] 2.3 Criar casca mobile-first da cliente com cabeçalho, navegação de biblioteca e componentes de foto protegida; verificar ausência de controles administrativos e acessibilidade por teclado.

## 3. Fluxo final do fotógrafo

- [x] 3.1 Implementar dashboard operacional autoral com pendências, atalhos e resumos reais; verificar carregamento, vazio, erro e dados sintéticos autorizados.
- [x] 3.2 Implementar lista e ficha de acervos-fonte/galerias privadas com busca, filtros de estado, clientes vinculadas, clonagem e ações confirmadas; verificar consultas backend-driven e proteção de dados.
- [x] 3.3 Implementar fluxo visual de criação/edição de galeria com ajustes, permissões, prazo e mensagem dentro do escopo existente; verificar persistência por API e mensagens de sucesso/erro.
- [x] 3.4 Implementar operação de pastas e upload com miniaturas administrativas, progresso, falha, renomeação e liberação explícita; verificar que ações destrutivas pedem confirmação e que a liberação atualiza somente destinos autorizados.
- [x] 3.5 Implementar exclusão administrativa segura de pastas e galerias privadas, com decisão no backend, confirmação acessível, auditoria e preservação de histórico de compra.

## 4. Fluxo final da cliente

- [x] 4.1 Implementar biblioteca visual de galerias e pastas liberadas, com nova rodada separada de histórico; verificar propriedade exclusiva, vazio, bloqueio e expiração.
- [x] 4.2 Implementar grade e ampliador responsivos com prévias protegidas, estados `nova`, `visualizada mas não comprada` e `já comprada`, seleção, favoritos e comentários quando habilitados; verificar permissões e ausência de vazamento entre clientes.
- [x] 4.3 Implementar visão de histórico privado após expiração, com fotos compradas identificadas e sem permissão de nova seleção fora das regras; verificar contrato de cliente e renderização.

## 5. Qualidade, homologação e revisão humana

- [x] 5.1 Cobrir APIs de lote/liberação e fluxos críticos das duas superfícies com testes backend/frontend; executar `ruff check backend/app backend/tests`, `pytest backend/tests -q`, `npm run lint`, `npm test` e `npm run build`.
- [x] 5.2 Validar a mudança com `npx --yes @fission-ai/openspec@latest validate launch-original-gallery-interface --strict` e corrigir falhas antes de marcar a tarefa.
- [ ] 5.3 Preparar e executar homologação com JPEGs e clientes sintéticos, inventário de impacto zero e aprovação explícita antes de deploy; registrar versão, resultado, rollback e solicitar a validação humana somente após a interface final estar disponível.
