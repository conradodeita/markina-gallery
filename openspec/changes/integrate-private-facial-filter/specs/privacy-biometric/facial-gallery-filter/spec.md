## Purpose

Definir o tratamento biométrico mínimo, isolado e reversível necessário para filtrar possíveis fotos dentro de uma Galeria pública que a cliente já está autorizada a visualizar.

## ADDED Requirements

### Requirement: Gate global e política interna automática

O processamento facial SHALL permanecer desligado por padrão no ambiente. Quando o operador habilitar o subsistema com versão de aviso, referência da hipótese legal, retenção, modelos, criptografia e configuração aplicável a menores válidos, o sistema SHALL criar ou reconciliar automaticamente uma política técnica interna para cada Galeria pública ativa e SHALL NOT exigir declaração, preparação ou ativação manual do fotógrafo. Desligar globalmente SHALL interromper novas indexações e consultas sem retirar seleção manual, pedidos ou histórico.

#### Scenario: Ambiente sem prontidão

- **WHEN** a configuração operacional não possui todos os controles obrigatórios vigentes
- **THEN** o sistema mantém a indexação indisponível, informa o estado no painel sem pedir uma ação jurídica ao fotógrafo e não inicia tratamento biométrico

#### Scenario: Galeria elegível em ambiente habilitado

- **WHEN** uma Galeria pública ativa possui prévias elegíveis e o subsistema global está válido e habilitado
- **THEN** o sistema garante automaticamente a política interna versionada e agenda somente a indexação que estiver ausente ou divergente

#### Scenario: Kill switch global

- **WHEN** o operador desliga o processamento facial global
- **THEN** novas consultas e indexações são recusadas, jobs pendentes são cancelados com limpeza e a jornada manual continua disponível

### Requirement: Indexação assíncrona desacoplada da mídia

O sistema SHALL indexar zero ou mais rostos somente depois que a prévia protegida da foto estiver pronta, em fila facial independente e de baixa prioridade. A indexação SHALL nascer de foto ou derivado novo, mudança explícita de versão, backfill ou retentativa, e SHALL NOT manter varredura recorrente da galeria. O estado facial SHALL ser `disabled`, `pending`, `ready`, `partial`, `failed` ou `purged`; falha facial SHALL NOT impedir publicação, visualização ou seleção manual da foto.

#### Scenario: Prévia pronta em ambiente habilitado

- **WHEN** uma foto elegível conclui as prévias interna limpa e protegida em uma Galeria pública ativa com o subsistema global habilitado
- **THEN** o sistema garante a política interna e enfileira indexação idempotente com galeria, foto, modelo e versão sem ação do fotógrafo e sem bloquear a disponibilidade da prévia

#### Scenario: Falha facial isolada

- **WHEN** detector, modelo ou armazenamento falha durante a indexação
- **THEN** o estado facial registra falha retomável e a foto permanece utilizável pelos fluxos não biométricos autorizados

#### Scenario: Galeria sem alteração

- **WHEN** todas as prévias elegíveis já possuem o mesmo fingerprint e versões de embedding e qualidade
- **THEN** o worker não recalcula a galeria e permanece aguardando novos jobs sem consumo ativo de CPU

### Requirement: Qualidade técnica versionada por rosto

O sistema SHALL calcular indicadores técnicos explicáveis para cada rosto indexado, incluindo nitidez local, corte nas bordas, tamanho/proeminência e pose. Após o gate conservador de similaridade, SHALL classificar somente o rosto correspondente à referência em `best` ou `other`; a qualidade SHALL NOT ocultar ou excluir fotos, inferir estética pessoal ou avaliar beleza, emoção, gênero, raça ou idade.

#### Scenario: Vários rostos na fotografia

- **WHEN** a referência corresponde a um rosto menor e outro rosto é maior ou mais central
- **THEN** o ranqueamento usa a qualidade do rosto correspondente e não atribui à cliente a qualidade do outro rosto

#### Scenario: Correspondência com qualidade inferior

- **WHEN** uma candidata supera o limiar facial mas o rosto correspondente está desfocado, cortado, pequeno ou em pose difícil
- **THEN** a foto permanece acessível em `other` e não é descartada, escondida ou selecionada automaticamente

### Requirement: Índice versionado, criptografado e restrito à galeria

Cada embedding do acervo SHALL pertencer a uma única Galeria pública, foto e versão de modelo, permanecer cifrado em repouso e ser acessível somente ao worker facial. Troca de modelo ou política MUST invalidar o índice anterior e exigir reindexação; nenhuma consulta SHALL comparar vetor de outra galeria ou ambiente.

#### Scenario: Mesmo rosto em outro evento

- **WHEN** uma consulta possui vetor semelhante em outra galeria ou ambiente
- **THEN** o item externo não participa do conjunto comparado nem aparece em resultado, contagem ou mensagem

#### Scenario: Modelo alterado

- **WHEN** a versão ou o hash do modelo configurado muda
- **THEN** o sistema não mistura vetores incompatíveis, marca o índice anterior inválido e reindexa somente após os gates vigentes

### Requirement: Consentimento da cliente e referência com um rosto

A cliente autenticada e autorizada SHALL aceitar um checkbox de consentimento específico e versionado para o uso temporário da foto de referência na procura por possíveis correspondências naquela Galeria pública antes de enviá-la. Esse consentimento SHALL pertencer à cliente e à referência, SHALL NOT ser substituído por declaração do fotógrafo e SHALL NOT ampliar acesso. O sistema SHALL aceitar somente formato, tamanho e resolução permitidos com exatamente um rosto utilizável, e SHALL retornar estados distintos para nenhum rosto, múltiplos rostos, baixa qualidade, índice incompleto, nenhum candidato, cancelamento e falha técnica.

#### Scenario: Referência válida

- **WHEN** a cliente aceita o aviso vigente e envia uma imagem segura com exatamente um rosto utilizável
- **THEN** o sistema registra o recibo do consentimento, inicia consulta somente naquela galeria e informa estado de processamento sem afirmar identidade

#### Scenario: Referência inadequada

- **WHEN** a imagem não possui exatamente um rosto utilizável ou viola limites de segurança
- **THEN** o sistema não executa associação, apresenta orientação específica e elimina o arquivo temporário

### Requirement: Consulta durável, progresso real e snapshot consistente

Cada consulta SHALL ser um job durável independente da presença do navegador. O sistema SHALL congelar o conjunto elegível em um snapshot de índice, expor estados e contagens reais de preparação, comparação e ordenação, e permitir retomar a consulta pelo identificador opaco com autorização repetida. Fechar, atualizar ou abandonar a tela SHALL NOT cancelar o processamento.

#### Scenario: Cliente sai durante a busca

- **WHEN** a cliente fecha a tela depois que o upload foi aceito
- **THEN** o job continua até estado terminal, a referência segue a retenção definida e a consulta pode ser retomada sem novo tratamento duplicado

#### Scenario: Índice ainda em preparação

- **WHEN** a consulta é criada enquanto parte do snapshot ainda não foi indexada
- **THEN** o sistema informa `waiting_index` com contagem `ready/total` e só conclui contra aquele snapshot, sem incorporar silenciosamente fotos carregadas depois

### Requirement: Exclusão da referência e retenção curta

O JPEG de referência e seu embedding SHALL ser eliminados automaticamente em sucesso, falha, cancelamento ou timeout, com teto de 15 minutos. A cliente SHALL poder cancelar/excluir de forma idempotente enquanto o processamento estiver pendente; resultados temporários SHALL expirar em 24 horas ou antes por revogação, nova busca, exclusão manual ou fim da galeria.

#### Scenario: Busca concluída

- **WHEN** a comparação termina com ou sem candidatos
- **THEN** o sistema elimina referência e embedding antes de publicar o estado final e mantém somente IDs temporários de fotos autorizadas até o prazo do resultado

#### Scenario: Exclusão repetida

- **WHEN** cliente ou rotina de retenção solicita novamente a exclusão já concluída
- **THEN** a operação responde com sucesso idempotente e não recria dado, resultado ou auditoria duplicada

### Requirement: Resultado é filtro e não autorização

A busca SHALL retornar somente possíveis fotos já visíveis à cliente na Galeria pública autorizada. Resultado facial SHALL NOT criar ou modificar galeria privada, vínculo, seleção, favorito, comentário, pedido, preço ou permissão; somente a seleção consciente da cliente SHALL chamar o resolvedor comercial existente.

#### Scenario: Candidatas encontradas

- **WHEN** a consulta encontra fotos acima do limiar conservador vigente
- **THEN** o sistema retorna referências ordenadas e deduplicadas somente para aquela cliente e naquela visualização autenticada da mesma Galeria pública, sem persistir identidade inferida ou operação comercial

#### Scenario: Primeira escolha de uma candidata

- **WHEN** a cliente seleciona conscientemente uma foto exibida pelo filtro
- **THEN** o sistema usa exatamente o fluxo de seleção manual para criar ou reutilizar sua única privada operacional daquela Galeria pública

### Requirement: Proteção reforçada para menores

O sistema SHALL manter busca infantil desabilitada enquanto não houver mecanismo não biométrico de comprovação do responsável, consentimento verificável, aviso acessível, avaliação do melhor interesse e RIPD aprovado. A referência SHALL NOT ser usada para estimar idade, autenticar identidade, inferir atributos, treinar modelo ou publicidade.

#### Scenario: Política infantil incompleta

- **WHEN** uma referência é declarada como pertencente a criança e qualquer controle infantil obrigatório está ausente
- **THEN** o sistema bloqueia o tratamento biométrico, preserva a alternativa manual e elimina qualquer upload recebido

### Requirement: Auditoria sem biometria e exercício de direitos

O sistema SHALL auditar política, consentimento, estado, versão do modelo, limiar, contagens agregadas, exclusão, revogação e ator em UTC, sem registrar imagem, embedding, landmarks, caixa facial, similaridade individual ou identidade inferida. Cliente e fotógrafo SHALL possuir ações autorizadas para consultar estado, revogar finalidade e solicitar eliminação sem revelar dados de terceiros.

#### Scenario: Revogação da galeria

- **WHEN** a política facial é revogada ou a finalidade termina
- **THEN** o sistema cancela jobs, expira resultados, elimina índices elegíveis e registra comprovação da limpeza sem apagar histórico comercial

### Requirement: Calibração conservadora e linguagem de possibilidade

O limiar SHALL ser versionado e calibrado para favorecer falsos negativos, com métricas por cenário e revisão antes de cada troca. A interface MUST usar linguagem como `Possíveis fotos encontradas`, SHALL NOT converter similaridade em porcentagem de identidade e SHALL permitir informar resultado incorreto sem treinamento automático.

#### Scenario: Cliente rejeita candidata

- **WHEN** a cliente informa que uma candidata não corresponde à pessoa procurada
- **THEN** o sistema remove o item daquele resultado, registra feedback sem identidade inferida e não altera automaticamente o modelo ou outras galerias
