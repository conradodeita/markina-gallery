## 1. Planejamento e contrato

- [x] 1.1 Revisar e aprovar esta mudança e o fluxo de uma tela com dois contextos.
- [x] 1.2 Alinhar contratos de API para desafio OTP, validação OTP, login de senha, validação TOTP, sessão e destino inicial.
- [x] 1.3 Definir expiração, tentativas máximas, reenvio e rate limit dos desafios.

## 2. Backend e persistência

- [x] 2.1 Criar modelos/migrations para desafios OTP, sessões, papéis e auditoria.
- [x] 2.2 Implementar normalização E.164 e adaptador de envio WhatsApp.
- [x] 2.3 Implementar autenticação do administrador com Argon2id, e-mail verificado e TOTP.
- [x] 2.4 Implementar sessão segura, rotação, revogação e middleware de autorização por papel.
- [x] 2.5 Implementar resolução de destino: `/admin`, galeria única ou biblioteca.

## 3. Frontend

- [x] 3.1 Criar tela única de entrada com escolha `Cliente`/`Fotógrafo`.
- [x] 3.2 Implementar etapas de nome/telefone/OTP do cliente.
- [x] 3.3 Implementar etapas de e-mail/senha/TOTP do administrador.
- [x] 3.4 Implementar redirecionamento e estados de carregamento, erro, expiração e reenvio.
- [x] 3.5 Garantir que o frontend não trate o botão, a URL ou o estado local como autorização.

## 4. Testes e segurança

- [x] 4.1 Testar sucesso e falha de OTP, senha e TOTP.
- [x] 4.2 Testar OTP usado/expirado, reenvio e rate limit.
- [x] 4.3 Testar isolamento de sessão cliente/admin e acesso negado a `/admin`.
- [x] 4.4 Testar galeria única versus biblioteca com múltiplas galerias.
- [x] 4.5 Validar auditoria, cookies seguros e ausência de enumeração de contas.
- [x] 4.6 Executar testes, validação OpenSpec e revisão humana antes de sincronizar a spec.
- [x] 4.7 Registrar no change qualquer desvio, limitação, bloqueio ou decisão tomada durante a implementação, garantindo continuidade para outro executor.

## Registro de continuidade — 2026-08-25

- Implementado: modelo SQLAlchemy inicial, desafio OTP de uso único, senha Argon2id + TOTP, cookie de sessão opaco, auditoria, autorização de papel/galeria, destino decidido no servidor e tela única responsiva.
- Evidência: `python -m pytest -q` no diretório `backend` (8 aprovados), `python -m ruff check app tests migrations`, `python -m alembic upgrade head --sql`, `npm test`, `npm run lint`, `npm run build` no diretório `frontend` e `npx --yes @fission-ai/openspec validate unified-authentication-routing --strict` (válido).
- Concluído nesta retomada: migration Alembic revisável, adaptador WhatsApp sandbox que não expõe códigos, limite por identidade/IP, reenvio limitado, rotação/revogação de sessões, UI de reenvio/expiração e testes de segurança.
- Revisão funcional concluída: em navegador local, foram conferidos os contextos Cliente e Fotógrafo, a etapa OTP com reenvio e a disponibilidade dos dois contextos em viewport de 390 px. A revisão revelou que o modo de desenvolvimento não encaminhava `/api/*` à API; foi corrigido com rewrite local configurável por `API_ORIGIN`, sem alterar o encaminhamento do Nginx em produção.
- O binário global `openspec` segue ausente do `PATH`, mas a validação foi executada com o CLI temporário `npx --yes @fission-ai/openspec`.
