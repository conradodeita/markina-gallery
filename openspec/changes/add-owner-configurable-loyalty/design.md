# Design: Programa de fidelidade configurável

## Estado

Adiada do primeiro release por decisão do proprietário em 07/11/2026. Não há código, migration ou regra de pontuação implementada. Esta change permanece como registro para retomada futura; sua aprovação não concede valores padrão nem autorização para ativar o programa.

## Direção técnica candidata

1. Guardar configuração versionada de regras globais com eventos, pontos/recompensas e estado ativo. Nenhuma regra vem ativa ou com quantidade presumida.
2. Registrar pontos em ledger append-only e saldo derivado/reconstruível. Uma chave única por regra/evento de origem impede dupla pontuação.
3. Representar concessão de recompensa como evento separado, com referência à regra e ao evento que a originou. Se conceder créditos, chamar o serviço de carteira e referenciar a recompensa sem unificar os ledgers.
4. Suspender regra impede novas pontuações, mas conserva histórico e recompensas já emitidas.
5. Proteger administração por capability global comercial específica; monitor técnico, identidade do fotógrafo e e-mail isolado não autorizam alterar regras.

## Decisões ainda abertas

- Eventos que pontuam, quantidades, critérios, conversão e catálogo de benefícios.
- Se e quando pontos expiram; o requisito atual só declara que créditos concedidos como recompensa não expiram.
- Resposta a reembolso/chargeback depois de pontos ou créditos de recompensa já terem sido usados.
- Papel, concessão auditada e superfície de UI para administração global.
- Evento de origem e atomicidade entre uma compra confirmada, ledger de pontos e geração idempotente de recompensa.

## Validação esperada

Cobrir regras desligadas, ausência de defaults, autorização, tenant scope, replay do evento, suspensão preservando histórico, concorrência, reconciliação de saldo, relação auditável ponto→recompensa→crédito e correções financeiras.

## Decisão do proprietário

Fidelidade não integra o primeiro release. Eventos, regras, ledger e telas ficam adiados até decisão comercial própria. Manter qualquer implementação futura sem defaults ativos e sem concessão de pontos/recompensas por esta change.
