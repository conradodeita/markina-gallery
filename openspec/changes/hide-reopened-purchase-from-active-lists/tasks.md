# Tasks

## 1. Contrato e projeções
- [x] 1.1 Registrar regressões HTTP de ocultação imediata, carrinho vazio, histórico administrativo, isolamento, nova compra e evidência tardia; implementar classificação derivada e filtro sem alterar registros financeiros. Evidência:8 testes PostgreSQL aprovados em61,82s; regressão de ocultação falhou antes do ajuste.

## 2. Interface
- [x] 2.1 Adequar Compras ao carrinho independente e à conferência tardia; acrescentar acesso explícito ao histórico administrativo com rótulo fiel, preservando filtros/paginação e testes. Evidência:29 testes frontend aprovados em8,45s;4 regressões falharam antes da correção.

## 3. Validação e integração
- [x] 3.1 Executar regressões backend/frontend e lint/build/TypeScript/Ruff/OpenSpec/gates afetados; revisar diff e manutenção proporcional e documentar evidência. Evidência: 12 testes PG finais/616 frontend, lint sem erros/build/TypeScript/Ruff/OpenSpec135/0 e política técnica aprovados; detalhes e checkpoints em validation.md.
- [ ] 3.2 Atualizar o mesmo PR262 em draft, conferir CI final e fechar evidências do roadmap e do PR266; sem merge/deploy/migration/segredos/dados reais.

## Workflow follow-up

Revisão humana e autorização operacional própria antes de merge, migration ou publicação. Não sincronizar/arquivar specs antes da revisão.
