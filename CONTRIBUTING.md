# Como contribuir para a Markina Gallery

Obrigado por querer melhorar a Markina Gallery. Contribuições de código, documentação, testes, acessibilidade e relatos de problemas são bem-vindas quando preservam a privacidade de famílias, a segurança operacional e o escopo do produto.

## Antes de começar

- Não envie dados reais de crianças, clientes, fotos privadas, bancos locais, `.env`, tokens, chaves ou capturas com informações sensíveis.
- Leia `AGENTS.md`, `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md`, `ROADMAP_ARQUITETURA.md` e as specs/changes relevantes em `openspec/` antes de alterar comportamento.
- Não implemente propostas OpenSpec supersedidas nem amplie requisitos além do roadmap e da change aprovada.
- A licença do projeto ainda não foi definida. Não presuma autorização jurídica para reutilizar, redistribuir ou relicenciar o código.

## Fluxo de contribuição

1. Abra uma issue para relatar um problema ou discutir uma ideia. Para vulnerabilidades ou dados expostos, não use issue pública.
2. Faça um fork do repositório e crie uma branch curta e descritiva no seu fork.
3. Para qualquer mudança de comportamento, crie ou atualize uma change OpenSpec com proposta, tasks verificáveis e specs quando aplicável. Mantenha os artefatos em português.
4. Faça alterações pequenas, focadas e compatíveis com as diretrizes do repositório. Preserve o trabalho preexistente e não inclua arquivos locais, caches, bancos, journals ou referências privadas.
5. Execute os testes, lint, typecheck, build e `openspec validate --strict --all --no-interactive` aplicáveis. Explique qualquer limitação de validação no pull request.
6. Use commits convencionais e abra um pull request para `develop`. Não faça push direto em branches de integração, deploy, migration destrutiva ou mudança de secrets.

## Revisão

Mantenedores podem pedir redução de escopo, uma change OpenSpec separada, testes adicionais ou ajustes de privacidade e segurança. Um pull request só é integrado após revisão humana e CI verde; uma contribuição nunca recebe automaticamente acesso a homologação, produção, banco ou credenciais.

## Segurança e conduta

Não publique vulnerabilidades, credenciais ou informações pessoais. Use o [reporte privado de vulnerabilidades do GitHub](https://github.com/conradodeita/markina-gallery/security/advisories/new) para problemas de segurança. O canal privado de incidentes de conduta está sendo configurado; até ele estar disponível, peça orientação ao mantenedor pelo perfil do repositório sem incluir detalhes sensíveis em uma issue.
