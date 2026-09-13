## 1. Navegação pela Visão geral

- [x] 1.1 Transformar o nome de cada item em “Acesso recente · Galerias privadas” em link para a ficha administrativa construída com o `id` recebido; verificar no teste do painel o destino exato da galeria. Evidência: o painel usa `/admin/galleries/{id}` e o teste direcionado confirmou os destinos exatos das galerias sintéticas `gallery-1` e `gallery-2`.
- [x] 1.2 Preservar prazo, badge e acesso administrativo de galerias ativas ou bloqueadas; verificar no teste direcionado que o indicador permanece separado e o nome bloqueado continua sendo link. Evidência: o teste confirmou links para os dois estados, badges “Ativa” e “Bloqueada” e a indicação “Prazo configurado”; 6/6 testes do painel aprovados.

## 2. Validação cirúrgica

- [x] 2.1 Executar o teste direcionado de `frontend/app/admin/page.test.tsx`, ESLint dos arquivos afetados e TypeScript; corrigir somente regressões relacionadas sem rodar localmente a suíte completa. Evidência: 6/6 testes direcionados aprovados, ESLint dos dois arquivos alterados e `tsc --noEmit` concluídos com código zero; suíte completa local não executada.
- [x] 2.2 Validar a change com OpenSpec estrito, executar `git diff --check` e revisar que API, banco, autenticação, dados pessoais e demais páginas não foram alterados. Evidência: OpenSpec estrito e `git diff --check` aprovados; diff funcional restrito ao painel e seu teste, sem alterações de backend, migration, autenticação, contrato ou dados pessoais.

## 3. Entrega controlada

- [ ] 3.1 Preparar branch e commit focados, registrar inventário de impacto zero e publicar por PR com os gates obrigatórios do CI aprovados.
- [ ] 3.2 Após autorização humana explícita, integrar e publicar em homologação; verificar SHA entregue, HTTP `200` nos healthchecks e navegação do nome recente até a ficha privada correspondente.
