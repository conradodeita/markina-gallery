# Tasks

Aceite humano para prosseguir recebido em 11/10/2026. Revisão pré-publicação identificou que a checagem periódica de segurança da spec vigente deve ser preservada e que falhas de outras operações devem respeitar o backoff.

## 1. Cobrir a recuperação automática

- [x] 1.1 Adicionar testes de regressão ao SessionBoundary para falha temporária, revalidação em segundo plano sem clique, recuperação/remoção do aviso, tentativas limitadas e single-flight; verificar que os casos falham no comportamento atual e correspondem aos cenários da delta spec. Evidência: os testes novos falharam antes da implementação; depois da correção, `npm test -- --run app/session-boundary.test.tsx` passou com 24 testes.
- [x] 1.2 Adicionar testes para pausa enquanto a página está oculta, revalidação ao voltar à página, falha isolada de operação com sessão válida, sessão expirada e ausência de replay da operação original; verificar os resultados e ausência de chamadas duplicadas. Evidência: os mesmos 24 testes dirigidos passaram; uploads e pedidos sintéticos foram chamados uma única vez.

## 2. Implementar reconexão automática

- [x] 2.1 Alterar `frontend/app/session-boundary.tsx` para iniciar revalidação automática da sessão em segundo plano após indisponibilidade transitória, com backoff limitado, uma verificação por vez, pausa quando oculto e retomada imediata quando visível; verificar os testes de regressão da task 1. Evidência: 24 testes dirigidos aprovados; intervalo progressivo limitado a 30 s com revalidação periódica de segurança preservada (revisão pré-publicação abaixo).
- [x] 2.2 Remover a dependência de controles manuais “Reconectar”/“Verificar conexão novamente” e manter o aviso global somente até a verificação segura confirmar a sessão ou o fluxo existente tratar expiração/acesso negado; verificar os testes de interface e que nenhuma requisição de negócio, OTP, compra ou upload seja repetida. Evidência: o controle manual foi removido; erro isolado com sessão válida não deixa aviso global e operações de teste não foram repetidas.
- [x] 2.3 Registrar no OpenSpec qualquer ajuste necessário à delta spec e documentar a semântica da recuperação — reconecta a sessão sem ação manual e não confirma nem repete operações ambíguas; verificar consistência entre proposal, design, spec delta e comportamento implementado. Evidência: proposal, design e delta spec descrevem reconexão automática, confirmação apenas da sessão e ausência de replay; tasks refletem o backoff implementado.

## 3. Validar integração

- [x] 3.1 Executar testes frontend dirigidos, lint e typecheck/build aplicáveis, validar a change com OpenSpec em modo estrito e revisar `git diff --check`; registrar os comandos e resultados em `validation.md`, corrigindo falhas atribuídas à alteração antes de concluir. Evidência: `validation.md` registra 24 testes dirigidos e 474 testes da suíte completa aprovados, lint sem erros, typecheck/build/OpenSpec estrito/diff check aprovados.

## 4. Revisão e publicação

- [x] 4.1 Preservar revalidação periódica de segurança e impedir que erros de operações antecipem retries; verificar regressões de revogação sem interação, falha inicial e backoff sob falhas simultâneas, repetindo as verificações afetadas. Evidência: 26 testes dirigidos/476 frontend aprovados; lint sem erros, typecheck/build e OpenSpec 91/91 aprovados.
- [ ] 4.2 Publicar somente os arquivos desta correção em PR para develop e conferir os checks do head; registrar PR e evidência em validation.md.
- [ ] 4.3 Apresentar inventário atual, portas/subdomínio e impacto; concluir homologação pelo fluxo aprovado e registrar saúde/SHA publicados, mantendo aprovação de environment quando exigida.
