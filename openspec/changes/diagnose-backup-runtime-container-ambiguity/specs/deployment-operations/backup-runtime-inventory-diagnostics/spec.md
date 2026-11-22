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

#### Scenario: Workflow confirma recusa do inventário normal
- **WHEN** o job read-only termina a consulta agregada para o mesmo SHA da operação
- **THEN** ele invoca o inventário normal, captura a resposta sem publicá-la e exige o código estático `api_container_record_ambiguous`
- **AND** publica somente esse código, sem fingerprint, precondições ou saída bruta
- **AND** se a identidade normal passar ou outra falha ocorrer, encerra com uma mensagem estática sanitizada

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

### Requirement: Instalação protegida verificável durante ambiguidade

O instalador do forced command protegido SHALL validar o contrato agregado read-only depois da troca atômica, usando código fixado à mesma revisão e o lock já adquirido, sem exigir fingerprint do inventário normal do runtime de backup.

#### Scenario: Instalação do canal de diagnóstico com inventário ambíguo
- **WHEN** o preflight protegido da aplicação é consistente, a referência exata da `main` é instalada e o módulo do diagnóstico retorna o schema agregado fixo sob o lock comum já adquirido
- **THEN** a verificação da instalação pode concluir sem usar contagens como fingerprint ou precondição do runtime
- **AND** falha de comando, formato ou preservação dos containers restaura o forced command anterior
- **AND** o inventário normal continua recusando a identidade ambígua

### Requirement: Destino da instalação vinculado ao preflight atual

O job de escrita SHALL comparar o binding de sua conexão SSH de produção com o `connection_binding` emitido pelo job protegido de preflight da mesma execução, sem depender de variáveis escopadas a outro ambiente.

#### Scenario: Destino de escrita corresponde ao preflight
- **WHEN** a fingerprint solicitada corresponde à fingerprint recém-coletada e o binding da conexão de produção corresponde ao binding do preflight
- **THEN** o job pode continuar para os gates de instalação protegida
- **AND** a igualdade da conexão continua obrigatória antes de qualquer comando SSH de escrita

#### Scenario: Destino de escrita diverge do preflight
- **WHEN** o binding da conexão de produção não corresponde ao `connection_binding` do preflight
- **THEN** o job falha antes de abrir a conexão SSH de escrita
- **AND** nenhuma alteração no host é realizada
