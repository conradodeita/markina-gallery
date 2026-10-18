# Spec Delta

## ADDED Requirements

### Requirement: Exclusão mútua dos releases de produção

Releases e rollbacks mutáveis de API+web e web-only SHALL adquirir o mesmo lock exclusivo no host antes de qualquer mutação. A operação SHALL falhar fechada se o lock estiver ocupado ou indisponível, se o diretório de estado não existir, ou se houver marcador de tentativa pendente do outro fluxo.

#### Scenario: Release API+web adquire lock livre
- **WHEN** um release ou rollback API+web aprovado começa e o lock está livre, sem tentativa web-only pendente
- **THEN** o script mantém o lock durante toda a operação e só então executa seus gates e mutações existentes

#### Scenario: Operação API+web encontra lock ou estado web-only pendente
- **WHEN** o lock está ocupado, `flock` não está disponível, o diretório de estado está ausente ou existe `web-in-flight.sha`
- **THEN** a operação API+web termina sem alterar imagens, containers, checkout ou estado de release

#### Scenario: Operação web-only encontra release API+web ativo ou pendente
- **WHEN** o lock está ocupado ou existe `app-in-flight.sha`
- **THEN** o fluxo web-only termina antes de alterar imagens, containers, checkout ou estado de release

#### Scenario: Inventário somente-leitura
- **WHEN** o operador executa inventário ou preflight sem mutação
- **THEN** os gates e informações de inventário existentes são preservados, sem iniciar uma publicação
