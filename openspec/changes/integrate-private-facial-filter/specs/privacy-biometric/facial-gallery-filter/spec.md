> **Decisão substitutiva aprovada em 21/09/2026 — `simplify-mobile-gallery-face-search`:** para novas buscas, toque em região indexada inicia diretamente sem diálogo/aceite ou declaração de idade; upload continua exigindo consentimento específico. Upload infantil exige somente o checkbox único com autodeclaração de responsável e consentimento versionado, sem registro prévio ou prova administrativa de representação. Regras anteriores de representação obrigatória e dois checkboxes ficam substituídas exclusivamente nesse escopo; evidências/controles históricos permanecem. Nome/seleção ficam abaixo das miniaturas; navegação ampliada sempre visível em barra externa abaixo da fotografia, nunca sobreposta. Demais controles de acesso, retenção, revogação e operação permanecem. Contrato completo: `openspec/changes/simplify-mobile-gallery-face-search/`.

## Purpose

Definir o tratamento biométrico mínimo, isolado e reversível necessário para filtrar possíveis fotos dentro de uma Galeria pública que a cliente já está autorizada a visualizar.

## ADDED Requirements

### Requirement: Gate global e política interna automática

Processamento facial SHALL iniciar desligado. Com ambiente, versões, retenção, modelos e criptografia válidos, habilitá-lo SHALL reconciliar a política técnica de cada galeria ativa sem configuração manual do fotógrafo. Adultos e menores no acervo não bloqueiam a indexação administrativa. O kill switch interrompe novas buscas/indexações sem afetar seleção, pedidos ou histórico.

#### Scenario: Ambiente sem prontidão

- **WHEN** a configuração operacional não possui todos os controles obrigatórios vigentes
- **THEN** o sistema não inicia novos jobs, informa falha técnica no painel sem apresentar bloqueio de política nem pedir ação jurídica ao fotógrafo

#### Scenario: Galeria elegível em ambiente habilitado

- **WHEN** uma Galeria pública ativa possui prévias elegíveis e o subsistema global está válido e habilitado
- **THEN** o sistema garante automaticamente a política interna versionada e agenda somente a indexação que estiver ausente ou divergente

#### Scenario: Acervo administrativo contém menores

- **WHEN** fotos do acervo contêm adultos, menores ou ambos e o subsistema global está válido e habilitado
- **THEN** o sistema indexa todas as fotos elegíveis pelo mesmo pipeline automático, sem exigir `FACIAL_MINOR_SEARCH_ENABLED`, declaração, consentimento ou desbloqueio do administrador

#### Scenario: Kill switch global

- **WHEN** o operador desliga o processamento facial global
- **THEN** novas consultas e indexações são recusadas, jobs pendentes são cancelados com limpeza e a jornada manual continua disponível

### Requirement: Indexação assíncrona desacoplada da mídia

Indexação facial SHALL ser assíncrona, de baixa prioridade e independente da entrega de mídia, iniciada apenas por foto/derivado novo, versão, backfill ou retentativa, sem varredura recorrente. O estado agregado é `processing`, `completed` ou `failed`, sem estado de política. Falha facial não bloqueia publicação, visualização ou seleção manual.

#### Scenario: Prévia pronta em ambiente habilitado

- **WHEN** uma foto elegível conclui as prévias interna limpa e protegida em uma Galeria pública ativa com o subsistema global habilitado
- **THEN** o sistema garante a política interna e enfileira indexação idempotente com galeria, foto, modelo e versão sem ação do fotógrafo e sem bloquear a disponibilidade da prévia

#### Scenario: Evento de indexação perdido por gate divergente

- **WHEN** uma execução privada ativa comprova que fotos de seu lote ficaram prontas sem job facial porque um processo persistente reteve configuração anterior
- **THEN** o operador pode executar backfill único, escopado à janela e ao lote autorizados, reutilizando a idempotência normal e preservando fotos, prévias e medição em andamento

#### Scenario: Falha facial isolada

- **WHEN** detector, modelo ou armazenamento falha durante a indexação
- **THEN** o estado facial registra falha retomável e a foto permanece utilizável pelos fluxos não biométricos autorizados

#### Scenario: Observação facial geometricamente inutilizável

- **WHEN** o detector retorna em uma foto uma observação cuja caixa ou landmarks não permitem calcular os indicadores técnicos versionados
- **THEN** o worker descarta somente essa observação, preserva as demais faces válidas e conclui a foto com zero rostos quando nenhuma observação utilizável restar, sem registrar falha operacional

#### Scenario: Galeria sem alteração

- **WHEN** todas as prévias elegíveis já possuem o mesmo fingerprint e versões de embedding e qualidade
- **THEN** o worker não recalcula a galeria e permanece aguardando novos jobs sem consumo ativo de CPU

### Requirement: Progresso administrativo cobre todas as pastas

Etapa 04 SHALL mostrar progresso facial por galeria e foto de conteúdo recebida, em qualquer pasta e durante preparo de prévias; capas ficam fora. Exibe contagens reais, atualiza enquanto há trabalho e termina em `completed`/`failed`, sem percentual inventado ou estado de política. Informa cobertura de fotos com rosto; zero rostos não é falha nem aciona limiar automático sem regra aprovada.

#### Scenario: Upload distribuído entre pastas

- **WHEN** o administrador envia fotos para uma ou mais pastas da mesma Galeria pública com o processamento facial habilitado
- **THEN** etapa 04 conta imediatamente todas as fotos recebidas em `prontas`, `aguardando preparo`, `fila`, `processando` ou `falha`, atualiza enquanto houver `processing`, conclui quando todos terminam e falha se restarem erros/indisponibilidade; não inventa percentual, não mostra gate de política e exclui capas técnicas

#### Scenario: Prévia ainda não gerou job facial

- **WHEN** uma foto já foi aceita, mas sua prévia limpa ou protegida ainda está sendo preparada
- **THEN** a foto participa do total e da contagem de itens aguardando preparo, e o painel não interrompe a atualização por ainda não existir job facial para ela

#### Scenario: Cobertura facial após o processamento

- **WHEN** a Galeria pública possui fotos processadas com e sem rostos detectados
- **THEN** o painel mostra `fotos com rosto/total` e porcentagem sobre todas as fotos recebidas, separadas de `fotos processadas/total`; zero rostos conta como concluído. A cobertura informa decisão humana e não impõe limiar de compartilhamento sem regra aprovada

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

Antes do upload, a cliente autenticada e autorizada SHALL consentir, em versão vigente, o uso temporário da referência naquela galeria; declaração do fotógrafo não substitui o aceite nem amplia acesso. O sistema aceita apenas formato, tamanho e resolução permitidos com exatamente um rosto utilizável e distingue ausência/múltiplos rostos, baixa qualidade, índice incompleto, nenhum candidato, cancelamento e falha técnica.

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

#### Scenario: Cliente retorna pela galeria ou pela notificação

- **WHEN** uma cliente autenticada retorna à mesma Galeria pública sem o identificador salvo na aba original
- **THEN** o sistema recupera somente sua consulta mais recente, ainda válida e pertencente àquela galeria, e reapresenta progresso ou resultados sem revelar consulta de outra cliente

#### Scenario: Índice ainda em preparação

- **WHEN** a consulta é criada enquanto parte do snapshot ainda não foi indexada
- **THEN** o sistema informa `waiting_index` com contagem `ready/total` e só conclui contra aquele snapshot, sem incorporar silenciosamente fotos carregadas depois

#### Scenario: Cem ou mais clientes iniciam consultas

- **WHEN** ao menos 100 clientes autenticadas e vinculadas enviam referências válidas para a mesma Galeria pública em uma janela concorrente
- **THEN** cada consulta é aceita como job durável e isolado por cliente, recebe progresso próprio, não substitui consulta de outra pessoa e pode aguardar capacidade do worker sem depender da aba do navegador

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

Consulta infantil SHALL ficar desabilitada por padrão; o gate vale só para upload/consulta da cliente, não para indexação administrativa. Upload exige checkbox único versionado, autodeclaração e consentimento específico, sem cadastro prévio ou prova. Fora da homologação controlada, exige aviso acessível, melhor interesse e RIPD. Referência não pode estimar idade, identificar pessoa, inferir atributos, treinar ou servir à publicidade.

#### Scenario: Política infantil incompleta

- **WHEN** uma referência é declarada como pertencente a criança e qualquer controle infantil obrigatório está ausente
- **THEN** o sistema bloqueia o tratamento biométrico, preserva a alternativa manual e elimina qualquer upload recebido

#### Scenario: Homologação privada autorizada com menor

- **WHEN** o administrador/fotógrafo inicia uma execução de homologação explicitamente autorizada, vinculada a lote documentado que inclui menores e com todos os controles temporários válidos
- **THEN** o sistema limita o tratamento àquele ambiente, lote, finalidade e janela, audita somente identificadores mínimos e exige purge e desativação do gate infantil ao encerrar

#### Scenario: Continuação autorizada após expiração da janela

- **WHEN** a janela controlada expira com jobs duráveis do mesmo lote ainda pendentes e o administrador/fotógrafo autoriza explicitamente sua conclusão
- **THEN** o sistema MAY reabrir o gate infantil somente por uma nova janela limitada, mantendo idênticos lote, origem, finalidade, autorização, quantidade, responsável e retenção, sem aceitar novas fotos nem ampliar o uso fora daquela homologação

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
