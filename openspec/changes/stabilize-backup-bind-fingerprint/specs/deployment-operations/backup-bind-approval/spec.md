## ADDED Requirements

### Requirement: Aprovação estável para vínculo e ensaio

O workflow e o wrapper SHALL comparar a fingerprint v2 no modo bind-and-rehearse. O wrapper SHALL revalidar as precondições de capacidade e inércia no inventário sob lock antes de escrever. A seleção recente, a aprovação protegida e a verificação do runtime instalado SHALL permanecer obrigatórias. Reconcile SHALL conservar a fingerprint integral.

#### Scenario: Oscilação de disco durante a aprovação

- **WHEN** somente os contadores voláteis de disco oscilam e as precondições atuais passam
- **THEN** o vínculo e o ensaio sintético SHALL permanecer elegíveis com a fingerprint v2 aprovada

#### Scenario: Capacidade ou identidade diverge

- **WHEN** a fingerprint v2 diverge ou a capacidade atual deixa de atender às precondições
- **THEN** o wrapper MUST abortar antes de gravar o vínculo ou acessar o destino para o ensaio

#### Scenario: Atestação da instalação antes de confirmar o recibo

- **WHEN** o runtime acaba de ser instalado em modo inerte
- **THEN** o instalador SHALL gravar o manifesto root-only em modo 0400 e a conclusão SHALL depender da mesma atestação de manifesto, link ativo e recibos usada antes do vínculo
