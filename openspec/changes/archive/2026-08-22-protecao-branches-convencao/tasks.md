## 1. Ajustar documentação e convenção

- [x] 1.1 Atualizar a seção de convenções do `README.md` (main protegida por convenção; sem enforcement técnico no plano gratuito) — verificar lendo a seção após a edição
- [x] 1.2 Atualizar a linha de convenções do `openspec/config.yaml` — verificar com `openspec instructions proposal --change "protecao-branches-convencao" --json` exibindo o contexto atualizado
- [x] 1.3 Registrar a decisão do plano gratuito em `docs/DECISOES-TECNICAS.md` — verificar lendo o novo item do documento

## 2. Validação e fechamento

- [x] 2.1 Validar a mudança — verificar com `openspec validate protecao-branches-convencao --strict`
- [x] 2.2 Após aceite do proprietário, sincronizar a spec `deployment-operations` em `openspec/specs/` e arquivar a mudança — verificar com `openspec list` e `openspec list --specs`
