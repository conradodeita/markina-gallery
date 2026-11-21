# Spec Delta

## ADDED Requirements

### Requirement: Configuração e chave do backup operacional

O chamador de backup SHALL usar uma chave operacional própria e um vínculo protegido a uma única pasta global autorizada na conta Workspace escolhida. SHALL existir uma cópia offline da chave autenticada para recuperação sob custódia do proprietário.

#### Scenario: Configuração ou credencial incompatível

- **WHEN** a chave, instalação, origem, destino, escopo ou permissão divergir da configuração revisada
- **THEN** o chamador MUST abortar sem copiar o banco e registrar um código técnico sem expor credenciais

### Requirement: Autorização mínima da pasta global

O escopo OAuth SHALL permanecer `drive.file`. A seleção SHALL conceder acesso somente ao item escolhido. O token de acesso SHALL ser curto e ficar somente em memória no navegador; o refresh token MUST NOT ser exposto ao navegador.

#### Scenario: Seletor disponível no console do proprietário

- **WHEN** o console autorizado receber do monitor Drive `availability=authorization_recorded` e `scope=platform_owner`
- **THEN** SHALL apresentar o formulário do seletor; o campo de escopo operacional do monitor MUST NOT ser interpretado como escopo OAuth, e o endpoint de sessão SHALL continuar validando `drive.file` após reautenticação

#### Scenario: Seleção do destino global

- **WHEN** o Picker emitir um evento intermediário de carregamento antes da seleção
- **THEN** o seletor SHALL continuar visível, sem registrar pasta ou iniciar autorização; somente seleção, cancelamento ou erro terminal SHALL encerrar a janela

#### Scenario: Confirmação da pasta global

- **WHEN** o proprietário selecionar pelo app a pasta `Pick-your-Pic Global` dentro de `Oracle-Production-Backups`
- **THEN** o app SHALL confirmar que o item é uma pasta privada de propriedade do usuário, sob a raiz esperada, autorizada para o app e capaz de receber arquivos; a seleção SHALL ser registrada sem token e a ferramenta root-only SHALL vincular seu ID à configuração protegida mantendo `enabled=false`

#### Scenario: Erro ao confirmar a seleção no Picker

- **WHEN** o Google Picker emitir a ação terminal `ERROR` ao confirmar uma seleção
- **THEN** o app SHALL encerrar o diálogo, mostrar uma mensagem genérica e sanitizada, não criar uma candidata nem enviar pedido de autorização, e MUST NOT registrar ou vincular o ID da pasta; tokens, IDs e detalhes internos do provedor MUST NOT aparecer na mensagem ou nos logs

#### Scenario: Retorno de foco durante a seleção

- **WHEN** o foco retornar do Picker ao console e a interface revalidar a propriedade da sessão
- **THEN** o console SHALL ocultar e bloquear seus controles durante a consulta, preservar em memória a instância do seletor e apresentar a candidata ou erro somente após confirmar novamente o acesso; a seleção MUST NOT enviar autorização automaticamente
- **AND** recusa, falha da consulta ou logout SHALL descartar a seleção, fechar o Picker e impedir que callbacks ou respostas antigas restaurem o fluxo; a autorização da pasta SHALL continuar exigindo senha e novo TOTP no backend

#### Scenario: Pasta não autorizada ou fora da raiz

- **WHEN** a pasta não for própria, estiver em drive compartilhado, não tiver autorização do app, estiver fora da raiz esperada ou não aceitar novos itens
- **THEN** o app MUST recusar o vínculo e o chamador MUST abortar sem copiar o banco

#### Scenario: Publicação sem ativação do backup

- **WHEN** o app e o runtime forem publicados antes da autorização do destino e da prova sintética
- **THEN** o serviço e o timer SHALL permanecer desativados e nenhuma cópia real SHALL ser iniciada

#### Scenario: Organização futura por tenant

- **WHEN** o operador preparar a raiz `Pick-your-Pic Tenants`
- **THEN** essa pasta SHALL permanecer apenas reservada até change própria implementar backup/restauração lógica por tenant, sem alterar a rotina de backup global

### Requirement: Execução interna agendada e manual

O chamador SHALL produzir o backup diário global e permitir acionamento manual pelo operador usando o mesmo lock e os mesmos controles, sempre dentro do escopo do projeto.

#### Scenario: Repetição da cópia diária

- **WHEN** a execução for repetida ou acionada manualmente para o mesmo ponto diário
- **THEN** o chamador SHALL reconciliar ou retomar o mesmo artefato e preservar cópias anteriores

### Requirement: Verificação pós envio e restauração distinta

O chamador SHALL enviar só o arquivo cifrado e verificar tamanho, SHA-256, autenticação do pacote e contexto antes de registrar cópia conferida. O registro de recuperação comprovada SHALL exigir restauração isolada independente.

#### Scenario: O destino confirma envio sem prova de recuperação

- **WHEN** o arquivo for aceito pelo Google sem um restore comprovado
- **THEN** a rotina MUST manter separados os estados de envio, leitura conferida e restauração comprovada

### Requirement: Ativação isolada e reversível

Instalar e ativar o agendamento SHALL exigir inventário, prova sintética e aprovação específica. MUST NOT recriar serviços de aplicação ou modificar backup e agendamento de terceiros.

#### Scenario: Necessidade de interromper rotina

- **WHEN** o operador desativar o agendamento
- **THEN** a rotina SHALL deixar de iniciar execuções novas e preservar os artefatos já gerados e o catálogo

### Requirement: Instalação e operação protegidas do runtime

A instalação do runtime SHALL aceitar somente artefato construído para o SHA exato com CI aprovada e dependências fixadas por hash. A operação remota SHALL usar comandos em lista permitida e inventário somente de leitura com impressão digital; MUST NOT aceitar comandos, caminhos ou artefatos arbitrários. A instalação SHALL manter serviço, timer e destino desativados, sem recriar API/web nem alterar serviços compartilhados.

#### Scenario: Instalar runtime sem ativar backup

- **WHEN** o operador aprovar a fingerprint do inventário e o artefato corresponder ao SHA e ao hash aprovados
- **THEN** o runtime SHALL ser instalado em caminho root-only versionado, preservando a versão anterior e mantendo unidades systemd desativadas e paradas, `destination.enabled=false` e os containers de aplicação inalterados

#### Scenario: Recusar inventário ou artefato divergente

- **WHEN** o SHA/CI, a fingerprint, a identidade do host, o artefato, as permissões ou o estado de produção divergirem do que foi revisado
- **THEN** a operação MUST abortar antes de qualquer escrita persistente e reportar somente uma falha técnica sanitizada

#### Scenario: Diagnóstico sanitizado de falha no inventário

- **WHEN** uma consulta fixa do inventário falhar
- **THEN** o operador SHALL receber somente um código técnico estático permitido ou uma categoria fixa de I/O/comando; nenhuma fingerprint ou precondição aprovada SHALL ser emitida
- **AND** mensagens de exceção, caminhos, saídas de comandos, dados de configuração, segredos, tokens, chaves e IDs do Drive MUST NOT aparecer no log

#### Scenario: Instalar o forced command de backup

- **WHEN** a revisão do wrapper exato passar pelo CI e o instalador protegido confirmar novamente o fingerprint atual do host
- **THEN** somente o forced command root-owned SHALL ser trocado atomicamente, SHALL preservar uma cópia anterior, SHALL continuar recusando comandos arbitrários e SHALL provar que todos os containers mantiveram identidade, imagem, estado e início
- **AND** a operação SHALL adquirir o lock comum de release e SHALL NOT recriar containers, alterar portas, proxy, banco ou recursos compartilhados

#### Scenario: O estado de containers compartilhados divergir

- **WHEN** qualquer container mudar entre os inventários estáveis antes e depois da preparação do artefato
- **THEN** a instalação MUST abortar antes da troca do runtime, sem alterar serviço ou timer, e reportar falha sanitizada

### Requirement: Ensaio sintético do destino global

Com destino root-only vinculado e `enabled=false`, a operação sintética SHALL usar somente conteúdo sintético próprio, sem snapshot ou leitura do banco de produção, tenant ou mídia de cliente. SHALL conferir releitura integral, tamanho e SHA-256 e remover somente o objeto criado pelo próprio ensaio, confirmando sua ausência. Credenciais, tokens e IDs do Drive MUST NOT aparecer em logs.

#### Scenario: Ensaio sintético aprovado

- **WHEN** o operador autorizado iniciar o ensaio com o runtime e timer desativados e a pasta global validada
- **THEN** o sistema SHALL enviar um único item sintético identificável por execução, reler e comparar bytes, tamanho e SHA-256, excluir somente o ID criado nessa execução e confirmar a ausência do item
- **AND** o sistema SHALL preservar `destination.enabled=false`, sem executar `pg_dump`, backup real ou ação na raiz reservada `Pick-your-Pic Tenants`
- **AND** o vínculo e o ensaio SHALL ocorrer sob o lock comum de release e somente depois de revalidar o fingerprint aprovado e o recibo do runtime instalado

#### Scenario: Falha ou limpeza incompleta no ensaio

- **WHEN** envio, leitura, soma de verificação, exclusão ou confirmação de ausência falhar
- **THEN** o sistema MUST NOT declarar o ensaio aprovado, SHALL manter serviço/timer/destino desativados e SHALL tentar remover somente o item criado pelo próprio ensaio
- **AND** se a remoção não puder ser confirmada, SHALL reportar estado sanitizado que exija reconciliação, sem apagar outros objetos

### Requirement: Montagem protegida do seletor sem troca da web

A ponte SHALL oferecer operação fixa de configuração somente da API para o mount do Picker. SHALL preservar imagem e versão da API, web e testemunhas, usar lock e journal durável e publicar a base somente após prova de saúde, schema, configuração e flag facial. MUST NOT aceitar paths, mounts ou comandos arbitrários.

#### Scenario: Reconhecimento do suporte aprovado no gate de escopo

- **WHEN** o gate API/web avaliar o suporte desta operação
- **THEN** SHALL aceitar nominalmente `.github/workflows/production-google-picker-config.yml` e `scripts/test_production_app_picker.py`, mantendo a recusa de workflows, testes e workers não revisados e a verificação dos blobs de runtime

#### Scenario: Base de produção reconciliada antes da configuração

- **WHEN** o release inerte anterior estiver comprovado por versão ativa, imagens e recibos saudáveis da API/web
- **THEN** o manifesto SHALL usar esse release como base de classificação, preservando os pins de runtime e sem classificar mudanças exclusivamente de suporte como nova publicação da aplicação

#### Scenario: Recriação autorizada para o Picker

- **WHEN** o operador aprovar o fingerprint atual e o arquivo protegido for válido
- **THEN** a ponte SHALL preservar a API anterior parada, criar somente a API com o bind read-only aprovado e manter a web intacta

#### Scenario: Interrupção da troca

- **WHEN** uma fase ficar incompleta ou qualquer identidade divergir
- **THEN** a ponte MUST bloquear repetição cega e oferecer inventário e recuperação explícitos somente da API, preservando todos os containers
