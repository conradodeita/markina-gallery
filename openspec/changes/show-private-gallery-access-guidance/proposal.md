# Proposal

## Why

Em galerias configuradas como `invite_only`, uma pessoa sem autorização pode ver o campo de código mesmo quando o servidor não entregou OTP. Isso cria expectativa de acesso e deixa pouco claro que a galeria é privada.

## What Changes

- Em desafios de autenticação contextual a uma galeria `invite_only`, mostrar primeiro um aviso de privacidade e ocultar o campo de OTP.
- Oferecer a clientes que já possuem convite uma ação explícita para abrir a etapa do código; quem não foi convidado é orientado a falar com o fotógrafo.
- Calcular a orientação somente pelo contexto/modo da galeria, sem consultar o vínculo do telefone para decidir o que a interface mostra.
- Preservar a resposta e a mensagem neutras, as regras existentes de entrega/reenvio de OTP e o fluxo atual das galerias `standard`.

## Capabilities

### New Capabilities

### Modified Capabilities

- `auth`: orientar o acesso a galerias `invite_only` antes de apresentar a validação OTP, sem revelar vínculo ou elegibilidade do telefone.

## Impact

- FastAPI: resposta de `/auth/client/challenge` incluirá um marcador de orientação derivado apenas do contexto autorizado.
- Next.js: entrada de autenticação de cliente exibirá aviso de galeria privada e uma ação explícita para quem possui convite.
- Testes de autenticação e interface; sem migration, alteração dos limites de OTP, provedor externo ou operação de produção.
