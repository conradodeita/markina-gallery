# Change: Remediar dependências vulneráveis do frontend

## Contexto

Em 14/10/2026, `npm audit` no lockfile do frontend reproduziu 11 vulnerabilidades (10 altas e 1 crítica). O lockfile mantinha Next.js e `eslint-config-next` em 16.3.2, junto a dependências transitivas com correções disponíveis. O Dockerfile usa `npm ci`, portanto instala as versões fixadas no lockfile.

## Objetivo

Atualizar o Next.js e as dependências transitivas corrigíveis dentro da linha compatível 16.x, removendo os achados críticos e altos do conjunto de dependências de produção do frontend.

## Escopo

- Elevar o mínimo declarado de Next.js e `eslint-config-next` para a primeira versão 16.x fora do intervalo vulnerável identificado.
- Atualizar o lockfile de forma reproduzível para incluir correções compatíveis de dependências transitivas.
- Verificar a auditoria de produção e registrar separadamente qualquer vulnerabilidade restante apenas em ferramentas de desenvolvimento sem correção compatível publicada.

## Fora de escopo

- Alterações de funcionalidades ou de interface.
- Mudanças no backend, no servidor, em segredos ou no ambiente de produção.
- Downgrade de versão principal, `npm audit fix --force`, deploy ou alteração de dados reais.

## Critérios de aceite

- `npm ci` pode instalar o lockfile atualizado sem divergência.
- Next.js e `eslint-config-next` permanecem na linha principal 16 e em versões compatíveis entre si.
- `npm audit --omit=dev` não reporta vulnerabilidades altas ou críticas.
- Achados restantes no audit completo ficam registrados com pacote, dependência de origem, escopo de execução e condição de correção upstream.
