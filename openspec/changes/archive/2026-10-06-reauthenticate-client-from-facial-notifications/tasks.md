# Tasks

## 1. Reautenticação contextual segura

- [x] 1.1 Aceitar contexto de galeria no desafio, reenvio e validação OTP sem capability somente após confirmar cliente, registro e estado ativos; cobrir cliente autorizado, telefone sem vínculo e revogação durante o desafio com regressões direcionadas.
- [x] 1.2 Garantir resposta externa neutra e nenhuma entrega OTP para telefone sem vínculo ativo; verificar os testes de isolamento e não enumeração.

## 2. Link e retorno da notificação

- [x] 2.1 Gerar URL de login contextual sem token ou resultado, preservar retorno seguro para galeria e navegar ao destino após OTP; cobrir construção de mensagem, entrada autenticada/desautenticada e retorno do resultado.
- [x] 2.2 Validar OpenSpec estrito, testes focalizados backend/frontend e `git diff --check`; registrar evidência e limites em `validation.md`.
