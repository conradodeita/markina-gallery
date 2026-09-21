> **Decisão substitutiva aprovada em 21/09/2026 — `simplify-mobile-gallery-face-search`:** para novas buscas, toque em região indexada inicia diretamente sem diálogo/aceite ou declaração de idade; upload continua exigindo consentimento específico. Upload infantil exige somente o checkbox único com autodeclaração de responsável e consentimento versionado, sem registro prévio ou prova administrativa de representação. Regras anteriores de representação obrigatória e dois checkboxes ficam substituídas exclusivamente nesse escopo; evidências/controles históricos permanecem. Nome/seleção ficam abaixo das miniaturas; navegação ampliada sempre visível em barra externa abaixo da fotografia, nunca sobreposta. Demais controles de acesso, retenção, revogação e operação permanecem. Contrato completo: `openspec/changes/simplify-mobile-gallery-face-search/`.

## Purpose

Permitir pesquisa facial privada sobre regiões detectadas no JPEG pós-edição temporário, com geometria reutilizável, isolamento e validação mensurável.

## ADDED Requirements

### Requirement: Análise high-res versionada e seletiva

O sistema SHALL analisar a maior versão JPEG recebida, orientada conforme EXIF, antes do ajuste de apresentação, com passes globais e aprofundamento seletivo limitado por orçamento. SHALL consolidar caixas e landmarks no mesmo espaço antes de extrair embeddings. SHALL registrar resolução, passes, tiles, contagens, rejeições e duração sem biometria bruta nos logs.

#### Scenario: Grupo em foto grande
- **WHEN** a análise inicial indica risco mensurável de perda de rostos pequenos
- **THEN** passes adicionais com overlap são executados dentro do orçamento e as detecções repetidas são deduplicadas

#### Scenario: Foto simples
- **WHEN** a análise encontra rostos grandes confiáveis sem sinais de dificuldade
- **THEN** o sistema evita os passes caros e registra a decisão

#### Scenario: Falha parcial de extração
- **WHEN** a extração de embeddings falha e a transação de indexação é revertida para retry
- **THEN** contagens e duração sanitizadas da tentativa permanecem no lifecycle, sem resíduos da foto anterior nem biometria bruta; a fonte não é descartada

### Requirement: Observabilidade administrativa por galeria

O status administrativo SHALL agregar análises high-res da própria galeria: fotos processadas/com faces, faces detectadas/aceitas/rejeitadas, falhas de detecção/extração, duração, fila e idade do job mais antigo. Os valores SHALL descrever a última tentativa de cada fonte, sem somar retries como novas fotos. O diagnóstico por foto SHALL mostrar tentativas e versão de qualidade. Não SHALL exportar regiões, vetores ou conteúdo de imagem nesses agregados.

#### Scenario: Isolamento de métricas
- **WHEN** o administrador consulta o status de uma galeria com retries e fotos de outro evento no banco
- **THEN** os agregados incluem somente as fontes e os jobs daquele escopo; métricas inválidas ou desconhecidas são ignoradas

### Requirement: Regiões normalizadas e espaços isolados

Cada região SHALL possuir ID opaco, foto/galeria consistentes, bbox em [0,1], confiança, qualidade, proveniência, versões e embedding cifrado. Comparações MUST exigir mesmo modelo, versão e dimensão, sem vetores de outros eventos. Regiões antigas sem geometria SHALL permanecer consultáveis pelo mecanismo legado sem inventar overlays.

#### Scenario: Retry de indexação
- **WHEN** a mesma fonte e versão são processadas novamente
- **THEN** os registros são substituídos atomicamente, sem crescimento de duplicatas ou órfãos

#### Scenario: Modelo ou galeria divergente
- **WHEN** uma região não pertence ao espaço ou galeria da consulta
- **THEN** a operação é negada sem expor vetor, resultados ou existência de outro evento

### Requirement: Pesquisa reutiliza índice persistido

Selfie SHALL gerar somente o embedding de consulta. Clique em região SHALL usar somente o embedding persistido indicado pelo UUID. Ambos SHALL repetir autenticação, escopo, consentimento, capacidade, rate limit e retenção. Nenhuma consulta SHALL executar detector nas fotos do acervo.

#### Scenario: Refinamento por região
- **WHEN** cliente autorizado aceita os controles vigentes e escolhe uma região válida
- **THEN** um job durável compara o embedding existente somente com o snapshot da mesma galeria

#### Scenario: Região removida durante espera
- **WHEN** a região de referência é removida ou invalidada antes da execução
- **THEN** a consulta termina sem resultados enganosos e sem fallback de recorte do preview

### Requirement: Resultados e interação sem identidade presumida

Resultados SHALL separar correspondências e possíveis correspondências por calibração de modelo, preservando outras fotos acessíveis. A interface SHALL oferecer overlays adaptativos, zoom/pan e seleção facial acessível; seleção comercial ampliada SHALL ficar fora da imagem e nas miniaturas SHALL ser menor e centralizada abaixo.

#### Scenario: Foto com muitas faces
- **WHEN** o número excede o limiar configurável de overlays automáticos
- **THEN** a imagem abre limpa e permite ativar seleção de pessoa e navegar pelas regiões visíveis

#### Scenario: Ausência de resultado
- **WHEN** uma foto não tem candidata
- **THEN** ela permanece disponível como outra foto sem afirmar ausência da pessoa

### Requirement: Coexistência e validação separada

O sistema SHALL admitir o novo pipeline por flag desligada por padrão, preservar legado e impedir reescaneamento de prévias de fotos high-res concluídas mesmo após desligamento. Recall, retrieval e recursos SHALL ser medidos separadamente em corpus anotado autorizado. EdgeFace SHALL NOT entrar em produção sem aprovação específica dos pesos e calibração própria.

#### Scenario: Rollback da admissão
- **WHEN** a flag high-res é desligada após remover fontes concluídas
- **THEN** os índices e previews duráveis continuam utilizáveis e reindexação incompatível exige reupload

#### Scenario: Corpus indisponível
- **WHEN** faltam imagens ou ground truth
- **THEN** o relatório identifica métricas não medidas e não apresenta testes sintéticos como recall real

#### Scenario: Limite de análise atingido
- **WHEN** a foto excede o orçamento configurado de tiles, candidatos ou embeddings
- **THEN** o processamento permanece limitado e a saturação aparece na telemetria administrativa, sem afirmar recall completo

#### Scenario: Manutenção entre análise e apresentação
- **WHEN** o índice high-res concluiu e a fonte ainda está válida enquanto a mídia aguarda geração
- **THEN** a manutenção preserva esse índice sem expô-lo para consulta até a foto ficar disponível; revogação/purge continua removendo as inferências

#### Scenario: Job antigo após reupload
- **WHEN** uma fonte expirada é reenviada e um job da geração anterior ainda está na fila
- **THEN** o worker cancela o job antigo sem consumir ou invalidar a nova fonte

#### Scenario: Revogação antes do purge físico
- **WHEN** a política facial é revogada e as regiões ainda aguardam exclusão assíncrona
- **THEN** a API deixa de expor essas regiões imediatamente
