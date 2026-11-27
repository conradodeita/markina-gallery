## ADDED Requirements

### Requirement: Retirada delimitada do backup global descontinuado

A retirada SHALL eliminar da operação a configuração, as entradas de execução, credenciais dedicadas e cópias verificadas da tentativa descontinuada. MUST preservar o banco, os dados de clientes, a mídia, integrações compartilhadas e seus mecanismos de recuperação.

#### Scenario: Console do proprietário após publicação

- **WHEN** o proprietário consulta o armazenamento externo
- **THEN** o Console SHALL manter a conexão e os registros do Drive e apresentar somente o estado dos recursos que continuam no seu escopo
- **AND** a API MUST deixar de oferecer a seleção e a autorização da pasta global descontinuada

#### Scenario: Retirada de credencial ou cópia

- **WHEN** uma credencial, chave ou cópia tem origem e uso exclusivo comprovados
- **THEN** sua retirada SHALL usar o canal autorizado para o ambiente e ser confirmada por evidência sem segredo ou dado pessoal
- **AND** uma dependência ainda ativa ou uma identidade incerta MUST bloquear a remoção do item correspondente

### Requirement: Remoção do runtime legado protegida por fingerprint

A remoção no servidor SHALL ocorrer somente pelo workflow protegido `production-app-compose-bridge-install.yml`, na `main` com CI verde, sob aprovação do ambiente `production` e usando alvos fixos. MUST revalidar a fingerprint sob o lock comum antes de remover qualquer item.

#### Scenario: Inventário e remoção autorizada
- **WHEN** o inventário atual mostra serviço inativo, timer inativo e desabilitado, mount do Picker ausente, diretórios/unidades com identidade esperada e endpoints da aplicação saudáveis
- **AND** a fingerprint submetida corresponde integralmente à coleta revalidada
- **THEN** o workflow SHALL remover somente os diretórios exclusivos, duas unidades systemd e configuração do Picker definidos no design
- **AND** preserva PostgreSQL, tabelas, dados de clientes, OAuth/Drive compartilhados, containers, Compose, recibos do suporte e recursos de terceiros
- **AND** registra recibo root-only sanitizado e comprova saúde HTTPS e ausência dos alvos após a retirada

#### Scenario: Fingerprint divergente, mount ou runtime ainda ativo
- **WHEN** qualquer item, precondição, health, identidade, mount, unidade, lock ou fingerprint diverge
- **THEN** o workflow MUST abortar antes de excluir
- **AND** não executa SQL, migration, Compose, restart, Drive ou operação em outro projeto

#### Scenario: Layout da configuração antiga é inesperado
- **WHEN** `/etc/pyp-backup` contém caminhos aninhados, outros nomes, diretórios no lugar de arquivos ou modos diferentes do layout conhecido
- **THEN** a pré-condição da retirada MUST bloqueá-la antes de excluir qualquer alvo
- **AND** o layout conhecido contém somente `destination.json`, `keyring.json` e `source.json` como arquivos regulares diretos `root:root` no modo `0400`, podendo qualquer um deles estar ausente; `source.json` é configuração exclusiva do runtime aposentado, e sua inclusão não afirma que ele seja a entrada observada no host

#### Scenario: Inventário identifica a categoria de uma entrada inesperada sem expor seu nome
- **WHEN** o inventário encontra uma entrada de nível superior fora da allowlist de runtime, configuração ou estado legado, ou uma entrada de configuração inconsistente no snapshot
- **THEN** ele SHALL abortar antes de gerar fingerprint ou autorizar remoção
- **AND** retornará somente `backup_retirement_unexpected_runtime_layout`, `backup_retirement_unexpected_config_layout` ou `backup_retirement_unexpected_state_layout`, ou `backup_retirement_unexpected_config_entry` para a inconsistência no snapshot
- **AND** o diagnóstico MUST NOT revelar nome, caminho, conteúdo, credencial, owner, mode, ID ou outro metadado da entrada
- **AND** a allowlist desta change e os critérios de elegibilidade permanecem explícitos e fixos; o inventário não os amplia dinamicamente

#### Scenario: Bind mount presente em árvore que seria removida
- **WHEN** o inventário Linux encontra um mountpoint no alvo ou em qualquer descendente de uma árvore protegida, inclusive bind mount no mesmo filesystem
- **THEN** ele SHALL obter a evidência pela tabela de mounts do processo, sem depender somente de `os.path.ismount()`
- **AND** a ausência de mountpoints relevantes SHALL integrar o snapshot vinculado à fingerprint
- **AND** um mountpoint encontrado MUST bloquear a fingerprint de aprovação e qualquer mutação, sem remover unidades, arquivos ou diretórios
- **AND** a tabela de mounts indisponível ou malformada MUST bloquear antes de qualquer exclusão
- **AND** o parser SHALL decodificar somente escapes Linux previstos para espaço, tabulação, nova linha e barra invertida; escape desconhecido MUST invalidar o inventário

#### Scenario: Mount muda entre preflight e remoção recursiva
- **WHEN** um mountpoint aparece em qualquer alvo depois do inventário ou antes de uma chamada de remoção recursiva
- **THEN** o helper SHALL revalidar as três árvores antes da primeira mutação e o alvo imediatamente antes de cada remoção recursiva
- **AND** qualquer diferença MUST abortar antes de remover o alvo afetado, preservando os alvos ainda existentes

#### Scenario: Falha durante ou depois da exclusão
- **WHEN** a retirada parcial ou a verificação posterior falha
- **THEN** a operação SHALL parar, preservar todos os alvos ainda existentes e gravar somente diagnóstico estático sanitizado quando possível
- **AND** não tenta rollback ou repetição automática; outra tentativa exige inventário e fingerprint novos

### Requirement: Inventário identifica a origem do mount do Picker

O inventário protegido SHALL incluir os metadados dos mounts na fingerprint e MUST NOT ler ou imprimir o conteúdo dos arquivos montados.

#### Scenario: Mount do Picker encontrado
- **WHEN** um container monta o arquivo de configuração do Picker, seu destino conhecido ou um diretório ancestral que cubra qualquer um desses caminhos
- **THEN** o inventário SHALL informar o prefixo do ID do container, os caminhos de origem e destino, o serviço Compose e a label de arquivos Compose quando disponíveis
- **AND** mount presente, origem desconhecida ou origem não reconciliada com a revisão protegida MUST bloquear a retirada

#### Scenario: OAuth compartilhado sem configuração do Picker
- **WHEN** um container monta somente `/etc/pyp-google-drive/oauth-client.json` em `/run/secrets/google-drive-oauth-client.json`
- **THEN** o inventário SHALL classificar `picker_mount` como ausente e MUST NOT apresentar esse bind como configuração do Picker
- **AND** o digest agregado dos containers SHALL continuar incluindo todos os mounts, inclusive o OAuth compartilhado
- **AND** a retirada MUST NOT alterar ou remover o cliente OAuth, sua configuração ou seus dados

#### Scenario: Bind de diretório que cobre o Picker
- **WHEN** a origem ou o destino de um bind é um diretório ancestral que cobre o caminho configurado do Picker
- **THEN** o inventário SHALL classificar o Picker como montado e bloquear a retirada
- **AND** caminho relativo, não canônico ou inválido MUST falhar fechado sem divulgar valores

### Requirement: Inventário restringe dados locais à estrutura antiga

O inventário SHALL aceitar somente caminhos e formatos de arquivo gravados pelo runtime antigo dentro de `/var/lib/pyp-backup`.

#### Scenario: Contagem agregada dos artefatos locais
- **WHEN** o inventário encontra a estrutura conhecida de catálogo, lock e artefatos
- **THEN** informa contagens e bytes agregados de artefatos cifrados e parciais sem exibir nomes ou IDs
- **AND** qualquer arquivo, tipo, modo ou caminho inesperado MUST bloquear a remoção antes de exclusão

### Requirement: Banco e recuperação fria permanecem preservados

A retirada do backup global descontinuado MUST NOT remover ou alterar schema, migrations, registros, OAuth compartilhado, catálogo, cobrança ou recuperação de mídia por fotógrafo.

#### Scenario: Auditoria do banco
- **WHEN** o repositório é inspecionado para identificar estruturas exclusivas da tentativa de backup global
- **THEN** migrations e tabelas `media_archive_*` e `google_drive_connection_state` continuam preservadas por atenderem à recuperação fria/integração atual
- **AND** nenhuma migration destrutiva é criada ou executada nesta retirada
