## ADDED Requirements

### Requirement: Reutilização de CI para operação protegida autorizada

Uma operação manual adaptada SHALL poder reutilizar o CI de push à main para seu SHA exato quando o run e todos os jobs necessários tiverem concluído com sucesso. Seleção desconhecida, SHA diferente, tentativa mais recente pendente ou falha, job necessário ausente ou API indisponível MUST bloquear a operação.

#### Scenario: CI exato já passou
- **WHEN** uma operação protegida autorizada usa o mesmo SHA da main e há CI push completo e verde com todos os jobs requeridos
- **THEN** a operação reutiliza essa evidência sem repetir a suíte e registra SHA e run usados

#### Scenario: Evidência de CI inválida
- **WHEN** o SHA difere ou o run mais recente está pendente, falha, incompleto ou sem job exigido
- **THEN** a operação falha fechada sem acesso mutável ao ambiente

### Requirement: Continuidade automática dentro da autorização vigente

O executor SHALL poder prosseguir sem pedir autorizações repetidas quando o proprietário já autorizou a operação, seu ambiente e impacto. SHALL apresentar inventário, escopo e fingerprint antes da mutação e revalidar fingerprint e SHA sob lock; autorização vigente SHALL NOT dispensar proteções do GitHub, backup, isolamento ou recusa de divergências.

#### Scenario: Estado estável e autorização abrangente
- **WHEN** a operação está autorizada, inventário é apresentado e o fingerprint permanece igual sob lock
- **THEN** o executor pode aprovar o ambiente protegido e continuar sem nova solicitação de autorização para a mesma operação

#### Scenario: Escopo ou estado mudou
- **WHEN** inventário, SHA, escopo ou autorização diverge
- **THEN** a operação não inicia a mutação e registra a divergência para decisão apropriada

### Requirement: Despacho da ponte reutiliza checks completos do SHA exato

A instalação da ponte e do wrapper de API/web SHALL usar um workflow manual em `main`, consultar os checks do push exato antes de acessar `production` e exigir o ambiente protegido. A permissão de reutilizar evidência com preflight recusado SHALL se limitar a esse instalador. O release SHALL continuar exigindo preflight próprio aprovado e fingerprint válido.

#### Scenario: CI de código aprovado e preflight recusado

- **WHEN** a tentativa mais recente do push para o SHA atual de `main` terminou, todos os jobs obrigatórios e o escopo estão verdes, o único job falho é `production-app-preflight` e o release API/web foi pulado
- **THEN** somente o job de instalação poderá aguardar a revisão de `production`, sem repetir a suíte e com os blobs revisados vinculados ao SHA

#### Scenario: Outra falha ou evidência incompleta

- **WHEN** o SHA não corresponde à main atual, a tentativa mais recente está pendente, faltam jobs obrigatórios ou outro job da tentativa falhou
- **THEN** o instalador SHALL recusar antes de acessar o ambiente protegido
