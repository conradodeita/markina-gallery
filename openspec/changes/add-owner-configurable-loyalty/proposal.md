# Proposal: Programa de fidelidade configurável

## Contexto

O documento de execução prevê pontos, regras, conversão e recompensas administrados pelo proprietário global. A investigação delimitada de backend, migrations, frontend e specs principais não localizou um modelo, fluxo ou tela de fidelidade. Também não encontrou critérios comerciais já aprovados para gerar pontos ou conceder recompensas.

## Goals

- Permitir configurar quais eventos geram pontos, quantidades, conversões/recompensas e estado ativo/inativo, com autorização global explícita.
- Manter ledger, saldo e histórico de pontos próprios, idempotentes e auditáveis.
- Ligar cada recompensa ao evento de origem e, quando emitir créditos, registrar um movimento distinto no ledger de créditos.
- Preservar movimentos anteriores quando uma regra for suspensa e evitar duplicidade por replay.
- Iniciar sem regras/recompensas comerciais padrão.

## Non-goals

- Definir eventos, quantidades, conversões, benefícios, validade dos pontos ou qualquer valor comercial sem decisão do proprietário.
- Misturar pontos e créditos em uma tabela ou permitir que pontos virem saldo monetário automaticamente.
- Ativar regras de pontuação em produção, conceder recompensa real, alterar pagamentos ou publicar migrations.

## Dependências e decisões

- Depende de identidade e permissões comerciais globais especificadas na trilha F5; `PlatformOwner` e `MonitorGrant` atuais autorizam somente o monitor.
- Depende dos contratos da carteira `add-photographer-credit-wallet` para emitir créditos como recompensa, mantendo ledger separado e referência ao evento de fidelidade.
- O proprietário deve decidir eventos elegíveis, pesos, conversão, benefícios, validade de pontos e resposta a estorno/chargeback antes de ativar regras.

## Evidência e refatoração

O checkout de fotos cria pedidos comerciais por cliente. Nenhum comportamento de fidelidade foi identificado nesse caminho. A implementação futura deve integrar-se aos eventos comerciais existentes sem acoplar o ledger de pontos ao de créditos ou alterar compras históricas. Revisar somente os produtores de eventos usados pelas regras; não iniciar refatoração geral.

## Decisão do proprietário — 07/11/2026

O programa de fidelidade fica fora do primeiro release. Nenhuma regra será criada/ativada e nenhum ponto ou recompensa será concedido até uma decisão comercial posterior. Esta decisão adia a implementação; não define eventos, conversão, benefícios ou validade.
