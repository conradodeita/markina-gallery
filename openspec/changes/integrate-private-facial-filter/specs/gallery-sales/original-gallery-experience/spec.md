## ADDED Requirements

### Requirement: Filtro facial na única jornada visual

A busca facial opcional SHALL permanecer na Galeria pública autorizada: a cliente vê melhores correspondências e depois outros resultados antes do acervo integral, sem perder fotos autorizadas. Os blocos são privados à cliente autenticada, não criam outra superfície nem alteram a ordem dos demais membros.

#### Scenario: Resultado disponível

- **WHEN** a busca facial autorizada encontra candidatas
- **THEN** a galeria mostra `Melhores resultados encontrados` e `Outros resultados encontrados` acima do acervo integral, preserva pastas, favoritos, seleção e cotação individuais e não cria um segundo card de galeria

#### Scenario: Nova busca na mesma origem

- **WHEN** a cliente pesquisa outra pessoa na mesma Galeria pública
- **THEN** o bloco temporário é substituído ou composto conforme a ação explícita da cliente, elimina duplicatas e mantém um único carrinho e total

### Requirement: Estados acessíveis e alternativa manual

A interface SHALL explicar consentimento, processamento, nenhum rosto, vários rostos, baixa qualidade, índice incompleto, nenhum candidato, falha, cancelamento e expiração. Em todos os estados, SHALL manter a navegação e seleção manual utilizáveis e oferecer nova tentativa segura quando aplicável.

#### Scenario: Foto de referência com baixa qualidade

- **WHEN** o backend rejeita a referência por qualidade insuficiente
- **THEN** a interface orienta iluminação, enquadramento e nitidez sem sugerir que a pessoa não está na galeria

### Requirement: Progresso retomável sem bloquear a galeria

A interface SHALL mostrar progresso real de preparação do índice e etapas de validação, busca e ordenação sem fabricar percentual. A cliente SHALL poder continuar navegando, fechar a tela e retomar a mesma consulta; a alternativa manual SHALL permanecer utilizável enquanto o job continua.

#### Scenario: Busca continua fora da tela

- **WHEN** a cliente navega para outra tela ou fecha o navegador durante o processamento
- **THEN** a consulta permanece durável e a galeria apresenta seu estado atualizado quando ela retorna autenticada
