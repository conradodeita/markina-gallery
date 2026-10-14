## ADDED Requirements

### Requirement: Atualização estável da capa na Etapa 03

Enquanto uma capa estiver em processamento, a Etapa 03 SHALL atualizar seu estado e sua prévia em segundo plano sem substituir o editor inteiro por um estado global de carregamento. Cabeçalho, formulário, valores ainda não salvos, foco e posição de rolagem SHALL permanecer estáveis entre consultas. O acompanhamento SHALL terminar quando a capa atingir estado terminal, e falha transitória de consulta SHALL ficar contida na área da capa com recuperação segura.

#### Scenario: Capa permanece em processamento

- **WHEN** consultas sucessivas ainda retornam a capa em processamento
- **THEN** a página permanece visível e estável sem piscar ou remontar o formulário
- **AND** valores digitados, foco e rolagem não são perdidos

#### Scenario: Capa fica pronta

- **WHEN** uma atualização em segundo plano retorna a capa pronta
- **THEN** somente o estado e a prévia correspondentes são atualizados
- **AND** novas consultas automáticas são encerradas

#### Scenario: Atualização transitória falha

- **WHEN** uma consulta de acompanhamento falha depois do carregamento inicial bem-sucedido
- **THEN** o editor permanece utilizável e informa a falha junto da capa
- **AND** a interface oferece ou executa uma nova tentativa segura sem descartar edições
