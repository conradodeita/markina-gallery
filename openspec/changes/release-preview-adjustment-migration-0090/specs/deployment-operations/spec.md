# Spec Delta

## ADDED Requirements

### Requirement: Release dedicado da migration de intensidade de prévias
O sistema SHALL oferecer operações manuais separadas para inventariar e publicar exclusivamente a migration `20261026_0090`, avançando de `20261025_0089` para `20261026_0090` e iniciando apenas os runtimes compatíveis previstos no plano aprovado. O fluxo SHALL falhar fechado diante de SHA, schema, diff ou serviço divergente.

#### Scenario: Origem e alvo aprovados
- **WHEN** o SHA candidato está integrado à `main`, todos os checks exigidos passaram, o inventário confirma schema `20261025_0089` e o fingerprint exato foi aprovado
- **THEN** o release aplica somente `20261026_0090`, publica os runtimes aprovados e confirma schema `20261026_0090` antes de liberar tráfego

#### Scenario: Schema ou escopo divergente
- **WHEN** o inventário aponta revisão diferente, o diff contém outra migration ou runtime não aprovado, ou o estado muda após aprovação
- **THEN** o procedimento falha antes de alterar banco, containers ou configuração

### Requirement: Backup e aprovação precedem a migration de produção
O release SHALL validar um backup recente e restaurável, executar preflight somente-leitura separado e vincular a aprovação humana ao fingerprint completo do SHA e do estado operacional observado. A credencial mutável SHALL permanecer indisponível ao preflight.

#### Scenario: Backup ou aprovação ausente
- **WHEN** o backup não pode ser verificado, o fingerprint está ausente/divergente ou não houve aprovação específica
- **THEN** nenhum escritor é interrompido e nenhuma migration ou publicação é iniciada

### Requirement: Recuperação da release 0090 falha fechada
O release SHALL preservar versão e imagens anteriores e SHALL NOT executar downgrade, restauração do banco ou rollback automático após iniciar a migration. Falha SHALL manter o tráfego fechado e registrar estado suficiente para recuperação explicitamente aprovada.

#### Scenario: Falha após início da migration
- **WHEN** Alembic iniciou e a verificação de schema, saúde ou smoke falha
- **THEN** o fluxo preserva backup, schema e artefatos, não declara sucesso nem executa downgrade automático, e exige reconciliação antes de liberar tráfego

### Requirement: Atualização restrita do wrapper de preflight
O sistema SHALL oferecer uma operação manual protegida que instale atomicamente somente o wrapper versionado e com SHA/blob verificados no caminho root-owned aprovado. A operação SHALL preservar backup e permissões `root:root 0755`, SHALL NOT alterar `authorized_keys` nem tocar em serviços, banco, imagens ou runtimes e SHALL verificar a recusa de comandos SSH arbitrários.

#### Scenario: Wrapper instalado com identidade exata
- **WHEN** a operação manual na `main` passa CI e aprovação do environment `production`, e o SHA/blob do wrapper corresponde ao checkout versionado
- **THEN** a cópia root-owned é substituída atomicamente, a anterior é preservada em backup e proprietário/modo/hash são conferidos

#### Scenario: Blob, sudo ou chave restrita diverge
- **WHEN** o arquivo, permissões, acesso root não interativo ou regra SSH restrita diferem do contrato esperado
- **THEN** a instalação falha fechada, não altera `authorized_keys` nem serviços e não inicia preflight ou release
### Requirement: Diagnóstico sanitizado de serviço duplicado no inventário 0090

O inventário 0090 SHALL recusar serviços ativos desconhecidos ou duplicados. Históricos SHALL estar encerrados, sem restart automático e fora da seleção API/web do Compose 2.35.1. Seus IDs e hashes de metadados SHALL integrar o fingerprint, sem expor dados privados nem autorizar remoção. Esta classificação substitui a recusa incondicional de nomes repetidos entre ativos e históricos.

#### Scenario: Containers com nome de serviço repetido
- **WHEN** dois ou mais containers ativos do projeto compartilham o mesmo serviço, ou um histórico pode ser selecionado para substituição API/web
- **THEN** o inventário falha fechado e informa o serviço conhecido, a quantidade e os estados, sem gerar fingerprint

#### Scenario: Identidade sanitizada de web duplicado
- **WHEN** dois containers web são observados
- **THEN** o diagnóstico informa classificações restritas da identidade e igualdade de imagem, sem imprimir dados arbitrários dos containers

#### Scenario: Auditoria de containers da Markina durante conflito
- **WHEN** o preflight detecta um conflito web e todos os objetos consultados pertencem ao projeto Markina
- **THEN** o relatório lista até 100 objetos com metadados limitados e prefixos únicos, sem nomes brutos ou caminhos e sem afirmar que um container pode ser removido

#### Scenario: Rótulos Compose de containers históricos
- **WHEN** o relatório sanitizado inclui containers parados
- **THEN** informa a presença ou ausência dos rótulos config-hash, one-off e número Compose sem expor seus valores brutos

#### Scenario: Nome ausente ou desconhecido
- **WHEN** o rótulo do serviço está ausente ou não integra a lista reconhecida
- **THEN** o diagnóstico informa somente uma categoria genérica, preservando a recusa e sem imprimir o rótulo bruto

### Requirement: Preservação verificável dos containers históricos no release 0090
O release SHALL fixar Compose 2.35.1, desabilitar remoção de órfãos e usar serviços explícitos com `--no-deps`. SHALL comparar identidade, imagem, estado, configuração, restart, montagens e redes dos históricos antes da manutenção, antes da DDL e antes de liberar tráfego. Divergências SHALL interromper o fluxo. A preservação SHALL ser comprovada em runner descartável sem acessar o daemon compartilhado ou produção.

#### Scenario: Prova real isolada
- **WHEN** o CI executa `run --rm --no-deps` e `up --no-deps` com substituição real de API/web
- **THEN** históricos API/web sem rótulos Compose, migration parada, serviços fora do modelo e seus arquivos sintéticos montados permanecem intactos

#### Scenario: Históricos preservados
- **WHEN** os históricos são inequivocamente classificados e suas assinaturas permanecem iguais em todas as verificações
- **THEN** somente os serviços ativos aprovados participam da operação, sem iniciar migrate ou remover órfãos

#### Scenario: Histórico muda ou versão diverge
- **WHEN** um histórico desaparece, reinicia ou muda de metadados, ou o Compose não é 2.35.1
- **THEN** o fluxo falha fechado; antes da DDL nenhum banco é alterado, depois da DDL mantém a barreira e exige recuperação

#### Scenario: Diagnóstico volátil de saúde em container encerrado
- **WHEN** apenas logs, contadores ou diagnóstico de Health mudam em um histórico ainda encerrado
- **THEN** a assinatura operacional permanece baseada em identidade, configuração, restart, montagens, redes e campos estáveis de execução/encerramento, sem vincular o fingerprint aos registros voláteis de Health; hashes sanitizados por campo permitem conferir a diferença sem expor conteúdo

#### Scenario: Drift em componente operacional de montagem
- **WHEN** a montagem de um container histórico muda entre o preflight e a revalidação após o build
- **THEN** o release informa somente o prefixo do ID e os nomes fixos dos campos divergentes, mantém os hashes operacionais no fingerprint e aborta antes de ativar manutenção ou iniciar DDL

#### Scenario: Diagnóstico de montagem sem revelar paths
- **WHEN** o preflight registra detalhes comparáveis das montagens históricas
- **THEN** informa tipos reconhecidos, acesso somente leitura/escrita e hashes dos componentes Source, Destination, Name, Driver, Mode e Propagation, sem revelar valores ou paths brutos

#### Scenario: Ordem de serialização das montagens históricas
- **WHEN** o daemon retorna os mesmos objetos de montagem em ordem diferente entre inventário e revalidação
- **THEN** a identidade compara uma cópia ordenada deterministicamente por representação canônica do objeto completo, sem depender da ordem do array
- **AND** qualquer alteração, inclusão, ausência ou propriedade diferente em um objeto de montagem continua mudando a identidade e bloqueando o release
- **AND** a ordem da lista utilizada pelos comandos Compose permanece inalterada

#### Scenario: Falha ao buscar candidato antes de DDL
- **WHEN** o `git fetch` do SHA candidato falha durante a construção prévia das imagens
- **THEN** o executor registra somente a subfase e uma categoria fixa (`ref_indisponivel`, `rede_indisponivel`, `acesso_negado`, `transferencia_incompleta` ou `outro`), sem stderr, URL, argumentos, paths, credenciais ou stdout
- **AND** SHALL recuperar os serviços Markina anteriores, confirmar que a migration não começou e manter o release bloqueado até a causa ser corrigida

#### Scenario: Cliente Git rejeita opção metadata-only
- **WHEN** o `git fetch` falha e o stderr privado identifica explicitamente que o cliente Git não reconhece `--no-write-fetch-head`
- **THEN** o executor repete uma única vez o fetch do mesmo SHA integral, sem tags e sem atualizar refs/branches, usando o comportamento padrão de `FETCH_HEAD`
- **AND** registra somente um marcador fixo de compatibilidade, sem expor stderr
- **AND** qualquer falha do retry permanece sanitizada, recupera os serviços anteriores e impede manutenção/DDL

#### Scenario: Comparação de ancestralidade com payload limitado
- **WHEN** o inventário consulta o GitHub Compare para comprovar que o candidato integrado permanece ancestral da main atual
- **THEN** solicita uma página de no máximo um commit e valida `status`, `base_commit.sha` e `merge_base_commit.sha` contra os SHAs esperados
- **AND** uma resposta excessiva, malformada ou divergente continua bloqueando o fingerprint e o release

#### Scenario: Arquivo Compose referenciado está ausente ou inseguro
- **WHEN** um path Compose necessário à operação API/web não pode ser validado
- **THEN** o inventário permanece inapto e informa categorias sanitizadas de todos os paths, consumidores reconhecidos, schema e saúde observados e disponibilidade independente do backup, sem imprimir paths arbitrários, segredos, valores de configuração ou fingerprint de release

### Requirement: Manifesto ativo por serviço no release 0090
O fluxo SHALL validar a ordem de arquivos efetivamente usada por API/web, inclusive manifesto consolidado em deploy-state, e comparar seus hashes Compose com os containers ativos. SHALL usar esses mesmos arquivos nas operações aprovadas. Referências antigas dos demais serviços SHALL permanecer vinculadas ao fingerprint como proveniência, sem serem carregadas pelo release. Os serviços preservados SHALL manter identidade, configuração, estado e proteção contra recriação.

#### Scenario: Nginx preservado referencia override aposentado
- **WHEN** somente Nginx referencia um arquivo RAW removido, enquanto API/web compartilham manifesto consolidado seguro cujos hashes correspondem ao runtime
- **THEN** o fluxo usa somente o manifesto API/web, mantém Nginx preservado e não restaura o override nem inicia serviços aposentados

#### Scenario: Manifesto diverge do runtime
- **WHEN** API/web usam ordens diferentes, um arquivo necessário está ausente/inseguro ou o hash Compose difere do container
- **THEN** nenhuma preparação de backup, parada ou publicação é autorizada

### Requirement: Preparação protegida de backup antes do preflight 0090
O sistema SHALL oferecer operação manual protegida para criar backup online consistente de schema0089, após validar os demais gates sob lock. Esta finalidade SHALL manter backup null no inventário inicial e SHALL NOT autorizar release. A operação SHALL verificar permissões, checksum e listagem pg_restore, revalidar schema e estado e registrar evidência sanitizada. SHALL NOT parar serviços, executar DDL, alterar configuração ou criar journal de release.

#### Scenario: Backup inicial ainda ausente
- **WHEN** CI/SHA/escopo, manifesto, runtime, saúde e schema0089 são válidos e a preparação protegida foi autorizada
- **THEN** o fluxo cria somente dump e manifesto seguros e o preflight normal pode verificar esse backup posteriormente

#### Scenario: Inventário sem backup chega ao release
- **WHEN** o inventário tem backup null ou não verificável
- **THEN** o validador de release recusa antes de qualquer mutação, mesmo que a preparação de backup tenha sido autorizada

#### Scenario: Preparação falha sem diagnóstico operacional suficiente
- **WHEN** a preparação do backup falha
- **THEN** o executor informa a última fase fixa, critérios controlados de recusa e classe/linha local de falhas inesperadas sem expor mensagens brutas, traceback, variáveis, caminhos ou conteúdo privado; a falha continua impedindo release
