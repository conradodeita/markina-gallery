# Proposal

## Why

Uma falha transitória em qualquer chamada da API deixa um aviso global de conexão preso em telas autenticadas de fotógrafos e clientes. A recuperação depende de um clique manual, embora a sessão possa voltar a funcionar sem intervenção, tornando a experiência repetitiva e alarmante.

## What Changes

- Iniciar automaticamente a reconexão/revalidação da sessão após falhas transitórias, sem exigir que fotógrafo ou cliente clique em “Reconectar” ou “Verificar conexão novamente”; limitar tentativas e impedir verificações concorrentes.
- Mostrar o aviso de indisponibilidade de conexão somente enquanto a própria verificação da sessão falhar; falhas isoladas permanecem no fluxo da operação.
- Retirar automaticamente o aviso de conexão quando a sessão for confirmada, sem botão manual. Se o resultado de uma operação com efeitos continuar incerto, manter um aviso próprio desse resultado, distinto da indisponibilidade de sessão.
- Manter a distinção entre indisponibilidade temporária, sessão expirada e acesso negado.
- Nunca repetir automaticamente a requisição comercial ou de comunicação que falhou; operações com resultado ambíguo continuam protegidas contra duplicação e seguem sua reconciliação própria.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `auth`: recuperação automática do estado transitório de conectividade em áreas autenticadas de fotógrafo e cliente.

## Impact

- Frontend: `frontend/app/session-boundary.tsx` e testes de sessão.
- Sem mudança de API, backend, autenticação, envio de OTP, compras ou implantação.
- A confirmação automática consulta somente o destino/sessão autenticados; não reenvia a operação que sofreu falha.
