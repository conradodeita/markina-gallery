## 1. Inventário e testes de contrato

- [x] 1.1 Mapear todos os produtores e consumidores de fotos sem pasta, registrar o inventário técnico na documentação da mudança e verificar por busca automatizada que nenhuma chamada interna fique sem classificação.
- [x] 1.2 Criar fixtures com fotos em pasta, fotos legadas sem pasta, referências derivadas, seleções e compras; verificar que os testes confirmam a preservação de IDs e relacionamentos antes da migration.
- [x] 1.3 Adicionar testes de API inicialmente falhos para recusar pasta sem galeria, foto sem pasta, divergência galeria/pasta e liberação cruzada; verificar os códigos e mensagens esperados no FastAPI.

## 2. Integridade de dados e migration

- [x] 2.1 Atualizar os modelos para exigir pasta na foto e coerência composta entre foto, pasta e galeria-mãe; verificar que a suíte de persistência rejeita vínculos inválidos.
- [x] 2.2 Criar migration aditiva que inventaria órfãos, gera uma pasta de compatibilidade determinística por galeria, associa fotos legadas e só então aplica nulidade e chaves; verificar idempotência em banco sintético.
- [x] 2.3 Cobrir upgrade e downgrade não destrutivo com galerias vazias, pastas existentes e históricos de compra; verificar que contagens, UUIDs, referências, seleções e pedidos permanecem iguais.
- [ ] 2.4 Validar a migration nos comportamentos SQLite de teste e PostgreSQL da aplicação, sem dados reais; verificar constraints, índices e plano de rollback documentado.

## 3. Contratos backend-driven do editor

- [x] 3.1 Implementar contrato autenticado de resumo do editor por galeria-mãe com etapas, conclusão, pendências, capacidades e ações permitidas; verificar paginação/escopo e ausência de originais ou dados indevidos.
- [x] 3.2 Implementar ou ajustar contratos pequenos de leitura e gravação para Ajustes, Vendas e Detalhes, retornando indisponibilidade explícita para capacidades futuras; verificar que o backend, não o navegador, decide permissões e disponibilidade.
- [x] 3.3 Consolidar os contratos da etapa Imagens para listar, criar, renomear, excluir e liberar pastas somente no contexto da galeria proprietária; verificar autorização administrativa, estados e coerência de origem.
- [x] 3.4 Fazer o cadastro e upload de novas fotos derivar a galeria exclusivamente da pasta em preparação e desativar a rota direta legada com `410 Gone`; verificar que nenhuma foto nova pode terminar sem pasta.
- [x] 3.5 Ajustar os contratos da etapa Clientes para link não listado, registros, vínculos e galerias privadas derivadas da mesma origem; verificar autenticação antes da visualização e bloqueio de referências cruzadas.

## 4. Fluxo administrativo em cinco etapas

- [x] 4.1 Transformar Galerias na entrada principal e criar rotas de nova galeria e edição contextual; verificar que URLs antigas de operações redirecionam sem criar dados ou perder um identificador válido.
- [x] 4.2 Implementar o componente acessível de etapas Ajustes, Vendas, Detalhes, Imagens e Clientes com navegação anterior/próxima; verificar foco, teclado, indicação da etapa atual e retomada após recarregar a página.
- [x] 4.3 Implementar Ajustes, Vendas e Detalhes consumindo exclusivamente os contratos do backend; verificar estados de carregamento, vazio, erro, salvamento e capacidade indisponível sem valores simulados.
- [x] 4.4 Implementar Imagens com cartões de pastas, capa autorizada, contagem, ordem, estado, upload, prévias, renomeação, exclusão segura e liberação; verificar que todos os comandos permanecem dentro da galeria selecionada.
- [x] 4.5 Implementar Clientes com link não listado, busca/cadastro, responsáveis vinculados e acesso às galerias privadas derivadas; verificar que a interface não apresenta senha pública nem catálogo pesquisável.
- [x] 4.6 Remover botões e formulários globais de criação de pasta ou upload e atualizar dashboard, navegação e estados vazios para conduzir primeiro à galeria; verificar por teste de componente e revisão das rotas administrativas.

## 5. Qualidade funcional e visual

- [x] 5.1 Criar testes frontend para a sequência completa, retorno entre etapas, falhas do backend, ausência de duplicação e indisponibilidade comercial; verificar a suíte de componentes sem mocks de autorização ou registros persistentes no browser. Evidência: `frontend/app/admin/galleries/gallery-editor.test.tsx` cobre sequência, retorno/avanço contextual, erro de contrato, filtro de responsável já vinculada e indisponibilidade comercial; `npx vitest run app/admin/galleries/gallery-editor.test.tsx --pool=threads --maxWorkers=1` (10 testes), `npx eslint app/admin/galleries/gallery-editor.test.tsx` e `npx tsc --noEmit` passaram em 2026-08-28.
- [x] 5.2 Executar o fluxo funcional com dados sintéticos: criar galeria, percorrer etapas, criar duas pastas, carregar JPEG, liberar uma pasta e vincular cliente; verificar que a outra pasta permanece administrativa e que a cliente vê somente referências autorizadas.
- [ ] 5.3 Revisar a interface em desktop e smartphone conforme as referências de fluxo e as diretrizes visuais próprias da Markina; verificar legibilidade, responsividade, estados vazios, confirmações e prévias protegidas.
- [x] 5.4 Executar `ruff check backend/app backend/tests`, testes backend, lint, testes e build frontend; registrar comandos e resultados, mantendo qualquer falha como tarefa aberta.

## 6. Documentação e preparação de homologação

- [x] 6.1 Atualizar documentação operacional e de arquitetura com a hierarquia galeria-mãe → pasta → foto → referências derivadas e verificar que não reste orientação de upload avulso.
- [ ] 6.2 Manter estes artefatos e checkboxes sincronizados durante a aplicação e validar a mudança com OpenSpec em modo estrito; verificar que proposal, specs, design e implementação permaneçam coerentes.
- [x] 6.3 Preparar roteiro de validação humana das cinco etapas e critérios de aceite para o fotógrafo, sem arquivar a mudança antes da aprovação visual; verificar que o roteiro usa somente dados sintéticos.
- [x] 6.4 Antes de qualquer homologação, apresentar inventário do host compartilhado, backup exclusivo do Markina, comandos Compose explicitamente limitados ao projeto e plano de impacto zero; verificar aprovação explícita antes de executar deploy.
