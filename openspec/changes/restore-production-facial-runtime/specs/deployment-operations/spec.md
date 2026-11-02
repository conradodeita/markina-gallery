## ADDED Requirements

### Requirement: Restauração facial preserva o ambiente e a versão saudáveis

A restauração facial SHALL preservar o contexto `production`, schema, dados e correções da versão saudável observada. O pacote SHALL identificar imagens e arquivos por digest, revalidar o inventário imediatamente antes da aplicação e excluir alterações SaaS locais não revisadas.

#### Scenario: Configuração preservada pertence ao ambiente anterior

- **WHEN** os containers faciais parados pertencem a `staging`, enquanto API e banco já operam em `production`
- **THEN** a operação recusa iniciar esses containers como estão e prepara uma configuração coerente com o ambiente atual

#### Scenario: Candidato perde uma correção da API ativa

- **WHEN** o inventário identifica comportamento ou arquivo da API saudável ausente no candidato
- **THEN** a preparação falha antes da substituição de serviços, preserva a versão ativa e registra a divergência

#### Scenario: Inventário mudou durante a preparação

- **WHEN** schema, imagens, configuração, serviços ou bindings diferem do fingerprint revisado
- **THEN** a aplicação é recusada antes da primeira mutação

### Requirement: Preparação facial valida dependências e modelos antes da exposição

A preparação SHALL validar arquitetura, dependências e integridade dos modelos em imagens isoladas sem acesso a banco ou mídia reais. Enquanto os gates de ativação não forem satisfeitos, SHALL manter o processamento real indisponível e SHALL NOT baixar ou substituir modelos implicitamente.

#### Scenario: API sem dependência ou cache facial

- **WHEN** a imagem da API não possui uma dependência ou arquivo exigido para a configuração habilitada
- **THEN** a operação informa o requisito técnico ausente e recusa ligar a flag no serviço ativo

#### Scenario: Modelo preservado validado

- **WHEN** os bytes dos modelos preservados correspondem ao manifesto fixado e à arquitetura aprovada
- **THEN** eles podem compor o candidato sem alterar a versão do motor, os limiares ou o acervo indexado

#### Scenario: Baseline sem manifesto facial

- **WHEN** o baseline da API ou do worker geral ainda não contém o manifesto facial
- **THEN** o candidato pode acrescentar somente o manifesto com o SHA fixado e os pesos previamente verificados; qualquer outro manifesto, peso ou alteração de dependência fora da allowlist MUST ser recusado

#### Scenario: Todos os consumidores recebem candidatos próprios

- **WHEN** o operador recebe candidatos para a API, worker geral e três workers faciais
- **THEN** cada candidato SHALL corresponder ao digest baseline daquele serviço, e a ausência ou reutilização do candidato de outro serviço SHALL ser recusada

### Requirement: Ativação restaurada exige evidência e escopo explícitos

A ativação SHALL registrar autorização humana, evidências reais dos gates vigentes, escopo inicial e configuração coerente antes de habilitar processamento. A operação MUST NOT fabricar calibração, inferir aprovação jurídica ou converter registros de outro ambiente para contornar uma recusa.

#### Scenario: Ordem de ligar sem evidência de calibração

- **WHEN** a reativação foi autorizada, mas o código exige uma aprovação de calibração ausente no banco
- **THEN** a autorização é preservada, a pendência é informada e nenhum registro de aprovação é criado sem evidência correspondente

#### Scenario: Gates e escopo comprovados

- **WHEN** as evidências foram revisadas, o inventário continua válido e a etapa inicial identifica o escopo autorizado
- **THEN** a operação habilita somente a etapa aprovada e comprova a busca autenticada, retenção e saúde antes de ampliar a exposição

### Requirement: Restauração facial não amplia implicitamente a exposição do legado

O operador SHALL conferir o efeito da compatibilidade legada sobre galerias sem rollout. A ausência de registro SHALL NOT ser tratada como allowlist explícita da nova etapa; qualquer preparação para delimitar escopo SHALL preservar embeddings e evitar suspensão ou purge implícitos.

#### Scenario: Flag alcançaria galerias além da etapa aprovada

- **WHEN** a simulação de elegibilidade mostra galerias fora do escopo inicial habilitadas pelo fallback legado
- **THEN** a ativação é bloqueada até um plano explícito de delimitação ser revisado e validado, sem alterar o contrato legado silenciosamente

### Requirement: Recuperação facial preserva dados financeiros e índices anteriores

A operação SHALL registrar fases e recuperação por imagem/configuração. Antes de trocar serviços, SHALL verificar backup e recuperação compatíveis. Falhas SHALL interromper novas admissões e recuperar os serviços autorizados sem restaurar banco indiscriminadamente, apagar índices anteriores ou alterar recursos externos ao projeto.

#### Scenario: Falha após habilitação

- **WHEN** a verificação de saúde ou a busca autenticada falha após a troca dos serviços
- **THEN** a operação segue a recuperação da fase registrada, preserva pedidos e pagamentos concorrentes e registra consultas temporárias que precisem de reconciliação controlada

#### Scenario: Recuperação não pode ser comprovada

- **WHEN** imagens, configuração ou recibo de recuperação estão ausentes ou divergentes
- **THEN** a aplicação é recusada e o ambiente saudável permanece em execução

### Requirement: Parada facial comprova o encerramento cooperativo

O operador SHALL comprovar a parada pelo encerramento normal do mesmo container inventariado, vinculando ID, imagem, comando, configuração, início, código zero e fase ao journal. Workers faciais SHALL concluir o ciclo atual após `SIGTERM` e não iniciar outro. O operador SHALL NOT depender de arquivo ACK externo nem enviar `SIGKILL` automaticamente.

#### Scenario: Worker facial termina o ciclo atual após SIGTERM

- **WHEN** o operador envia `SIGTERM` ao worker facial inventariado
- **THEN** o worker finaliza o ciclo atual, inicia nenhum ciclo subsequente e o operador registra o encerramento normal do mesmo ID antes da troca

#### Scenario: Parada excede o prazo ou sai com erro

- **WHEN** um consumidor não encerra em até 120 segundos, sai com código diferente de zero ou sua identidade muda durante a parada
- **THEN** o operador não o recria, não envia `SIGKILL` e tenta restaurar a política de reinício e o mesmo container original; a falha permanece registrada

### Requirement: Troca e recuperação preservam camadas e mounts

O operador SHALL conferir a camada gravável antes e depois de parar um container. Candidatos SHALL usar raiz read-only, manter os mounts persistentes e gravar temporários somente em `tmpfs` limitado. A recuperação MUST NOT remover candidato com identidade, mounts ou camada persistente inesperados.

#### Scenario: Camada original muda durante parada

- **WHEN** `docker diff` mostra alteração não vazia antes ou depois da parada de um container original
- **THEN** o operador reinicia esse mesmo container e aborta antes de substituição, preservando a camada e os mounts

#### Scenario: Candidato está restrito a escrita temporária

- **WHEN** um candidato facial é iniciado
- **THEN** sua raiz é somente leitura, `/tmp` e `/run` são `tmpfs` limitados, os mounts duráveis permanecem idênticos e a validação registra camada persistente vazia

### Requirement: CLI facial limita destino e confirma a fase

A CLI SHALL expor apenas inventário, preparação e fases fixas. Host, projeto, serviços, comandos e diretórios SHALL vir de constantes do operador; cada fase que grava SHALL exigir confirmação interativa vinculada à operação e fase.

#### Scenario: CLI recebe destino ou comando arbitrário

- **WHEN** a CLI recebe host, projeto, serviço, comando Docker ou diretório de estado fora dos valores fixos do operador
- **THEN** a chamada é recusada antes de acessar o host ou gravar um recibo

#### Scenario: Confirmação da CLI não vincula a fase

- **WHEN** a confirmação interativa não corresponde à operação e à fase pedidas
- **THEN** a CLI recusa a ação e não invoca a fase mutável

### Requirement: Conclusão facial depende da experiência autenticada

A restauração SHALL ser declarada concluída somente com evidência da versão carregada, configuração coerente, workers saudáveis e busca autenticada no escopo aprovado. Saúde isolada ou flag verdadeira SHALL NOT comprovar caixas faciais, processamento e retorno dos resultados.

#### Scenario: Flag verdadeira sem resultado funcional

- **WHEN** a flag está verdadeira, mas a consulta não chega a um estado terminal verificável ou a interface não apresenta o resultado autorizado
- **THEN** a restauração permanece inconclusiva, com estado e próxima ação registrados
