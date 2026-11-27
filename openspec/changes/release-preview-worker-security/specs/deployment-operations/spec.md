# Spec Delta

## ADDED Requirements

### Requirement: Inventário de runtime e proveniência do worker de prévias
O inventário SHALL ser somente leitura, limitado aos containers e manifestos Compose do projeto `markina-gallery`. Ele SHALL registrar imagens por digest, arquitetura, saúde, política de reinício, proveniência/hash Compose, revisão única do schema e contagens agregadas da fila.

#### Scenario: Inventário válido do candidato isolado
- **WHEN** checkout, Compose, serviços, imagem anterior e candidato ARM64 são identificados sem divergências
- **THEN** o relatório contém somente metadados operacionais permitidos, proveniência e contagens agregadas

### Requirement: Inventário fail-closed e minimizado
O inventário MUST NOT expor ambiente de containers, configuração de conexão, fotografias ou dados de clientes. Ele SHALL recusar serviço desconhecido, duplicidade ativa, manifesto fora das raízes aprovadas, checkout sujo, arquitetura incompatível ou resposta incompleta.

#### Scenario: Proveniência ou runtime ambíguo
- **WHEN** aparece um serviço desconhecido, manifesto inseguro ou duas instâncias ativas do mesmo serviço
- **THEN** o inventário falha fechado e não produz aprovação operacional

### Requirement: Identidades de containers históricos parados
O inventário SHALL preservar metadados de identidade dos containers parados, sem depender de manifestos históricos já retirados e sem permitir recriação desses containers. Todo serviço ativo SHALL continuar sujeito à proveniência Compose integral; serviços desconhecidos e duplicidade ativa SHALL continuar bloqueados.

#### Scenario: Histórico parado e runtime ativo
- **WHEN** um container histórico parado aponta para manifesto retirado
- **THEN** sua identidade e seus labels são preservados no snapshot sem permitir sua recriação; um manifesto ausente de serviço ativo continua bloqueando

### Requirement: Operação privilegiada com lock existente
Um operador root SHALL poder adquirir o lock existente do proprietário do diretório de estado privado, sem modificar permissões e mantendo exclusividade e rejeição de symlinks ou escrita por terceiros.

#### Scenario: Operador privilegiado e lock privado
- **WHEN** root usa um lock existente de outro proprietário
- **THEN** o diretório de estado deve ser privado e pertencer ao mesmo proprietário do lock; qualquer divergência bloqueia

### Requirement: Seleção explícita de Compose homologado
A CLI SHALL selecionar somente versões Compose homologadas, atualmente 2.35.1 e 5.6.1. Consultas por serviço SHALL selecionar explicitamente os profiles, sem iniciar serviços; a seleção de profiles não dispensa a verificação dos hashes.

#### Scenario: Worker definido em profile
- **WHEN** o inventário consulta o hash do worker de prévias definido em profile
- **THEN** o serviço é incluído na consulta sem iniciar containers, e divergência de hash continua bloqueando

### Requirement: Manutenção de segurança exclusiva do worker de prévias
O procedimento SHALL permitir preparar a substituição apenas do preview-adjustment-worker por imagem ARM64 com os quatro pins aprovados, preservando Python, RawTherapee, código e demais distribuições. SHALL exigir inventário atual, autorização da janela, tratamento aprovado dos callbacks e lock comum antes de mutação.

#### Scenario: Consumidor já corrigido
- **WHEN** API e worker geral já contêm os pins corrigidos
- **THEN** suas imagens não são substituídas; eventual pausa utiliza e retoma os mesmos containers

#### Scenario: Opcional produtor ativo
- **WHEN** existe produtor fora da allowlist da manutenção
- **THEN** o procedimento recusa antes de qualquer parada

### Requirement: Transição segura do processo legado
O procedimento SHALL bloquear novos produtores, parar graciosamente API/worker, aguardar fila queued/processing vazia e confirmar a identidade antes de SIGINT no legado, aceitando somente saída 130. Timeout ou falha SHALL recuperar sem SIGKILL.

#### Scenario: Novo trabalho durante drenagem
- **WHEN** a fila permanece ocupada ou um produtor não encerra
- **THEN** nenhuma troca é executada e os containers anteriores são retomados

### Requirement: Confirmação limitada da barreira de entrada
Após recarregar o Nginx, o procedimento SHALL confirmar HTTP 503 em uma rota pública antes de continuar. Respostas anteriores à efetivação do reload ou falhas transitórias de conexão SHALL ser consultadas novamente por até 15 segundos; nenhuma resposta diferente de 503 SHALL liberar a próxima etapa.

#### Scenario: Reload ainda propagando
- **WHEN** a primeira consulta retorna 200 e uma consulta posterior retorna 503 dentro do limite
- **THEN** a barreira somente é considerada ativa após observar 503

#### Scenario: Barreira não confirmada
- **WHEN** o limite termina sem HTTP 503
- **THEN** o procedimento falha fechado e mantém o journal para recuperação

### Requirement: Recuperação do worker preserva dados
O procedimento SHALL registrar journal antes de mutação, preservar imagem anterior, testar candidato e restaurar apenas esse serviço em falha. Banco, dados e outros serviços SHALL NOT sofrer rollback.

#### Scenario: Saúde do candidato falha
- **WHEN** o container substituto não passa os gates
- **THEN** o procedimento restaura a imagem anterior, comprova saúde, retoma produtores e libera entrada somente depois da recuperação

#### Scenario: Recuperação falha
- **WHEN** não é possível provar o runtime recuperado
- **THEN** o journal e a manutenção permanecem ativos, e o resultado é recuperação pendente

#### Scenario: Recuperação antes da recriação do worker
- **WHEN** a falha ocorre antes de substituir o container original do worker
- **THEN** o procedimento reconhece a identidade e o hash Compose originais sem exigir o hash de um overlay ainda não aplicado
