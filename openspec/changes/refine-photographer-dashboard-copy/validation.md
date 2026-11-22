# Validação

## Evidências — 05/11/2026

- Na Visão Geral e na tela Créditos, o alerta agora mostra “Saldo insuficiente para novos uploads” seguido do link “Adquira um pacote →”. O link foi clicado em UI local e chegou a `/admin/credits#credit-packages`, com o título “Pacotes disponíveis” como destino. Não houve compra nem mutação financeira.
- O cabeçalho da área existente agora diz “Prática de publicação”; as três etapas e ações permaneceram inalteradas.
- A cópia e a navegação foram verificadas em Chrome local (`127.0.0.1:3040`) com a conta de teste já existente. Configurações foram conferidas em desktop e viewport 390×844; a Visão Geral foi conferida no DOM em ambas as larguras disponíveis. Sem consulta ou escrita em produção.
- `npm test -- app/admin/page.test.tsx app/admin/credits/page.test.tsx app/admin/settings/tenant-address-panel.test.tsx`: **26 testes passaram**. ESLint direcionado e `npx tsc --noEmit` passaram. `openspec validate refine-photographer-dashboard-copy --strict --no-interactive` passou.
- `npm run build` completo com Turbopack passou após a extração do componente compartilhado, em cópia local isolada sem `.env`, com raiz de resolução temporária restrita a `C:/codex-data`; 26 rotas geradas. A cópia permanece em `C:/codex-data/temp/pyp-saas-ux-build-20261105` porque a revisão automática bloqueou a remoção recursiva solicitada; o junction de `node_modules` aponta para o frontend original.
- Revisão proporcional: alteradas somente as duas superfícies da carteira, o heading da seção, a âncora e os testes correspondentes. A cópia/CTA foram extraídos para `CreditShortfallNotice`, evitando duplicação entre Visão Geral e Créditos. Nenhuma regra de saldo/upload/publicação mudou; não houve limpeza geral elegível.
