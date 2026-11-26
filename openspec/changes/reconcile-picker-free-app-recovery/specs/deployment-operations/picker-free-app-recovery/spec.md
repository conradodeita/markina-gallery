# Spec Delta

## Purpose

Esta capability permite recuperar API/web pelo handoff protegido sem montar a configuração aposentada do Google Picker, preservando OAuth, banco, mídias e serviços fora da transição.

## ADDED Requirements

### Requirement: Receita de recuperação sem o mount do Picker
O handoff SHALL registrar receita root-only e fingerprintada para recuperar API/web com imagens e modelos Compose comprovados, removendo somente o bind exato do Picker.

#### Scenario: Bind exato do Picker
- **WHEN** o modelo anterior contém somente o bind exato de `picker-config.json`
- **THEN** a receita exclui esse bind e preserva imagem, ambiente, redes, volumes, OAuth e demais mounts, com hashes vinculados ao registro

#### Scenario: Bind ancestral ou configuração ambígua
- **WHEN** um bind ancestral cobre Picker e OAuth ou sua origem/destino não pode ser separado sem alterar outro recurso
- **THEN** o handoff bloqueia a receita antes de qualquer mutação e mantém a referência existente

### Requirement: Recuperação protegida usa a receita sem iniciar testemunhas
A recuperação SHALL exigir inventário somente-leitura e aprovação próprios, recriar somente API/web pela receita aprovada e validar saúde antes de publicar o novo estado.

#### Scenario: Recuperação aprovada
- **WHEN** fingerprint, imagens, receita e aprovação coincidem com o estado observado
- **THEN** API/web são recriados sem o bind do Picker, nenhum container histórico testemunha é iniciado e `/`, `/healthz` e `/api/health` são verificados

#### Scenario: Receita ou runtime divergente
- **WHEN** imagem, modelo, metadados, schema ou fingerprint difere do registro aprovado
- **THEN** a recuperação aborta antes de parar ou criar containers e preserva o diagnóstico sanitizado

### Requirement: Testemunhas históricas ficam intactas e fora da recuperação
Uma testemunha com Picker SHALL ser reconhecida como não ativa somente quando sua identidade e configuração correspondem ao registro aprovado, seu estado é parado e a receita vigente não a seleciona para recovery.

#### Scenario: Testemunha parada aprovada
- **WHEN** o container parado corresponde integralmente à testemunha registrada e a receita vigente não depende dele
- **THEN** o inventário preserva seus metadados na fingerprint, não o seleciona como candidato e não conta seu bind como mount ativo do Picker

#### Scenario: Testemunha mudou ou está ativa
- **WHEN** a identidade/configuração diverge, o container está em execução ou o registro está ausente
- **THEN** o inventário mantém `picker_mount=present` e bloqueia o cleanup sem iniciar, parar, renomear ou remover o container

#### Scenario: Inventário ancora testemunha na ponte aprovada
- **WHEN** o inventário de aposentadoria examina testemunhas históricas
- **THEN** ele valida o blob exato da ponte root-only na revisão aprovada, revalida ID, imagem, nome, serviço, configuração, mounts e lifecycle localmente, e inclui todos os mounts no digest agregado mesmo quando não apresenta o mount de uma testemunha exata como ativo
- **AND** falha sem fingerprint quando a saída da ponte é inválida, incompleta ou diverge da inspeção local

### Requirement: Recuperação preserva OAuth e dados da plataforma
A recuperação SHALL preservar o OAuth compartilhado, schema, dados de clientes, mídias, volumes, banco, workers, Nginx e recursos de outros projetos.

#### Scenario: Recuperação de API/web
- **WHEN** a receita é aplicada
- **THEN** somente API/web podem ser recriados, OAuth permanece montado e MUST NOT ocorrer SQL, migration, alteração de volume, remoção de container testemunha ou ação em Drive

### Requirement: Retirada do Picker exige recibo atual de runtime sem Picker
A retirada protegida do arquivo exato do Picker SHALL exigir recibo root-only válido ligado à receita picker-free e ao runtime API/web atual e saudável. A operação SHALL revalidar fingerprint e recibo sob lock antes de remover qualquer alvo e SHALL preservar OAuth, banco, dados de clientes, witnesses e caminhos compartilhados.

#### Scenario: Recuperação sem recibo válido
- **WHEN** o journal não é da recuperação picker-free, uma fase/API/web não está saudável, o schema não está verificado, o recibo não corresponde à receita/base ativa, ou a inspeção atual encontra o mount do Picker
- **THEN** o inventário falha sem fingerprint utilizável e a retirada não remove arquivos, unidades ou diretórios

#### Scenario: Recibo vigente ligado ao runtime observado
- **WHEN** a ponte root-only valida journal e fases saudáveis, receita/modelos e imagem pinados, schema, manifesto/base ativa, IDs atuais de API/web e ausência do Picker em `Mounts`, `HostConfig.Binds` e `HostConfig.Mounts`
- **THEN** o inventário inclui hashes do recibo, receita, manifesto e ponteiro, IDs/imagens/saúde dos dois serviços e os vincula à fingerprint de aposentadoria
- **AND** a operação reobtém o mesmo estado sob lock/fingerprint antes da remoção e confirma no pós-check que recibo e digest agregado de containers continuam iguais

#### Scenario: Estado muda após aprovação do inventário
- **WHEN** qualquer parte do runtime, receita, recibo, ponteiro ativo, mounts ou fingerprint muda entre inventário e retirada
- **THEN** a operação aborta antes da primeira remoção e preserva OAuth, banco, dados de clientes e os containers existentes
