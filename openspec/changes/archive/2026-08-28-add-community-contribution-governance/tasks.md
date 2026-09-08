## 1. Orientação para contribuições

- [x] 1.1 Criar `CONTRIBUTING.md` com fluxo de fork, branch, OpenSpec, testes, commits e pull request para `develop`; verificar que o GitHub o reconhece e que ele referencia as fontes de verdade sem duplicar secrets ou decisões sensíveis. (arquivo padrão criado e verificado por Prettier e inspeção de segredos em 2026-08-28)
- [x] 1.2 Criar `CODE_OF_CONDUCT.md` com padrões de convivência, aplicação e canal privado para incidentes de segurança/comportamento; verificar clareza, tom inclusivo e ausência de dados pessoais de contato. (canal de conduta autorizado pela proprietária; reporte privado de vulnerabilidades do GitHub ativado e confirmado em 2026-08-28)

## 2. Triagem e revisão

- [x] 2.1 Adicionar templates de issue para bug e proposta, solicitando impacto, reprodução, privacidade e escopo OpenSpec; verificar que não pedem credenciais, dados pessoais ou dados de homologação. (forms YAML verificados por Prettier e inspeção de conteúdo em 2026-08-28)
- [x] 2.2 Adicionar template de pull request com checklist de OpenSpec, testes, segurança, migrations e documentação; verificar que contribuições externas não recebem permissão implícita de deploy ou escrita direta. (template Markdown verificado por Prettier e inspeção de conteúdo em 2026-08-28)
- [x] 2.3 Documentar no guia a pendência de licença e a regra de que nenhuma licença é presumida; verificar que não há arquivo ou afirmação jurídica conflitante no repositório. (nenhum arquivo `LICENSE*`, `COPYING*` ou `NOTICE*` encontrado em 2026-08-28)

## 3. Validação documental

- [x] 3.1 Revisar os novos arquivos contra `AGENTS.md`, CI e OpenSpec; verificar links locais, consistência de linguagem e `openspec validate add-community-contribution-governance --type change --strict --no-interactive`. (Prettier, `git diff --check` e validação estrita aprovados em 2026-08-28)
