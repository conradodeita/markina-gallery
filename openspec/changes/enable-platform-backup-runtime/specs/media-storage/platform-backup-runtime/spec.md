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

#### Scenario: Classificar exceção interna sem expor detalhes

- **WHEN** o helper de suporte encontra uma exceção interna cuja classe pertence à allowlist estática
- **THEN** SHALL emitir somente o código de categoria fixo associado; classes desconhecidas SHALL continuar usando support_internal_error
- **AND** texto, classe dinâmica, traceback, caminhos e valores da exceção MUST NOT aparecer no log, e nenhuma fingerprint ou precondição aprovada SHALL ser emitida

#### Scenario: Registro de container falha na validação

- **WHEN** o registro de API, web ou banco não corresponder ao formato fixo esperado
- **THEN** o operador SHALL receber somente um código allowlisted que identifique o papel fixo do container e a classe do campo inválido
- **AND** valores retornados, nomes e IDs de containers, argumentos/saída do comando, exceções, caminhos e dados de configuração MUST NOT aparecer no log
- **AND** nenhuma fingerprint ou precondição aprovada SHALL ser emitida

#### Scenario: Resolver API e web pela identidade ativa e banco pelos labels fixos

- **WHEN** o inventário resolver API, web e banco para compor a impressão digital
- **THEN** SHALL confirmar que a ponte é arquivo regular `root:root`, modo `0755`, link único e que seu blob corresponde ao SHA exato do código de suporte revisado; obter API/web pelo projeto ativo e pelo ID completo retornados por operações fixas vinculadas a esse SHA; inspecionar os IDs e revalidar os labels de projeto e serviço
- **AND** SHALL resolver o banco somente pela combinação exata dos labels Compose `project=markina-gallery` e `service=db`, exigindo um ID completo e revalidando os labels após a inspeção
- **AND** SHALL repetir a resolução ativa de API/web antes de emitir fingerprint e exigir que projeto e ID não tenham mudado
- **AND** as leituras inicial, pré-mutação e pós-instalação do instalador SHALL usar o mesmo SHA exato de suporte aprovado em todas as consultas de inventário
- **AND** MUST NOT selecionar containers por nome, escolher registros antigos por label como fallback para API/web ou usar agregados diagnósticos como identidade; metadados inseguros, falha, ausência, duplicidade, saída inválida, blob da ponte divergente ou mudança SHALL abortar com código estático allowlisted, sem fingerprint ou precondição
- **AND** IDs e saídas brutas da ponte MUST NOT aparecer em logs

#### Scenario: Emitir resumo de inventário sem identificadores

- **WHEN** o inventário normal concluir com sucesso
- **THEN** a saída SHALL conter somente o SHA do checkout, estado/saúde dos serviços fixos, revisão do schema, espaço disponível e estado das unidades do runtime
- **AND** MUST NOT incluir IDs ou imagens de containers, horários de início, metadados de caminhos, conteúdo de configuração ou saída bruta da ponte
- **AND** os IDs completos SHALL permanecer somente em memória para a inspeção e a composição da fingerprint

#### Scenario: Instalar o forced command de backup

- **WHEN** a revisão do wrapper exato passar pelo CI e o instalador protegido confirmar novamente o fingerprint atual do host
- **THEN** somente o forced command root-owned SHALL ser trocado atomicamente, SHALL preservar uma cópia anterior, SHALL continuar recusando comandos arbitrários e SHALL provar que todos os containers mantiveram identidade, imagem, estado e início
- **AND** a operação SHALL adquirir o lock comum de release e SHALL NOT recriar containers, alterar portas, proxy, banco ou recursos compartilhados

#### Scenario: Restaurar o forced command anterior após instalação concluída

- **WHEN** uma instalação do wrapper tiver sido concluída, o inventário seguinte revelar falha, e o operador solicitar restauração protegida de uma cópia anterior identificada pelo recibo
- **THEN** o canal SHALL aceitar somente a cópia root-only preservada no diretório fixo e cujo SHA-256 corresponda ao recibo aprovado, exigindo fingerprint atual, CI da `main` no SHA exato e aprovação do ambiente protegido
- **AND** o recibo SHALL ser a linha `previous_wrapper_backup_sha256` do resumo da instalação protegida concluída; a operação SHALL aceitar somente esse digest e localizar exatamente uma cópia correspondente no diretório fixo, sem input de caminho
- **AND** SHALL preservar a versão atualmente ativa em uma nova cópia verificável antes de substituir o wrapper em troca atômica
- **AND** SHALL verificar arquivo regular, owner/mode/link, SHA-256, sintaxe e recusa de comando arbitrário, e SHALL confirmar a invariância de todos os containers
- **AND** se qualquer verificação posterior à troca falhar, SHALL restaurar atomicamente a versão que estava ativa antes da tentativa de rollback e manter ambos os recibos/cópias
- **AND** MUST NOT aceitar caminho arbitrário, alterar API/web, banco, Compose, Drive, configuração de backup, serviço ou timer, nem executar inventário mutável

#### Scenario: Cópia anterior ausente, ambígua ou divergente

- **WHEN** a cópia fixa não existir, mais de uma cópia corresponder aos critérios, a identidade/metadados forem inseguros ou o SHA-256 divergir do recibo
- **THEN** a restauração MUST abortar antes da troca, sem remover ou alterar qualquer wrapper ou cópia preservada, e SHALL emitir somente falha sanitizada

#### Scenario: Recuperação compensatória não comprovada

- **WHEN** a validação da versão restaurada falhar e a troca atômica de retorno à versão ativa antes da tentativa falhar ou não puder ser confirmada por metadados, SHA-256, sintaxe, allowlist e invariância dos containers
- **THEN** o fluxo MUST parar sem nova troca, repetição automática ou limpeza, preservar o alvo no estado observado e todas as versões e recibos envolvidos, e emitir somente o código estático allowlisted `wrapper_restore_fallback_unverified`
- **AND** o estado ativo SHALL ser informado como não verificado, sem revelar caminhos, hashes, IDs ou conteúdo
- **AND** qualquer recuperação manual SHALL exigir fluxo protegido próprio com contrato e implementação revisados, merge autorizado, CI verde da `main` no SHA exato, novo preflight somente leitura, fingerprint atual e autorização operacional explícita aprovada pelo ambiente protegido
- **AND** MUST NOT executar comandos shell/SSH ad hoc nem remover cópias ou recibos

#### Scenario: Staging fixo de recuperação já existe

- **WHEN** o staging fixo da troca ou o staging de recuperação compensatória já existir
- **THEN** a operação MUST abortar sem sobrescrever nem remover o artefato preexistente e SHALL emitir falha sanitizada
- **AND** SHALL preservar a cópia ativa e a cópia indicada pelo recibo

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

### Requirement: Preparar e restaurar o bootstrap protegido do runtime

Antes do inventário do backup, o suporte SHALL usar operações fixas e protegidas, CI da `main` no SHA exato, fingerprint atual, lock comum e aprovação `production`. SHALL preservar cópias/recibos root-only, alterar somente ponte, forced command e `origin/main`, e oferecer compensação única. A fingerprint de suporte MUST NOT ser aceita como inventário do runtime; checkout, aplicações, banco, containers, Drive e timer MUST NOT ser alterados.

#### Scenario: Inventário read-only usa credenciais protegidas de produção

- **WHEN** `support-inventory` ou `restore-support-inventory` acessa o host pelo canal SSH atual
- **THEN** SHALL exigir aprovação do ambiente `production`, que contém as credenciais SSH usadas pelo fluxo
- **AND** MUST NOT disponibilizar essas credenciais no ambiente `production-preflight` sem revisor obrigatório
- **AND** SHALL limitar a operação aos dados read-only descritos no contrato, sem alterar host, containers ou configuração

#### Scenario: Preparar a base de suporte sem publicar runtime

- **WHEN** `prepare-support` for executado com SHA atual da `main`, CI verde, fingerprint de suporte idêntica e estado revalidado sob o lock
- **THEN** SHALL registrar em recibo root-only a presença/hash/metadados anteriores dos executáveis, a presença/SHA anterior da referência Git, os blobs candidatos, a impressão agregada dos containers e as cópias verificadas
- **AND** SHALL atualizar por compare-and-swap somente `refs/remotes/origin/main`, trocar atomicamente os dois executáveis fixos e confirmar blob/hash, owner/mode/link, allowlist e invariância de containers
- **AND** SHALL preservar todas as cópias/recibos sem limpeza automática e deixar o runtime de backup sem alteração

#### Scenario: Falha parcial durante preparação

- **WHEN** qualquer operação depois da primeira mutação ou qualquer verificação pós-troca falhar
- **THEN** SHALL executar no máximo uma compensação verificável na ordem inversa, respeitando a presença/ausência e os hashes registrados
- **AND** se a compensação não puder ser provada, MUST NOT sobrescrever valor desconhecido nem tentar novamente; SHALL preservar os alvos observados, cópias/recibos e emitir somente `support_preparation_rollback_unverified`

#### Scenario: Recibo, backup ou staging preexistente

- **WHEN** nome de cópia, recibo ou staging fixo já existir antes da preparação
- **THEN** MUST abortar antes de alterar qualquer alvo, sem sobrescrever ou remover o artefato preexistente
- **AND** SHALL manter o lock/fingerprint sem aprovação para preparação e emitir somente erro sanitizado

#### Scenario: Preparação concluída requer inventário novo do runtime

- **WHEN** `prepare-support` terminar com sucesso
- **THEN** o operador SHALL executar em despacho separado `operation=inventory`, que coleta a fingerprint completa do runtime, saúde, schema, espaço, portas/subdomínio e serviços/timers
- **AND** a fingerprint de suporte MUST NOT liberar `install-wrapper`, vínculo, Drive, backup, restore ou ativação de timer

#### Scenario: Restaurar suporte preparado por recibo

- **WHEN** `restore-support` receber somente o digest de recibo apresentado, com fingerprint read-only atual, CI verde da `main` no SHA exato e aprovação do ambiente protegido
- **THEN** SHALL preservar primeiro os dois executáveis ativos e o estado atual da ref em cópias/recibo root-only e restaurar os valores anteriores registrados pelo recibo de preparação em ordem inversa
- **AND** SHALL aceitar somente correspondência única e íntegra de recibo/cópias no diretório fixo, confirmar metadados/hash/sintaxe/allowlist/ref e invariância de containers e preservar todos os recibos/cópias
- **AND** caminho arbitrário, cópia ausente/ambígua/adulterada, fingerprint divergente, ref/arquivo com valor inesperado ou falha de verificação MUST abortar sem sobrescrever estado desconhecido

#### Scenario: Compensar falha na restauração protegida

- **WHEN** a restauração alterar um ou mais alvos e falhar antes de comprovar o estado anterior
- **THEN** SHALL tentar uma única compensação para o estado exato imediatamente anterior à restauração usando somente cópias e recibo dessa operação
- **AND** se a compensação falhar ou não puder ser verificada, SHALL parar, preservar estado observado, cópias e recibos e emitir somente `support_restore_fallback_unverified`; MUST NOT limpar, repetir ou chamar shell/SSH ad hoc
