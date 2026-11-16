> **Decisão substitutiva aprovada em 21/09/2026 — `simplify-mobile-gallery-face-search`:** para novas buscas, toque em região indexada inicia diretamente sem diálogo/aceite ou declaração de idade; upload continua exigindo consentimento específico. Upload infantil exige somente o checkbox único com autodeclaração de responsável e consentimento versionado, sem registro prévio ou prova administrativa de representação. Regras anteriores de representação obrigatória e dois checkboxes ficam substituídas exclusivamente nesse escopo; evidências/controles históricos permanecem. Nome/seleção ficam abaixo das miniaturas; navegação ampliada sempre visível em barra externa abaixo da fotografia, nunca sobreposta. Demais controles de acesso, retenção, revogação e operação permanecem. Contrato completo: `openspec/changes/simplify-mobile-gallery-face-search/`.

## Purpose

Definir o ciclo de vida seguro, observável e reversível do reconhecimento facial como capacidade de produção da Markina Gallery, sem transportar os controles temporários usados exclusivamente no benchmark privado.

## ADDED Requirements

### Requirement: Ativação de produção por ambiente e rollout autorizado

`FACIAL_PROCESSING_ENABLED` SHALL ser kill switch independente por ambiente. Produção nova/não autorizada fica desligada até evidências de segurança, privacidade, base legal, calibração, capacidade e recuperação e aprovação humana; deploy autorizado preserva estado ativo. Rollout começa em contas/galerias permitidas e admite expansão/reversão sem migration destrutiva. Homologação MAY seguir habilitada após limpeza do benchmark.

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

Upload SHALL exigir autenticação, vínculo e consentimento versionado. Interface SHALL oferecer controles responsivos e opções distintas de JPEG/câmera no celular. Browser, proxy e API SHALL aceitar JPEGs até 30 MiB e validar tipo, pixels e descompressão; detecção usa cópia proporcional limitada. Jobs duráveis mantêm progresso e retomam após fechamento/lease, com estado sanitizado terminal. Resultados antecedem o acervo sem score, vetor ou identidade inferida.

#### Scenario: Cliente escolhe a origem da referência no celular

- **WHEN** a cliente abre o diálogo de busca facial em um smartphone
- **THEN** ela pode escolher JPEG existente ou câmera em ações distintas, com alvo legível; campo nativo não é a ação principal e a referência não é pré-visualizada nem persistida no navegador

#### Scenario: Cliente usa a busca facial no desktop

- **WHEN** a cliente abre o diálogo em um navegador desktop
- **THEN** o conteúdo permanece centralizado, legível e contido no viewport, com origem, declaração, consentimento e ações em hierarquia clara

#### Scenario: Cliente seleciona uma referência grande

- **WHEN** a cliente escolhe uma JPEG de até 30 MiB
- **THEN** browser, proxy e API aceitam até 30 MiB, informam esse limite antes do envio e preservam validações de tipo, pixels e descompressão
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
- **THEN** a cliente recebe orientação sanitizada para reenviar; não se cria seleção, galeria privada ou pedido

#### Scenario: Resultados não revelam dados biométricos

- **WHEN** uma busca autorizada termina com candidatas
- **THEN** a UI mostra grupos `Melhores resultados encontrados` e `Outros resultados encontrados` antes do acervo completo, sem score, vetor, identidade inferida ou dado facial técnico

### Requirement: Representação e consentimento no fluxo infantil da cliente

O gate de referência infantil SHALL existir somente no fluxo da cliente, separado da indexação administrativa. O servidor SHALL exigir checkbox único, desmarcado por padrão, com autodeclaração de responsável e consentimento específico versionado, registrar o aceite e permitir revogação. Não SHALL exigir cadastro ou documento de representação; variável de ambiente não substitui consentimento.

#### Scenario: Responsável sem cadastro prévio consente

- **WHEN** uma cliente autenticada e vinculada envia referência infantil válida sem registro prévio de representação e marca o checkbox vigente
- **THEN** a consulta é admitida sem documento ou aprovação administrativa, usando os controles técnicos e de retenção da busca adulta

#### Scenario: Consentimento infantil ausente

- **WHEN** uma cliente envia referência infantil sem aceite explícito e vigente
- **THEN** o servidor recusa o upload antes do processamento e mantém a seleção manual disponível

### Requirement: Minimização, retenção, revogação e direitos

Referências e embeddings SHALL ser cifrados com chaves separadas por ambiente; referências expiram no terminal/até 15 minutos e resultados em até 24 horas. Índices são removidos quando foto, galeria, escopo ou finalidade acabam. Logs, métricas e avisos excluem mídia e dados biométricos/identificadores; direitos eliminam derivados sem apagar histórico comercial justificável.

#### Scenario: Revogação de uma galeria

- **WHEN** o administrador revoga a capacidade facial de uma galeria
- **THEN** novas consultas são bloqueadas imediatamente, o purge prioritário elimina índices e candidatas daquele escopo e uma prova agregada de limpeza fica auditável

#### Scenario: Referência terminal

- **WHEN** a consulta conclui, falha, é cancelada ou excede o prazo máximo
- **THEN** o arquivo e seu localizador cifrado são eliminados de forma idempotente sem remover seleções ou pedidos legítimos

#### Scenario: Prazo de resultados e registros operacionais

- **WHEN** uma referência termina, um resultado expira ou o sistema grava log, métrica ou notificação
- **THEN** referências desaparecem até 15 minutos, candidatas em até 24 horas e nenhum registro inclui imagem, embedding, score, landmarks, caixa facial, nome inferido ou telefone em claro

#### Scenario: Exercício de direitos sobre dados faciais

- **WHEN** uma pessoa exerce direito aplicável sobre derivados faciais
- **THEN** o procedimento localiza, comprova e exclui os derivados do escopo sem remover histórico comercial com fundamento independente

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
