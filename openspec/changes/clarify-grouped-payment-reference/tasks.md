# Tasks

## 1. Projeção da compra agrupada no painel

- [x] 1.1 Rastrear as superfícies administrativas que recebem decisão por comunicação, grupo e atalho de pedido; documentar nos testes quais dados de grupo, pedidos e galerias já são retornados pela API.
- [x] 1.2 A projeção autenticada já expõe associação, código do grupo, total e pedidos/galerias vinculados via relações persistidas. Testes confirmam grupo com múltiplas galerias e IDs existentes; nenhuma migration ou novo identificador foi necessário.

## 2. Identificação e ações no painel

- [x] 2.1 Apresentar `Compra <prefixo existente do grupo>` como referência primária, listar `Pedido <prefixo existente>` por galeria e valor/composição; testes de UI cobrem localização pelo código e preservação dos códigos individuais.
- [x] 2.2 Identificar confirmação, recusa e correção como ações sobre o grupo, com total, galerias e pedidos abrangidos visíveis antes da decisão; testes cobrem ação agrupada e pedido legado isolado.

## 3. Contexto de mensagens de pagamento

- [x] 3.1 Implementar a variável contextual completa para mensagens de pagamento e atualizar templates padrão/prévias; testes cobrem grupos e pedidos individuais com os mesmos códigos existentes e o texto “da galeria sua compra”.
- [x] 3.2 Implementar e testar transformação idempotente somente das frases reconhecidas de confirmação/recusa e do aviso ao fotógrafo, preservando texto personalizado fora dos trechos, templates não reconhecidos e histórico; a prévia autenticada apresenta `before`/`after` reversíveis e não grava configuração.

## 4. Integração

- [x] 4.1 Executar testes direcionados backend/frontend, validação OpenSpec estrita e `git diff --check`; revisar diff para confirmar ausência de alteração de UUID, snapshots históricos, arquivos locais preexistentes ou operação de produção. Evidência em `validation.md`.
- [ ] 4.2 Antes de qualquer aplicação remota da transformação de template, apresentar inventário, diff/preview, backup e plano de impacto zero e obter autorização operacional explícita; registrar resultado sem alterar outros recursos.

> A task 4.2 permanece pendente: nenhuma configuração ou dado remoto foi alterado neste job. A execução remota exige a revisão e autorização operacional descritas acima.

## Workflow follow-up

- Sincronizar a spec principal e arquivar somente após implementação validada e revisão humana.
- Qualquer publicação em produção exige inventário e aprovação operacional explícita separados.
