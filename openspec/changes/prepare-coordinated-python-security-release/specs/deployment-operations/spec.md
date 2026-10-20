# Spec Delta

## ADDED Requirements

### Requirement: Preparação Python independente preserva runtime existente
O planejamento SHALL identificar somente consumidores ativos, cruzar IDs/ARM64/versões reais e excluir opcionais inativos. Candidatos SHALL preservar base, código, modelos e todas as distribuições fora das quatro correções aprovadas. IDs locais SHALL ser distinguidos de registry e Oracle.

#### Scenario: Reinstalação altera pacote não relacionado
- **WHEN** o inventário de distribuições do candidato difere fora de aiohttp, multidict, urllib3 e yarl
- **THEN** o candidato é recusado mesmo se pip check passa

#### Scenario: Opcional ausente
- **WHEN** um worker opcional não está running no inventário
- **THEN** ele não é ativado nem incluído automaticamente no rollout

### Requirement: Escopo Python não pode cair no release API web
O executor oficial app SHALL distinguir explicitamente python-security e SHALL recusar release/rollback/recover reais enquanto a cobertura de drenagem/execução não estiver implementada e validada. Planejamento e simulação SHALL declarar que não concedem autorização operacional.

#### Scenario: Drenagem indisponível
- **WHEN** um processo antigo não oferece confirmação cooperativa de encerramento após finalizar seus efeitos
- **THEN** nenhuma troca real é executada, mesmo com fila momentaneamente vazia e autorização humana

### Requirement: Contrato simulado coordenado é sequencial e reversível
A simulação SHALL validar SHA/fingerprint/imagens, tarefa ativa e capacidade de drenagem antes de mutação simulada; SHALL salvar recibo por serviço antes da troca, verificar saúde e reverter em ordem inversa se houver falha, preservando dados e serviços fora do escopo.

#### Scenario: Falha intermediária
- **WHEN** o segundo consumidor simulado falha na saúde
- **THEN** ele e o consumidor anterior são restaurados por identidade e os demais não são substituídos

#### Scenario: Frontend protegido
- **WHEN** um plano inclui web, banco, Redis, Nginx ou serviço desconhecido
- **THEN** ele é recusado antes de qualquer troca
