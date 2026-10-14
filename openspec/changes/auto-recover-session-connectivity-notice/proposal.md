# Proposal

## Why

Uma falha transitória em qualquer chamada da API deixa um aviso global de conexão preso em telas autenticadas de fotógrafos e clientes. A recuperação depende de um clique manual, embora a sessão possa voltar a funcionar sem intervenção, tornando a experiência repetitiva e alarmante.

## What Changes

- Iniciar automaticamente a reconexão/revalidação da sessão após falhas transitórias, sem exigir que fotógrafo ou cliente clique em “Reconectar” ou “Verificar conexão novamente”; limitar tentativas e impedir verificações concorrentes.
- Mostrar o aviso global somente enquanto a própria sessão/conectividade não puder ser confirmada; falhas isoladas de uma operação permanecem no respectivo fluxo.
- Retirar automaticamente o aviso de indisponibilidade quando a sessão for confirmada; a recuperação acontece em segundo plano, sem botão manual de reconexão.
- Manter a distinção entre indisponibilidade temporária, sessão expirada e acesso negado.
- Nunca repetir automaticamente a requisição comercial ou de comunicação que falhou; operações com resultado ambíguo continuam protegidas contra duplicação.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `auth`: recuperação automática do estado transitório de conectividade em áreas autenticadas de fotógrafo e cliente.

## Impact

- Frontend: `frontend/app/session-boundary.tsx` e testes de sessão.
- Sem mudança de API, backend, autenticação, envio de OTP, compras ou implantação.
- A confirmação automática consulta somente o destino/sessão autenticados; não reenvia a operação que sofreu falha.
