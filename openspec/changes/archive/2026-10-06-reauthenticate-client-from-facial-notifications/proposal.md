# Proposal

## Why

As notificações de conclusão da busca facial apontam diretamente para uma galeria protegida, mas o cliente pode abrir a mensagem em outro dispositivo ou depois de a sessão expirar. A entrada atual não preserva a galeria nem permite iniciar OTP sem o convite original, impedindo o acesso ao resultado recém-concluído.

## What Changes

- Fazer o link da notificação abrir a entrada de cliente com retorno à galeria correspondente quando não houver sessão válida.
- Permitir reautenticação contextual por nome, telefone e OTP somente para cliente com vínculo ativo já existente à galeria indicada.
- Manter resposta neutra, limites e auditoria existentes; não enviar OTP a números sem vínculo ativo para essa galeria.
- Após OTP válido, restaurar a sessão e retornar à galeria, que carrega a busca facial mais recente autorizada.
- Não incluir token de convite nem resultado facial na URL/mensagem; o ID da galeria serve apenas para localizar o contexto, nunca para conceder acesso.

## Capabilities

### New Capabilities

- `privacy-biometric/facial-search-notifications`: links de conclusão e retomada autenticada dos resultados faciais.

### Modified Capabilities

- `auth`: reautenticação OTP contextual a uma galeria por cliente com vínculo já ativo.

## Impact

- `backend/app/facial/notifications.py`: destino seguro da mensagem transacional.
- `backend/app/auth.py` e `backend/app/main.py`: contexto opcional de galeria no desafio OTP e revalidação do vínculo antes de enviar, reenviar ou validar o código.
- `frontend/app/session-recovery.ts`, `frontend/app/auth-entry.tsx` e entrada da busca facial: preservar retorno seguro e enviar o contexto da galeria.
- Testes de contrato de autenticação, recuperação de sessão e mensagem facial; sem alteração de banco, capabilities, convites existentes, segredos ou configuração de homologação.
