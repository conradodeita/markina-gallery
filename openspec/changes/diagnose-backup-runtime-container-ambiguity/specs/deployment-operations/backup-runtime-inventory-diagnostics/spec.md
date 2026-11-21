# Spec Delta

## Purpose

Explicar ambiguidades no inventário de containers do runtime de backup por meio de dados agregados e restritos, mantendo intactas as guardas de identidade e operação.

## ADDED Requirements

### Requirement: Contagens agregadas por papel fixo

O diagnóstico SHALL consultar somente os papéis fixos `api`, `web` e `db` do projeto Compose autorizado e informar, por papel, a quantidade de registros e as contagens de estado `running`, `stopped` e `unknown`.

#### Scenario: Registros ambíguos
- **WHEN** houver zero, um ou múltiplos registros para um papel fixo
- **THEN** o operador recebe somente uma linha agregada desse papel com as contagens correspondentes, sem registros individuais
- **AND** nenhum papel ou serviço fora da lista fixa é consultado

#### Scenario: Estado ausente ou não reconhecido
- **WHEN** um registro válido não tiver estado reconhecido
- **THEN** ele é contado somente na categoria `unknown`, sem expor o valor original

### Requirement: Diagnóstico não aprova inventário

O diagnóstico SHALL permanecer separado da aprovação operacional, e o inventário normal MUST continuar exigindo exatamente um ID completo por papel e revalidando os labels Compose após a inspeção.

#### Scenario: Diagnóstico encontra duplicidade
- **WHEN** o diagnóstico relata múltiplos registros para qualquer papel
- **THEN** o inventário normal permanece recusado com seu código de ambiguidade
- **AND** nenhuma fingerprint, precondição aprovada, seleção de container ou operação `operate` é produzida

#### Scenario: Contagens não substituem nova validação
- **WHEN** as contagens agregadas forem consultadas
- **THEN** elas não podem ser reutilizadas como prova de identidade para instalação, vínculo, ensaio ou backup
- **AND** qualquer operação posterior exige executar novamente o inventário normal protegido e passar por seus gates próprios

### Requirement: Canal restrito e resultado sanitizado

A consulta SHALL ser somente de leitura e acessível apenas pelo canal protegido allowlisted; respostas MUST omitir identificadores, nomes, valores de labels, saídas brutas, caminhos, exceções, configuração e segredos.

#### Scenario: Consulta protegida permitida
- **WHEN** o operador autenticado invoca a operação fixa de diagnóstico pelo canal autorizado
- **THEN** somente os dados agregados especificados são retornados e nenhum serviço, arquivo, configuração ou dado do Drive é alterado

#### Scenario: Limite seguro de registros excedido
- **WHEN** um papel fixo retorna mais de 512 registros correspondentes
- **THEN** o diagnóstico retorna somente um código estático allowlisted, sem contagens parciais nem identificadores

#### Scenario: Falha de consulta ou registro inválido
- **WHEN** a listagem, inspeção ou validação de um registro falha
- **THEN** o sistema retorna somente um código estático allowlisted, sem contagens parciais nem detalhes do comando ou do registro
- **AND** nenhuma fingerprint ou precondição aprovada é emitida
