# Spec Delta

## ADDED Requirements

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

### Requirement: Recuperação do worker preserva dados
O procedimento SHALL registrar journal antes de mutação, preservar imagem anterior, testar candidato e restaurar apenas esse serviço em falha. Banco, dados e outros serviços SHALL NOT sofrer rollback.

#### Scenario: Saúde do candidato falha
- **WHEN** o container substituto não passa os gates
- **THEN** o procedimento restaura a imagem anterior, comprova saúde, retoma produtores e libera entrada somente depois da recuperação

#### Scenario: Recuperação falha
- **WHEN** não é possível provar o runtime recuperado
- **THEN** o journal e a manutenção permanecem ativos, e o resultado é recuperação pendente
