## Purpose

Permitir que o fotógrafo acompanhe na Visão geral o volume físico ocupado pelas fotos da Markina Gallery e a quantidade total de fotos registradas, sem expor caminhos ou dados pessoais.

## ADDED Requirements

### Requirement: Medição agregada do armazenamento fotográfico

O sistema SHALL calcular para o administrador a soma dos bytes fisicamente presentes nas raízes autorizadas de fotos recebidas, derivados e histórico de mídia, e SHALL informar separadamente a quantidade total de registros de foto existentes no banco.

#### Scenario: Visão geral com fotos armazenadas

- **WHEN** o administrador autenticado abre a Visão geral e existem fotos e derivados no servidor
- **THEN** o painel apresenta o espaço total ocupado em MB ou GB e a quantidade total de fotos
- **AND** a soma inclui uma única vez cada arquivo regular das raízes fotográficas autorizadas

#### Scenario: Acervo vazio

- **WHEN** não existem registros de foto nem arquivos nas raízes fotográficas autorizadas
- **THEN** o painel apresenta zero fotos e zero MB ocupados

### Requirement: Métrica administrativa segura e isolada

O sistema SHALL disponibilizar a métrica somente para sessão administrativa válida e SHALL retornar apenas valores agregados, sem nomes de arquivos, caminhos, identificadores de clientes ou conteúdo de mídia.

#### Scenario: Cliente solicita a métrica

- **WHEN** uma sessão de cliente ou uma requisição sem autenticação consulta o resumo administrativo
- **THEN** o sistema nega o acesso sem revelar contagem, bytes ou estrutura de armazenamento

#### Scenario: Uma raiz não pode ser medida

- **WHEN** a medição física não pode ser concluída com segurança
- **THEN** o indicador informa indisponibilidade sem inventar valor
- **AND** as demais métricas e ações da Visão geral continuam disponíveis

### Requirement: Apresentação legível sem perder precisão contratual

O sistema SHALL manter a quantidade de bytes como valor inteiro autoritativo na resposta e SHALL formatá-la na interface em MB enquanto menor que 1 GB e em GB a partir desse limite.

#### Scenario: Mudança de unidade

- **WHEN** o volume medido ultrapassa o limite de apresentação entre MB e GB
- **THEN** a interface escolhe a unidade correspondente e preserva precisão suficiente para acompanhamento operacional
