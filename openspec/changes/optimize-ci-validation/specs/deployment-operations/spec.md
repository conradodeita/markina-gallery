## ADDED Requirements

### Requirement: Validação backend completa sem repetição equivalente

O CI SHALL executar cada teste coletado da suíte geral do backend uma única vez por configuração, podendo distribuir módulos em runners isolados. Testes com configuração de banco diferente SHALL preservar cada variante necessária. Pushes protegidos e execuções manuais SHALL manter cobertura completa; nenhuma redução de tempo SHALL depender da omissão de testes existentes.

#### Scenario: Regressão focada já coberta
- **WHEN** uma regressão focada pertence à suíte completa e usa a mesma configuração
- **THEN** o workflow executa essa regressão pela suíte sem repetir um passo equivalente

#### Scenario: Variante PostgreSQL de exclusão
- **WHEN** a suíte geral usa SQLite e uma regressão exige DATABASE_URL PostgreSQL
- **THEN** ambas as configurações continuam executando e qualquer falha bloqueia a validação

### Requirement: Agregação de partes com cobertura integral

O check `backend` SHALL permanecer estável e exigir sucesso da qualidade e de todas as partes necessárias, coleções idênticas e partição completa sem sobreposição. Ausência, falha, cancelamento, coleção divergente ou artefato incompleto MUST impedir resultado verde. Relatórios SHALL permitir medir duração por teste sem usar dados de produção.

#### Scenario: Todas as partes completas
- **WHEN** cada parte passa e suas seleções formam exatamente a coleção completa
- **THEN** backend passa e disponibiliza os relatórios de duração

#### Scenario: Parte falha ou cobertura diverge
- **WHEN** uma parte falha, é cancelada, não executa, omite testes ou repete testes de outra parte
- **THEN** backend falha e os gates dependentes não autorizam release
