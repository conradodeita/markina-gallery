# Tasks

## 1. Resposta neutra do desafio

- [x] 1.1 Incluir marcador de orientação derivado somente de `access_mode=invite_only`, inclusive nos caminhos de desafio sem entrega; testar mesma resposta de orientação para identidades vinculadas e não vinculadas, preservando rate limit, suppressão, OTP, tenant e sessão. Evidência: `test_invite_only_otp.py`: **18 passaram**; testes direcionados após reforço da asserção (**2 passaram**) confirmam o mesmo marcador para telefone vinculado e não vinculado no mesmo contexto de galeria, além de retorno sem challenge/outbox/sessão quando o telefone não tem vínculo. Ruff passou.

## 2. Experiência de autenticação

- [x] 2.1 Exibir aviso de galeria privada sem campo OTP no estado inicial e permitir abrir explicitamente o campo a quem tem convite; cobrir contexto `invite_only`, continuação/OTP e fluxo `standard` em testes do componente. Evidência: testes AuthEntry direcionados: **64 passaram** em 2 arquivos; o teste contextual confirma aviso, ausência do campo e continuação explícita com OTP.

## 3. Integração local

- [x] 3.1 Executar regressões direcionadas de auth/backend e AuthEntry, lint, TypeScript, build aplicável e OpenSpec strict; revisar refatoração focal e registrar confirmação de ausência de migration, envio real, escrita de dados ou operação remota. Evidência: `test_invite_only_otp.py` **18 passaram** (mais 2 regressões focadas após reforço das asserções); AuthEntry **64 passaram/2 arquivos**; Ruff passou; ESLint nos arquivos tocados passou sem avisos; `tsc --noEmit` passou; `npm run build` concluiu; OpenSpec strict passou para esta change e para `clarify-client-otp-access-guidance`; `git diff --check` passou. Nenhuma migration, envio de OTP real, gravação de dados operacionais ou chamada remota foi executada.

## Workflow follow-up

- Sincronizar a spec principal e arquivar somente após revisão humana.
- O teste local não autoriza publicar ou ativar cadastro público nem alterar produção.
