# Design: Remediação de dependências do frontend

## Decisão

Usar releases corrigidas dentro da linha Next.js 16. A versão 16.3.8 é a primeira versão fora do intervalo vulnerável informado pelo audit; as versões 16.3.8 de `next` e `eslint-config-next` existem no registry. O resolvedor compatível pode selecionar release 16.x posterior e corrigida no lockfile.

Executar a resolução sem scripts de instalação e sem `--force`. Não introduzir overrides especulativos nem trocar o conjunto de regras ESLint para ocultar um achado transitivo.

## Evidência e limites

Uma simulação isolada de `npm audit fix --package-lock-only --ignore-scripts` elevou Next.js e `eslint-config-next` para 16.4.0 e atualizou dependências runtime como `sharp` (0.35.3 → 0.35.5) e `source-map-js` (1.2.1 → 1.2.2). A auditoria somente de produção ficou sem achados.

A simulação deixou cinco itens altos no audit completo, todos pela cadeia de ferramentas `eslint-config-next` → `@next/eslint-plugin-next` → `fast-glob` → `micromatch` → `braces@3.0.3`. O registry não publica versão `braces` 3.x posterior a 3.0.3 no momento desta mudança; a alternativa indicada pelo `npm audit fix --force` rebaixa `eslint-config-next` para 14.2.35 e quebra o alinhamento com Next.js 16. Esse downgrade foi rejeitado. O achado de desenvolvimento deve permanecer explicitamente documentado até uma correção upstream compatível.

## Segurança operacional

O Dockerfile instala dependências por `npm ci` e produz uma imagem standalone. Esta mudança só altera manifests/lockfile frontend e documentação OpenSpec. Não autoriza build/deploy em produção nem acessa configurações, banco ou dados do servidor.
