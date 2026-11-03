## ADDED Requirements

### Requirement: Ordem específica do proprietário resolve o bloqueio infantil de retomada

Para esta restauração, a operação SHALL registrar `owner-minor-production-unblock-20261103` como autorização operacional do proprietário para o fluxo infantil vigente, substituindo o bloqueio adicional do `AGENTS.md`. O recibo SHALL NOT afirmar parecer jurídico independente, representação comprovada ou calibração medida.

#### Scenario: Proprietário substitui expressamente a regra impeditiva

- **WHEN** a ordem específica está documentada e vinculada ao fingerprint e ao escopo da restauração já autorizada
- **THEN** o operador pode prosseguir com os gates técnicos comprovados sem exigir novo aceite para a regra substituída
- **AND** preserva consentimento condicional versionado no upload, OTP, vínculo, isolamento, política ativa, retenção, criptografia e auditoria

#### Scenario: Evidência humana é apresentada como avaliação externa

- **WHEN** o registro tenta transformar a ordem operacional em parecer jurídico, representação comprovada ou medição de precisão
- **THEN** a evidência é corrigida para registrar somente a decisão realmente recebida antes de qualquer declaração de conclusão

### Requirement: Restauração geral sem calibração exige decisão explícita

O modo `owner-authorized-general-restore-v1` SHALL permitir a restauração geral sem medição prévia somente com referência de autorização do proprietário vinculada ao manifesto e recibo. O código SHALL exigir calibração por padrão; o modo autorizado SHALL registrar dispensa, nunca aprovação de medição, e preservar todos os demais controles de tenant, política, versões e acesso.

#### Scenario: Proprietário autoriza restauração geral sem calibração

- **WHEN** o manifesto registra o modo autorizado e referência de decisão e a etapa é `general`
- **THEN** os consumidores usam as flags explícitas para não exigir calibração/rollout prévio, e o operador comprova o escopo de políticas ativas sem inserir calibração fictícia

#### Scenario: Dispensa não possui autorização ou etapa correspondente

- **WHEN** falta a referência, o modo diverge ou a etapa não é `general`
- **THEN** a operação é recusada e o modo estrito preserva suas exigências anteriores

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

#### Scenario: Fotos elegíveis existentes estão sem job ou índice

- **WHEN** o inventário pós-ativação identifica um conjunto finito de fotos de conteúdo autorizadas, com processamento permitido, prévias prontas, sem `PhotoAnalysis`, job corrente ou embeddings
- **THEN** a operação revalida o conjunto e a contagem na mesma transação e pode enfileirar somente essas fotos pela rotina idempotente existente
- **AND** preserva os demais índices, políticas, schema e dados comerciais, sem executar reindexação geral

### Requirement: Parada facial comprova o encerramento cooperativo

O operador SHALL comprovar a parada pelo encerramento normal do mesmo container inventariado, vinculando ID, imagem, comando, configuração, início, código zero e fase ao journal. Workers faciais SHALL concluir o ciclo atual após `SIGTERM` e não iniciar outro. O operador SHALL NOT depender de arquivo ACK externo nem enviar `SIGKILL` automaticamente.

#### Scenario: Worker facial termina o ciclo atual após SIGTERM

- **WHEN** o operador envia `SIGTERM` ao worker facial inventariado
- **THEN** o worker finaliza o ciclo atual, inicia nenhum ciclo subsequente e o operador registra o encerramento normal do mesmo ID antes da troca

#### Scenario: Parada excede o prazo ou sai com erro

- **WHEN** um consumidor não encerra em até 120 segundos, sai com código diferente de zero ou sua identidade muda durante a parada
- **THEN** o operador não o recria, não envia `SIGKILL` e tenta restaurar a política de reinício e o mesmo container original; a falha permanece registrada

### Requirement: Troca e recuperação preservam camadas e mounts

Diretórios estruturais de mounts SHALL exigir prova de ausência de conteúdo subjacente antes de serem aceitos como camada sem dados.

#### Scenario: Docker criou diretórios de montagem na camada

- **WHEN** o diff contém somente destinos de mounts declarados ou seus ancestrais
- **THEN** a exportação TAR em streaming comprova diretórios sem arquivos, links ou entradas especiais subjacentes e confere identidade, mounts e diff antes/depois; nenhum TAR é extraído ou persistido
- **AND** qualquer diferença fora desse caso bloqueia a recriação

O operador SHALL conferir a camada gravável antes e depois de parar um container. Candidatos SHALL usar raiz read-only, manter os mounts persistentes e gravar temporários somente em `tmpfs` limitado. A recuperação MUST NOT remover candidato com identidade, mounts ou camada persistente inesperados.

#### Scenario: Camada original muda durante parada

- **WHEN** `docker diff` mostra conteúdo ou diretórios estruturais não comprovados antes ou depois da parada de um container original
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

### Requirement: Operador facial preserva a coordenação de release compartilhada

O adaptador real SHALL exigir UID/GID root antes do acesso ao host. O operador SHALL validar o diretório fixo `deploy-state` como `ubuntu:ubuntu 0700` e manter nele o lock e os marcadores conhecidos em `PENDING`. SHALL NOT alterar proprietário, modo ou conteúdo compartilhado.

A conversão de `OSError` para recusa do lock SHALL limitar-se à abertura, validação de metadados e aquisição do lock. Exceções do corpo protegido SHALL preservar a causa operacional original.

#### Scenario: Diretório compartilhado pertence a ubuntu e operador é root

- **WHEN** o operador root valida o diretório compartilhado `ubuntu:ubuntu 0700` e o lock existente `ubuntu:ubuntu 0600`
- **THEN** obtém o lock global sem alterar proprietário, modo, tamanho ou conteúdo do pai, lock ou manifesto

#### Scenario: Adaptador é executado sem UID/GID root

- **WHEN** o adaptador operacional é iniciado por uma identidade diferente de root:root
- **THEN** recusa o destino antes de acessar Docker, ler o manifesto ou criar o estado privado

#### Scenario: Lock global tem metadados inseguros

- **WHEN** o lock não é arquivo regular, único hard link, `ubuntu:ubuntu 0600`, ou já está ocupado
- **THEN** o operador recusa a operação sem truncar, recriar ou corrigir o lock

#### Scenario: Operação protegida falha depois de adquirir o lock

- **WHEN** o corpo protegido lança `OSError` depois da aquisição bem-sucedida
- **THEN** o operador preserva o erro operacional e não o apresenta como lock ocupado

### Requirement: Estado da restauração facial é privado e isolado

Diários, recibos e snapshots faciais SHALL ficar somente em `deploy-state/facial-runtime-restoration`, `root:root 0700`. `inventory` SHALL ser somente leitura; `prepare` pode criar o filho ausente. Symlink, tipo, dono, grupo ou modo divergente SHALL bloquear sem reparo automático.

Arquivo privado obrigatório ausente SHALL produzir a recusa específica `arquivo_privado_ausente`; o operador não SHALL inferir, sintetizar ou contornar evidência ausente.

#### Scenario: Estado facial dedicado está ausente

- **WHEN** `inventory` verifica o estado e o filho privado ainda não existe
- **THEN** a consulta continua sem criar arquivos ou diretórios, e `prepare` pode criar somente o filho fixo `root:root 0700`

#### Scenario: Estado facial tem metadados inseguros

- **WHEN** o filho privado é symlink, tem tipo, proprietário ou modo divergente
- **THEN** a operação é recusada antes de qualquer alteração de serviço ou configuração e não corrige metadados automaticamente

#### Scenario: Recibo privado obrigatório está ausente

- **WHEN** uma operação tenta ler um recibo de recuperação obrigatório que não existe
- **THEN** recusa com `arquivo_privado_ausente` antes de alterar serviços, configuração ou dados

### Requirement: Manifesto de candidatos permanece protegido no caminho existente

O manifesto SHALL permanecer no caminho fixo `deploy-state/facial-runtime-candidates.json`, como arquivo regular root-owned `0600`. A validação SHALL conferir separadamente o pai `ubuntu:ubuntu 0700` e vincular `support_sha` ao checkout limpo do operador; nenhum caminho pode ser escolhido pela CLI. Rebind pode alterar somente esse campo, atomicamente sob o lock global.

#### Scenario: Manifesto possui caminho ou metadados inseguros

- **WHEN** o manifesto está ausente, é symlink, tem tipo, proprietário, modo ou contagem de links divergente
- **THEN** a preparação é recusada sem relocá-lo ou alterar o pai compartilhado

#### Scenario: Manifesto diverge do checkout do operador

- **WHEN** `support_sha` não corresponde ao checkout limpo, ou o rebind altera qualquer outro valor do manifesto
- **THEN** o operador recusa a preparação e preserva o arquivo existente

#### Scenario: Outra operação deixou marcador pendente

- **WHEN** há marcador compartilhado listado em `PENDING` ou journal facial in-flight no estado novo ou legado
- **THEN** a operação recusa a preparação e preserva integralmente os artefatos encontrados

### Requirement: Preparação reproduz o perfil Compose dos consumidores faciais

`prepare` SHALL resolver o modelo e calcular `config --hash` com `--profile facial` habilitado para os cinco serviços candidatos. Cada hash SHALL corresponder ao label `com.docker.compose.config-hash` do container inventariado. Todas as verificações Compose SHALL terminar antes de criar o diretório privado específico da operação ou alterar containers.

#### Scenario: Hash de worker facial exige perfil

- **WHEN** um serviço candidato é declarado no perfil Compose `facial`
- **THEN** a resolução do modelo e o cálculo de hash incluem `--profile facial`, e o hash observado coincide com o baseline inventariado

#### Scenario: Falha ao resolver ou comparar configuração Compose

- **WHEN** a configuração ou o hash de qualquer consumidor não puder ser resolvido ou não coincidir com seu baseline
- **THEN** `prepare` recusa a operação antes de criar o diretório privado da operação ou substituir qualquer serviço

### Requirement: Comparação de configuração normaliza somente DNS não configurado

Ao comparar a configuração dos containers, o operador SHALL tratar `HostConfig.Dns` igual a `[]` e `null` como ausência equivalente de DNS explícito. Listas não vazias SHALL continuar sendo comparadas exatamente.

#### Scenario: Docker reporta DNS vazio com representações distintas

- **WHEN** o baseline e o candidato representam DNS não configurado como `[]` e `null`, em qualquer ordem
- **THEN** a comparação aceita essa diferença de representação e mantém todas as demais verificações de configuração, mounts, camada gravável e identidade
- **AND** qualquer lista DNS não vazia divergente continua bloqueando a operação

### Requirement: Recuperação identifica o candidato parado pelo journal

Quando containers históricos compartilham os labels de projeto e serviço, a recuperação SHALL selecionar o candidato pelo ID integral de `active_ids` no journal e conferir seus labels, imagem e configuração. Outro container ativo SHALL bloquear a recuperação. Sem identidade persistida, a recusa por ambiguidade SHALL permanecer.

#### Scenario: Projeto contém containers históricos do mesmo serviço

- **WHEN** o candidato atual está parado e existem containers antigos parados com os mesmos labels de projeto/serviço
- **THEN** a recuperação seleciona o ID integral comprovado pelo journal e restaura a imagem/configuração original
- **AND** a ausência ou divergência do ID, ou outro container ativo, bloqueia a substituição

### Requirement: Recuperação aceita retry somente após restauração comprovada

Se uma recuperação recriar o baseline e falhar antes de registrar a conclusão, a próxima tentativa SHALL manter esse baseline ativo durante a quiescência e aceitá-lo somente quando imagem, configuração, política de reinício e saúde correspondam ao recibo. Para API, SHALL repetir a validação e reload do Nginx. Qualquer estado parcial divergente SHALL continuar bloqueado.

#### Scenario: Recuperação interrompida após substituir a API

- **WHEN** o baseline foi recriado, mas o journal ainda contém a identidade do candidato e a intenção de recuperar a API
- **THEN** a nova tentativa não para o baseline já restaurado, verifica seu estado e repete o reload gracioso no mesmo Nginx
- **AND** um estado sem essa intenção, sem saúde ou configuração compatível é recusado

### Requirement: Nginx recarrega a resolução após substituir a API

Após recriar o container da API, o operador SHALL validar a configuração do Nginx e emitir reload gracioso no mesmo container inventariado, para atualizar o endereço do upstream. SHALL manter identidade, imagem, configuração montada e bind de porta do Nginx. A verificação SHALL aguardar ambos `/api/health` e `/healthz` retornarem 200, com retry limitado a 120 segundos para a prontidão do upstream; esgotado o prazo, a operação permanece incompleta.

#### Scenario: API recebe novo endereço de rede

- **WHEN** uma fase substitui o container da API e o Nginx pode manter em memória o endereço anterior
- **THEN** o operador executa `nginx -t` e reload gracioso, mantém o mesmo container/configuração/porta e confirma os dois health checks
- **AND** falha na validação/reload ou ausência de 200 após 120 segundos mantém a fase incompleta e segue o procedimento de recuperação
