## Purpose

Definir o ciclo de vida seguro, observável e reversível do reconhecimento facial como capacidade de produção da Markina Gallery, sem transportar os controles temporários usados exclusivamente no benchmark privado.

## ADDED Requirements

### Requirement: Ativação de produção por ambiente e rollout autorizado

O sistema SHALL manter `FACIAL_PROCESSING_ENABLED` como kill switch técnico independente por ambiente. Homologação MAY permanecer habilitada para validação funcional após o encerramento e a limpeza do benchmark, mas produção MUST iniciar desligada e somente SHALL ser habilitada após evidência registrada de segurança, privacidade, base legal, calibração, capacidade, recuperação e aprovação humana. O rollout SHALL limitar inicialmente contas ou galerias explicitamente permitidas e SHALL permitir expansão e reversão sem migration destrutiva.

#### Scenario: Deploy ainda não aprovado para produção

- **WHEN** qualquer gate obrigatório de produção estiver ausente, vencido ou reprovado
- **THEN** o subsistema facial permanece indisponível em produção, enquanto upload, navegação e seleção manual continuam saudáveis

#### Scenario: Rollout progressivo aprovado

- **WHEN** todos os gates estiverem aprovados e uma etapa de rollout identificar explicitamente as contas ou galerias permitidas
- **THEN** somente esse escopo recebe indexação e busca facial, com kill switch e rollback verificados antes da ampliação

### Requirement: Indexação administrativa automática sem classificação etária

Quando a capacidade estiver habilitada para uma galeria, o sistema SHALL indexar automaticamente as fotos elegíveis após as prévias necessárias ficarem prontas e SHALL mostrar ao administrador progresso técnico, falhas e cobertura facial agregada. A indexação administrativa SHALL processar adultos e menores da mesma forma técnica, SHALL NOT estimar idade nem depender do gate de referência infantil da cliente, e zero rosto utilizável SHALL contar como processamento concluído.

#### Scenario: Acervo misto publicado pelo fotógrafo

- **WHEN** as prévias protegida e administrativa de uma foto elegível ficam prontas em uma galeria habilitada
- **THEN** a indexação é admitida de forma durável e o painel atualiza processadas, total, fotos com rosto, rostos detectados e falhas sem exibir dado biométrico

#### Scenario: Foto sem rosto utilizável

- **WHEN** a foto contém pessoa de costas, rosto distante, desfocado ou nenhuma observação tecnicamente utilizável
- **THEN** o job termina com sucesso técnico, cobertura facial não é incrementada e upload/publicação permanecem disponíveis

#### Scenario: Administrador solicita reprocessamento

- **WHEN** o administrador aciona `Refazer reconhecimento facial` em uma galeria habilitada após falha ou interrupção
- **THEN** o sistema reconcilia fotos elegíveis sem índice e recoloca falhas técnicas na fila de forma idempotente, sem duplicar o arquivo original, a prévia ou um índice já concluído

### Requirement: Busca facial autenticada e individual da cliente

A cliente SHALL poder enviar uma referência somente após autenticação, vínculo vigente com a Galeria pública, aviso e consentimento versionados. No celular, a interface SHALL oferecer escolhas explícitas para usar uma foto JPEG existente ou abrir a câmera e SHALL NOT forçar captura ao escolher o arquivo existente. O diálogo SHALL usar controles coesos e responsivos, sem expor o campo nativo de arquivo como ação principal. Em desktop, o diálogo SHALL preservar largura legível, hierarquia visual e ações acessíveis sem ultrapassar o viewport. O sistema SHALL aceitar JPEGs de até 30 MiB no navegador, proxy e API, SHALL informar o limite antes do envio e SHALL apresentar mensagem específica quando ele for excedido, preservando as validações de tipo, pixels e descompressão. O detector SHALL limitar a resolução de sua cópia de trabalho sem modificar o arquivo original nem reduzir o limite funcional de 30 MiB. A consulta SHALL continuar em job durável se a cliente fechar a página, SHALL ser recuperável no retorno e SHALL mostrar progresso real. Uma interrupção abrupta SHALL ser retomada por lease e SHALL terminar com resultado sanitizado após o máximo de tentativas, sem manter a interface indefinidamente em `validating_reference`. Ao concluir, `Melhores resultados encontrados` e `Outros resultados encontrados` SHALL aparecer antes do acervo integral, sem expor score, vetor ou identidade inferida.

#### Scenario: Cliente escolhe a origem da referência no celular

- **WHEN** a cliente abre o diálogo de busca facial em um smartphone
- **THEN** ela pode escolher uma foto JPEG da galeria do aparelho ou usar a câmera por ações distintas, com alvo de toque legível, sem pré-visualizar nem persistir a referência no navegador

#### Scenario: Cliente usa a busca facial no desktop

- **WHEN** a cliente abre o diálogo em um navegador desktop
- **THEN** o conteúdo permanece centralizado, legível e contido no viewport, com origem, declaração, consentimento e ações em hierarquia clara

#### Scenario: Cliente seleciona uma referência grande

- **WHEN** a cliente escolhe uma JPEG de até 30 MiB
- **THEN** navegador, proxy e API aceitam o envio sob o mesmo contrato funcional
- **WHEN** o arquivo excede 30 MiB
- **THEN** a interface impede a transferência e informa especificamente o limite de 30 MB

#### Scenario: Cliente abandona e retorna

- **WHEN** a cliente fecha a página após a admissão válida da referência e retorna autenticada enquanto a consulta ainda existe
- **THEN** a interface recupera a consulta mais recente do backend, retoma o progresso e apresenta o resultado terminal sem exigir que a aba original permaneça aberta

#### Scenario: Referência JPEG de alta resolução

- **WHEN** uma JPEG válida dentro do limite de 30 MiB possui resolução superior ao orçamento de trabalho do detector
- **THEN** o provider preserva a referência original e executa detecção sobre cópia proporcional limitada, sem exceder o orçamento de memória definido

#### Scenario: Worker interrompido durante a validação

- **WHEN** o processo termina abruptamente depois de marcar a consulta como `validating_reference`
- **THEN** outro worker retoma o job após o lease e, se o máximo de tentativas já foi excedido, encerra a consulta como falha sanitizada e elimina a referência temporária

#### Scenario: Galeria pública em desktop largo

- **WHEN** a cliente abre a Galeria pública em um navegador desktop largo
- **THEN** a grade usa a largura útil do viewport e a visualização ampliada pode ocupar a área disponível, mantendo a foto inteira sem o limite de leitura de 960 pixels das demais páginas

#### Scenario: Referência tecnicamente inadequada

- **WHEN** a referência contém zero rostos utilizáveis, múltiplos rostos ou qualidade insuficiente
- **THEN** a cliente recebe orientação específica e sanitizada para enviar outra foto, sem criação de seleção, galeria privada ou pedido

### Requirement: Representação e consentimento no fluxo infantil da cliente

O gate de referência infantil SHALL existir somente no fluxo da cliente e MUST permanecer separado da indexação administrativa. Antes de aceitar referência de menor em produção, o sistema SHALL exigir mecanismo não biométrico de comprovação de representação legal, texto específico versionado, registro de consentimento e procedimento de revogação; uma simples variável de ambiente SHALL NOT substituir esses controles.

#### Scenario: Responsável não comprovado

- **WHEN** uma cliente declara que a referência pertence a menor sem representação legal vigente comprovada
- **THEN** o upload facial é recusado de forma genérica e a seleção manual permanece disponível

#### Scenario: Responsável comprovado e consentimento vigente

- **WHEN** a representação legal, o vínculo da galeria e o consentimento específico são válidos
- **THEN** a consulta infantil segue o mesmo pipeline técnico isolado, retenção mínima e autorização repetida aplicados à consulta adulta

### Requirement: Minimização, retenção, revogação e direitos

O sistema SHALL cifrar embeddings e referências, separar chaves por ambiente, excluir a referência em estado terminal ou no máximo em 15 minutos, expirar candidatas no máximo em 24 horas e eliminar índices quando a foto, a galeria, o escopo permitido ou a finalidade deixarem de existir. Auditoria, logs, métricas e notificações SHALL NOT conter imagem, embedding, score, landmarks, caixa facial, nome inferido ou telefone em claro. O procedimento de direitos SHALL localizar, comprovar e eliminar os derivados aplicáveis sem apagar histórico comercial que possua justificativa independente.

#### Scenario: Revogação de uma galeria

- **WHEN** o administrador revoga a capacidade facial de uma galeria
- **THEN** novas consultas são bloqueadas imediatamente, o purge prioritário elimina índices e candidatas daquele escopo e uma prova agregada de limpeza fica auditável

#### Scenario: Referência terminal

- **WHEN** a consulta conclui, falha, é cancelada ou excede o prazo máximo
- **THEN** o arquivo e seu localizador cifrado são eliminados de forma idempotente sem remover seleções ou pedidos legítimos

### Requirement: Capacidade, backpressure e isolamento

O subsistema SHALL admitir de forma durável pelo menos 100 consultas simultâneas sem misturar clientes ou galerias, SHALL limitar concorrência e recursos do processamento pesado e SHALL priorizar rotas interativas e geração de prévias. Sob saturação, o sistema SHALL enfileirar com estimativa/progresso honesto ou recusar novas admissões com resposta temporária retentável, sem perder jobs aceitos nem tornar a seleção manual indisponível.

#### Scenario: Cem clientes enviam referências simultaneamente

- **WHEN** pelo menos 100 clientes autenticadas e vinculadas enviam consultas válidas ao mesmo tempo
- **THEN** cada request e job permanece isolado por cliente e galeria, nenhum job aceito é perdido e a carga respeita os limites do worker e do banco

#### Scenario: Limite operacional atingido

- **WHEN** fila, memória, CPU ou latência ultrapassa o limite configurado
- **THEN** o sistema aplica backpressure, mantém healthchecks e seleção manual e emite somente métricas agregadas acionáveis

### Requirement: Observabilidade e resposta a incidente

Produção SHALL possuir métricas agregadas, SLOs e alertas para admissão, fila, tempo de indexação, tempo de consulta, falhas sanitizadas, retenção, purge, CPU, memória e disponibilidade. O runbook SHALL permitir desligar novas indexações e consultas, preservar evidência não biométrica, eliminar temporários e reverter somente os componentes da Markina Gallery.

#### Scenario: Aumento de falhas técnicas

- **WHEN** a taxa de falhas ou a latência ultrapassa o SLO definido
- **THEN** o alerta identifica ambiente, tipo de job e contagem agregada, e o operador pode suspender o recurso sem expor PII ou biometria

#### Scenario: Incidente de segurança ou privacidade

- **WHEN** houver suspeita de acesso indevido, chave comprometida ou retenção excedida
- **THEN** o kill switch bloqueia novas operações, referências pendentes são eliminadas, chaves e escopos afetados são isolados e o runbook orienta investigação e comunicação
