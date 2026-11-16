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

Cada processamento SHALL partir da prévia convencional limpa e aplicar proteção após o tratamento. Resultado SHALL registrar assinatura da configuração e só ser publicado se fonte/proteção/configuração vigem. Alterações invalidam resultados obsoletos sem mudar originais, histórico comercial ou índice facial; fotos novas usam modo efetivo e existentes exigem ação explícita.

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

O controle facial da pasta SHALL oferecer herança, admissão de novos trabalhos ou pausa, sempre subordinado aos gates de ambiente, rollout, política e consentimento. Pausar bloqueia novas admissões, agendamentos e retentativas, sem apagar índice nem invalidar busca autorizada; trabalhos admitidos podem concluir sob lifecycle e retenção vigentes. A consulta da cliente continua limitada às pastas comuns e atribuídas.

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

Consulta de configuração/progresso, ajuste paginado e retentativa facial SHALL exigir autenticação e pasta ativa, ser auditados e afetar só a pasta pedida, sem alterar público, vínculos, seleção, compra ou entrega. Ações gerais respeitam ajustes locais. Na limpeza explícita de homologação, configuração local é dado operacional: inventário conta sem valores, preserva configuração global e recusa tabelas não classificadas; classificá-la não inicia limpeza nem reprocessamento.

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

Imagens e Acervo SHALL compartilhar um painel recolhível por pasta que mostre herança/personalização/desligamento, valores efetivos, progresso real e ações locais. Estados de sucesso/erro e controles SHALL ser acessíveis e sem overflow móvel. Consultas iniciam ao abrir; polling para ao fechar, desmontar ou ficar sem trabalhos. O painel informa o escopo compartilhado, e o padrão/resumo é identificado como configuração da galeria.

#### Scenario: Abrir pasta restrita compartilhada
- **WHEN** o fotógrafo abre o processamento de uma pasta no Acervo
- **THEN** vê seu escopo e aviso de compartilhamento, sem iniciar processamento ou alterar configuração apenas ao abrir

#### Scenario: Uso móvel com teclado
- **WHEN** o painel é usado em viewport estreita ou navegando por teclado
- **THEN** controles permanecem legíveis, identificados e alcançáveis sem crescimento horizontal por nome longo
