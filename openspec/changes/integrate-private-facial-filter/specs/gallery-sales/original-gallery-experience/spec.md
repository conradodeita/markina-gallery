## ADDED Requirements

### Requirement: Filtro facial na única jornada visual

O sistema SHALL apresentar a busca facial opcional dentro da Galeria pública já autorizada. Durante e depois da consulta, a cliente SHALL permanecer na mesma superfície; resultados tecnicamente melhores aparecem primeiro, outros resultados correspondentes aparecem em seguida e todas as fotos continuam disponíveis conforme a autorização e a organização vigentes. Os blocos de resultado SHALL existir somente no estado privado da cliente autenticada e SHALL NOT alterar a ordem vista por outros membros.

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
