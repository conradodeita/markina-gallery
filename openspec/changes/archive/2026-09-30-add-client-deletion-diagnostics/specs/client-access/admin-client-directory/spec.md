## ADDED Requirements

### Requirement: Auditoria de exclusão permanece limitada e completa

O evento de auditoria de exclusão SHALL manter uma referência curta ao recibo durável e SHALL respeitar o limite de tamanho da coluna persistida. O recibo SHALL permanecer como fonte autoritativa para UUID da cliente, ator administrativo, resultado, fingerprint do inventário e contagens completas; a exclusão SHALL NOT truncar nem descartar esses dados para caber no evento.

#### Scenario: Exclusão com grafo operacional extenso

- **WHEN** uma exclusão elegível remove várias categorias operacionais na mesma transação
- **THEN** o evento de auditoria referencia o recibo sem exceder o limite de 320 caracteres, o recibo conserva os dados completos e a transação conclui também em PostgreSQL
