## Purpose

Definir o tratamento biométrico mínimo, isolado e reversível necessário para filtrar possíveis fotos dentro de uma Galeria pública que a cliente já está autorizada a visualizar.

## ADDED Requirements

### Requirement: Gate global e política interna automática

O processamento facial SHALL permanecer desligado por padrão no ambiente. Quando o operador habilitar o subsistema com versões, retenção, modelos e criptografia válidos, o sistema SHALL criar ou reconciliar automaticamente uma configuração técnica interna para cada Galeria pública ativa e SHALL NOT exigir declaração, preparação, autorização sobre menores ou ativação manual do fotógrafo. A presença de adultos ou menores nas fotos do acervo SHALL NOT bloquear nem alterar a indexação administrativa. Desligar globalmente SHALL interromper novas indexações e consultas sem retirar seleção manual, pedidos ou histórico.

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

O sistema SHALL indexar zero ou mais rostos somente depois que a prévia protegida da foto estiver pronta, em fila facial independente e de baixa prioridade. A indexação SHALL nascer de foto ou derivado novo, mudança explícita de versão, backfill ou retentativa, e SHALL NOT manter varredura recorrente da galeria. O estado administrativo agregado SHALL ser somente `processing`, `completed` ou `failed`; estado de política SHALL NOT fazer parte desse contrato. Falha facial SHALL NOT impedir publicação, visualização ou seleção manual da foto.

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

O painel administrativo SHALL exibir na etapa 04, em `Processamento automático` → `Reconhecimento facial`, uma barra de progresso agregada para toda a Galeria pública. O total SHALL incluir cada foto de conteúdo assim que seu upload estiver persistido, independentemente da pasta e mesmo enquanto as prévias ainda estiverem em preparação. A interface SHALL continuar consultando enquanto o estado for `processing`, SHALL encerrar em `completed` quando todas as fotos terminarem e SHALL encerrar em `failed` quando restarem falhas ou o serviço não puder concluir o trabalho. O painel SHALL distinguir contagens reais de fotos prontas, aguardando preparo, na fila, em processamento e com falha sem fabricar percentual, e SHALL NOT exibir estado, gate ou ação de política. Ativos técnicos de capa SHALL NOT participar desse total.

Além do progresso técnico, o painel SHALL informar separadamente a cobertura facial do acervo: quantidade e porcentagem de fotos de conteúdo que possuem ao menos um rosto detectado, usando como denominador o total recebido na Galeria pública. Foto processada com zero rostos SHALL contar como processamento concluído e SHALL NOT ser classificada como falha. A cobertura SHALL ser informativa para a decisão humana de compartilhar o link e SHALL NOT impor limiar automático sem configuração de negócio aprovada.

#### Scenario: Upload distribuído entre pastas

- **WHEN** o administrador envia fotos para uma ou mais pastas da mesma Galeria pública com o processamento facial habilitado
- **THEN** a etapa 04 apresenta imediatamente `prontas/total` para o conjunto recebido em todas as pastas e atualiza a barra até cada foto terminar ou expor uma falha recuperável

#### Scenario: Prévia ainda não gerou job facial

- **WHEN** uma foto já foi aceita, mas sua prévia limpa ou protegida ainda está sendo preparada
- **THEN** a foto participa do total e da contagem de itens aguardando preparo, e o painel não interrompe a atualização por ainda não existir job facial para ela

#### Scenario: Cobertura facial após o processamento

- **WHEN** a Galeria pública possui fotos processadas com e sem rostos detectados
- **THEN** o painel mostra `fotos com rosto/total` e sua porcentagem separadamente de `fotos processadas/total`, sem tratar ausência de rosto como erro

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

O sistema SHALL manter a consulta iniciada por uma cliente com referência infantil desabilitada por padrão. Esse gate SHALL se aplicar somente ao upload temporário da referência e à consulta da cliente; SHALL NOT bloquear a indexação administrativa do acervo, mesmo quando as fotos contenham menores. Em homologação privada, o operador MAY habilitar a consulta infantil somente para uma execução explicitamente autorizada e vinculada a lote enviado pelo administrador/fotógrafo, com origem e finalidade documentadas, acesso autenticado, criptografia, retenção mínima e exclusão controlada. Fora desse modo controlado, a habilitação SHALL exigir mecanismo não biométrico de comprovação do responsável, consentimento verificável, aviso acessível, avaliação do melhor interesse e RIPD aprovado. A referência SHALL NOT ser usada para estimar idade, autenticar identidade, inferir atributos, treinar modelo ou publicidade.

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
