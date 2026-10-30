# Spec Delta

## ADDED Requirements

### Requirement: Carregamento inequívoco do candidato de manutenção
O processo de manutenção SHALL importar o pacote Python do candidato revisado, sem precedência do pacote antigo existente no diretório de trabalho da imagem. O executor MUST preservar esse diretório e a resolução dos caminhos relativos de mídia; a seleção do candidato não autoriza trocar a imagem de aplicação ou ignorar a verificação de blobs.

#### Scenario: Imagem preservada contém pacote anterior
- **WHEN** a imagem contém `app` antigo no diretório de trabalho e o candidato está em `PYTHONPATH`
- **THEN** o processo usa o pacote do candidato sem mudar o diretório de trabalho nem os caminhos relativos de mídia

### Requirement: Inventário independente da ordem de mounts
O inventário SHALL comparar mounts pela identidade de destino, preservando todos os campos retornados pelo Docker. A ordem da lista MUST NOT provocar drift; destinos ausentes ou duplicados e qualquer alteração de valor MUST permanecer bloqueantes.

#### Scenario: Docker reordena a lista sem alterar a configuração
- **WHEN** duas consultas retornam os mesmos mounts em ordens diferentes
- **THEN** o fingerprint e a verificação de preservação permanecem iguais

#### Scenario: Mount sofre alteração efetiva
- **WHEN** fonte, destino, permissões ou outro campo de um mount muda
- **THEN** a comparação continua detectando drift e impede a publicação

### Requirement: Corte coordenado de contexto ambiental
O executor SHALL tratar a migração biométrica aprovada, envelopes de integração e bindings do canal como um conjunto recuperável. A operação MUST exigir SHA atual de main com CI push verde, inventário e fingerprint estáveis, execução exclusiva, backup cifrado reaberto e pausa graciosa dos consumidores próprios. O relatório não pode expor credenciais, payloads, IDs ou hashes de conteúdo biométrico.

#### Scenario: Origem com índice legado e referência vazia
- **WHEN** o inventário confirma índices de fotos operacionais, ausência de referências/notificações com conteúdo e zero jobs ativos
- **THEN** o executor prepara o caminho SQL, preservando versões, identidades e vínculos
- **AND** divergência de modelo histórico não provoca reindexação nem descarte

#### Scenario: Etapa financeira falha depois da biométrica
- **WHEN** a atualização financeira falha dentro do lote
- **THEN** a transação externa reverte índices, cofre e bindings sem liberar estado parcial

### Requirement: Prova autenticada substitui inferência por contagem total
O corte SHALL verificar o snapshot de destino contra um pacote autenticado vinculado ao plano/inventário; contagem positiva de registros preservados não equivale à existência de ciphertexts de origem após essa prova. O fluxo anterior de inventário continua bloqueado sem prova; não aceitar um booleano ou contagem de caller para zerar o bloqueio.

#### Scenario: Snapshot diverge do pacote
- **WHEN** qualquer registro, envelope, vínculo ou metadado atual diverge do conjunto autenticado
- **THEN** a verificação de destino falha e o corte ou recuperação não sobrescreve o estado desconhecido

### Requirement: Recuperação de configuração e canais
O executor SHALL preservar em pacote separado a configuração efetiva anterior, imagens, comandos, montagens e bindings e SHALL validar continuidade SMTP/WhatsApp sem mensagens. O corte MUST manter as imagens publicadas e atuar somente no projeto inventariado.

#### Scenario: Falha ao iniciar API ou worker no destino
- **WHEN** ambiente, cofre, canal ou saúde falha após a transição SQL
- **THEN** a barreira de manutenção permanece ativa enquanto o executor restaura dados/configuração do conjunto conhecido
- **AND** estado não reconhecido mantém a barreira e exige intervenção

### Requirement: Busca facial suspensa e liberação live separada
Durante o corte autorizado, o executor SHALL deixar a busca facial indisponível, conservar os três containers especializados parados e preservar fotos, índices, imagens e volumes. O gate Mercado Pago SHALL permanecer fechado até a transição ter recibo de sucesso e elegibilidade por tenant comprovada. A fase live MUST preservar PIX e o par sandbox e não emitir cobranças reais de teste.

#### Scenario: Transição concluída e gate aberto
- **WHEN** o destino production, o cofre, os canais e a saúde são verificados
- **THEN** a fase autorizada de liberação abre somente novas emissões de contas reais opt-in por fotógrafo
- **AND** contas de teste continuam limitadas ao par autorizado e tenants não configurados permanecem sem Mercado Pago
