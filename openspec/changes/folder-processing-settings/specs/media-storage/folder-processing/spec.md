## Purpose

Controlar processamento facial e ajuste de prévias por pasta comum ou restrita, preservando a herança da galeria, a proteção das imagens e a operação administrativa simples.

## ADDED Requirements

### Requirement: Herança compatível e substituição completa

Pastas de conteúdo SHALL iniciar herdando a configuração da galeria. O ajuste SHALL permitir herdar, personalizar ou desligar; a configuração própria SHALL substituir integralmente exposição e intensidade, nunca acumular com os valores gerais. Configurações próprias SHALL ser preservadas quando o padrão da galeria mudar. Os limites atuais de exposição e intensidade SHALL ser aplicados pelo backend.

#### Scenario: Exposição própria
- **WHEN** a galeria tem exposição +0,3 e a pasta recebe configuração própria +0,5
- **THEN** o processamento aplica somente +0,5 naquela pasta e mantém +0,3 nas pastas herdadas

#### Scenario: Padrão alterado
- **WHEN** o fotógrafo muda a exposição geral de +0,3 para +0,7
- **THEN** somente pastas herdadas recebem o novo valor efetivo, enquanto a pasta personalizada +0,5 permanece com +0,5

#### Scenario: Personalização com padrão desligado
- **WHEN** o padrão está desligado e uma pasta recebe ajuste personalizado ativo
- **THEN** somente a pasta personalizada pode agendar e apresentar resultados ajustados

#### Scenario: Desligamento e retorno à herança
- **WHEN** uma pasta é desligada e posteriormente volta a herdar
- **THEN** enquanto desligada usa a prévia convencional e ao herdar usa os valores atuais da galeria sem somar o último ajuste próprio

### Requirement: Ajuste sem acumulação e publicação consistente

Cada processamento SHALL partir da prévia convencional limpa preservada e aplicar proteção depois do tratamento. O resultado SHALL conter uma assinatura da configuração efetiva e somente ser publicado/entregue se fonte, proteção e configuração ainda forem vigentes. Alterações SHALL invalidar resultados afetados e impedir publicação obsoleta, sem modificar originais, histórico comercial ou índice facial. Novas fotos SHALL usar o modo efetivo; fotos existentes SHALL exigir ação explícita de processamento.

#### Scenario: Reprocessamento repetido
- **WHEN** o fotógrafo processa três vezes a mesma pasta com exposição +0,5
- **THEN** cada execução parte da prévia convencional e o resultado mantém +0,5 sem intensificar o efeito

#### Scenario: Troca durante render
- **WHEN** a configuração muda ou é desligada enquanto o worker renderiza
- **THEN** o resultado da configuração anterior não se torna elegível e a cliente recebe fallback convencional autorizado

#### Scenario: Revisões numéricas coincidentes
- **WHEN** uma pasta passa de herança geração 2 para configuração própria revisão 2
- **THEN** o sistema distingue as origens e não reutiliza resultado apenas por coincidência numérica

### Requirement: Controle facial local subordinado aos gates

O processamento facial da pasta SHALL permitir herdar, permitir novos trabalhos ou pausar novos trabalhos. Nenhuma escolha SHALL contornar gates de ambiente, rollout, política ou consentimento existentes. Pausar SHALL impedir novas admissões, agendamentos e retentativas daquela pasta, sem apagar índices nem alterar busca autorizada sobre resultados existentes. Trabalhos já admitidos SHALL poder concluir sob o lifecycle e a retenção existentes. A autorização facial da cliente SHALL continuar limitada às pastas comuns e atribuídas.

#### Scenario: Pasta pausada
- **WHEN** o fotógrafo pausa uma pasta e envia novas fotos
- **THEN** as prévias convencionais continuam disponíveis pelo fluxo normal, mas não surgem novos trabalhos faciais da pasta

#### Scenario: Índice anterior preservado
- **WHEN** a pasta pausada já possui índice e trabalho admitido
- **THEN** o índice não é apagado, a busca mantém os controles de audiência e o trabalho admitido pode terminar sem iniciar retentativa nova pelo painel

#### Scenario: Gate global indisponível
- **WHEN** a pasta permite processamento, mas o ambiente ou rollout está indisponível
- **THEN** a interface informa indisponibilidade e o backend recusa processamento facial

### Requirement: Operação delimitada e auditada

O administrador SHALL consultar configuração efetiva e progresso separado por pasta, agendar ajuste paginado e solicitar retentativa facial local. Cada ação SHALL identificar e afetar somente a pasta solicitada. As operações SHALL exigir autenticação administrativa e pasta de conteúdo ativa válida, com auditoria e sem alterar público, vínculos, seleção, compra ou entrega. Ações gerais SHALL respeitar configurações locais desligadas ou personalizadas.

A configuração por pasta SHALL ser classificada como dado operacional da pasta na política de limpeza explícita de homologação. O inventário SHALL contá-la sem revelar seus valores; a política SHALL continuar preservando configurações globais e recusando tabelas não classificadas. A simples classificação SHALL NOT iniciar limpeza ou reprocessamento.

#### Scenario: Processar uma entre duas pastas
- **WHEN** o administrador solicita processamento da pasta A
- **THEN** somente fotos de A entram na fila e os trabalhos/configurações da pasta B permanecem inalterados

#### Scenario: API solicitada por cliente
- **WHEN** uma cliente conhece o UUID e solicita configuração ou processamento administrativo de uma pasta
- **THEN** o backend nega a ação sem alterar registros nem revelar prévias não autorizadas

#### Scenario: Inventário de homologação com configuração local
- **WHEN** uma pasta sintética possui configuração própria e o inventário restrito de homologação é consultado
- **THEN** a configuração aparece somente como contagem operacional e as configurações globais continuam na categoria preservada

### Requirement: Painel de pasta acessível e consistente

A etapa Imagens e o Acervo SHALL usar o mesmo painel recolhível por pasta, com identificação de herança/personalização/desligamento, valores efetivos, progresso real e ações locais. A UI SHALL oferecer sucesso/erro explícitos, labels/foco/teclado acessíveis e layout móvel sem overflow. Consultas SHALL iniciar somente na abertura e polling SHALL parar ao fechar/desmontar ou quando não houver trabalhos pendentes. Pasta compartilhada SHALL informar que configurações se aplicam a todas as clientes atribuídas. O padrão/resumo geral SHALL permanecer identificado como da galeria.

#### Scenario: Abrir pasta restrita compartilhada
- **WHEN** o fotógrafo abre o processamento de uma pasta no Acervo
- **THEN** vê seu escopo e aviso de compartilhamento, sem iniciar processamento ou alterar configuração apenas ao abrir

#### Scenario: Uso móvel com teclado
- **WHEN** o painel é usado em viewport estreita ou navegando por teclado
- **THEN** controles permanecem legíveis, identificados e alcançáveis sem crescimento horizontal por nome longo
