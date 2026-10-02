# Spec Delta

## Purpose

Definir a validação futura de jornadas e isolamento com um grupo pequeno de fotógrafos e clientes, usando o diagnóstico de capacidade somente quando o sistema estiver tecnicamente pronto para o ensaio.

## ADDED Requirements

### Requirement: Validação futura condicionada à prontidão

O ensaio com fotógrafos e clientes SHALL ocorrer somente após completar o isolamento dos caminhos inventariados, preservar o legado e aprovar os testes de engenharia aplicáveis, com evidências de prontidão registradas. A intenção do proprietário de validar assim que possível SHALL ser tratada como objetivo futuro condicionado a esses pré-requisitos e às autorizações operacionais do ambiente. Ela MUST NOT ser tratada, por si só, como ordem de execução imediata, criação de uma segunda conta operacional ou dispensa de isolamento para antecipar a validação. O monitor SHALL ser testado durante as jornadas quando essa etapa futura puder ser executada.

#### Scenario: Preparação ainda incompleta
- **WHEN** restam caminhos sem isolamento, testes de engenharia pendentes ou dependências que invalidam as jornadas
- **THEN** o ensaio permanece planejado e o trabalho avança na preparação e nas verificações independentes, sem ativar outra conta operacional

#### Scenario: Prontidão demonstrada
- **WHEN** os pré-requisitos técnicos estão comprovados e as autorizações operacionais necessárias foram concedidas
- **THEN** o ensaio pode ser realizado na primeira oportunidade viável, usando o monitor antes, durante e depois das jornadas

### Requirement: Provisionamento e piloto pequenos e autorizados

O piloto SHALL usar duas contas de fotógrafo com três clientes próprias de cada conta, uma galeria por conta e no máximo seis JPEGs sintéticos por galeria. Um telefone SHALL se repetir entre contas para testar identidades independentes. Não haverá cadastro público de fotógrafo. Provisionamento remoto SHALL exigir inventário de contas/configurações preservadas e autorização específica. Dados e segredos reais MUST NOT ser incluídos no repositório; mensagens reais e biometria real SHALL exigir autorização própria.

#### Scenario: Piloto local
- **WHEN** o executor prepara o ensaio antes da autorização remota
- **THEN** usa banco, mídia e adaptadores descartáveis exclusivos, com OTP e pagamentos sintéticos sem envio ou movimentação financeira real

#### Scenario: Piloto em homologação
- **WHEN** o proprietário aprova o inventário, destino, versão, canais e plano de impacto zero
- **THEN** somente os recursos e dados identificados do Pick-your-Pic são criados ou alterados, preservando o fotógrafo atual e recursos vizinhos

### Requirement: Entrega persistente de configuração de canais

O Compose SHALL disponibilizar bindings de canais por arquivo opcional não versionado somente aos serviços `api`, `worker` e `face-search-worker`. Conteúdo SHALL preservar valores literalmente sem interpolação. A ausência do arquivo SHALL conservar o funcionamento legado de conta única; o suporte MUST NOT criar conta, canal ou segredo automaticamente. Criação/alteração do arquivo real SHALL exigir autorização operacional, permissão restrita e preservação do canal atual antes da ativação de B.

#### Scenario: Bindings ainda não configurados
- **WHEN** o arquivo opcional não existe
- **THEN** Compose resolve normalmente e conserva as variáveis legadas existentes

#### Scenario: Bindings explicitamente configurados
- **WHEN** o arquivo autorizado contém a associação e credenciais próprias por alias
- **THEN** somente os três consumidores recebem os valores literais e deploys posteriores conservam o arquivo não versionado

### Requirement: Jornadas positivas e tentativas de acesso cruzado

O ensaio SHALL exercitar login de ambos os fotógrafos, OTP contextual, pasta comum e restrita, seleção, checkout com PIX de teste ou finalização sem cobrança, confirmação sintética e entrega. SHALL comprovar que o mesmo telefone em duas contas recebe sessões, seleção e histórico separados. Requisições diretas a galerias, arquivos, clientes, carrinhos, pedidos e configurações de outra conta SHALL ser negadas. Concorrência SHALL ser limitada a seis jornadas cliente, uma por cadastro, sem aumentar infraestrutura.

#### Scenario: Cliente comum aos dois fotógrafos
- **WHEN** a pessoa acessa os links dos dois fotógrafos e autentica separadamente
- **THEN** seus estados permanecem separados e uma compra ou edição em A não aparece nem altera B

#### Scenario: Isolamento falha
- **WHEN** qualquer tentativa revela dados ou produz efeito em outra conta
- **THEN** o ensaio é interrompido e a liberação é reprovada, com evidência sem dados pessoais e tarefa de correção pendente

### Requirement: Leituras reais de capacidade com limites explícitos

O operador autorizado SHALL coletar e copiar diagnósticos antes, durante e depois das jornadas, registrando janela UTC, cache, evidência, ocupação do pool, conexões PostgreSQL e estados das cinco filas. Intervalos SHALL respeitar o cache vigente; uma coleta reutilizada MUST NOT ser apresentada como nova. Os relatórios SHALL ser associados às etapas em evidência manual sanitizada, sem adicionar histórico automático ao produto. Filas sem trabalho SHALL permanecer descritas como vazias, sem conclusão sobre saúde do worker; o resultado MUST NOT declarar capacidade máxima, fairness, p95, SLO ou orçamento global completo.

#### Scenario: Job transitório não capturado
- **WHEN** o job conclui entre duas amostras e o snapshot não observa fila pendente
- **THEN** o relatório registra a limitação e usa evidência separada da conclusão, sem inventar pico de fila ou tempo de espera

#### Scenario: Comparação antes durante e depois
- **WHEN** as jornadas terminam e os diagnósticos são comparados
- **THEN** o executor registra os valores observados e as lacunas, além dos resultados de isolamento e das verificações de conclusão dos jobs
