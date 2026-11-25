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

#### Scenario: Falha durante ou depois da exclusão
- **WHEN** a retirada parcial ou a verificação posterior falha
- **THEN** a operação SHALL parar, preservar todos os alvos ainda existentes e gravar somente diagnóstico estático sanitizado quando possível
- **AND** não tenta rollback ou repetição automática; outra tentativa exige inventário e fingerprint novos

### Requirement: Inventário identifica a origem do mount do Picker

O inventário protegido SHALL incluir os metadados dos mounts na fingerprint e MUST NOT ler ou imprimir o conteúdo dos arquivos montados.

#### Scenario: Mount do Picker encontrado
- **WHEN** um container monta o caminho de configuração do Picker ou seu destino conhecido
- **THEN** o inventário SHALL informar o prefixo do ID do container, os caminhos de origem e destino, o serviço Compose e a label de arquivos Compose quando disponíveis
- **AND** mount presente, origem desconhecida ou origem não reconciliada com a revisão protegida MUST bloquear a retirada

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
