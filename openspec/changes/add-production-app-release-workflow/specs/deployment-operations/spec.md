# Spec Delta

## ADDED Requirements

### Requirement: Release de aplicação em produção é separado da manutenção facial
O workflow SHALL oferecer um release protegido e independente para alterações de aplicação que exijam atualizar `api` e/ou `web`. Esse fluxo SHALL NOT usar a autorização de manutenção facial como autorização de aplicação. O gate facial existente SHALL permanecer ativo e independente.

#### Scenario: Alteração comercial de API e web
- **WHEN** uma mudança aprovada altera somente caminhos de aplicação permitidos pelo manifesto de release, sem mudanças em Docker/Compose ou migrations
- **THEN** o fluxo de aplicação pode preparar inventário e release somente de `api` e `web`, enquanto o fluxo facial não é executado para esse escopo

#### Scenario: Escopos misturados ou não permitidos
- **WHEN** a mudança inclui caminhos faciais não autorizados, iniciação ou alteração de serviço de worker, migration, Docker/Compose, Monitor do sistema ou outro caminho fora do manifesto
- **THEN** o preflight compara o diff desde o checkout ativo de produção e falha fechado antes de qualquer mutação, mesmo quando a mudança facial já está em `main`, exigindo plano OpenSpec/release compatível

### Requirement: Publicação do runtime de backup permanece inerte
O release API/web MAY incluir módulos da rotina de backup global somente quando cada blob estiver fixado no manifesto do candidato e o diff não incluir migrations, alteração de Docker/Compose ou configuração de instalação do serviço. O release SHALL NOT instalar, habilitar ou iniciar o serviço/timer de backup nem iniciar cópia real.

#### Scenario: Código de backup incluído sem ativação
- **WHEN** o candidato contém módulos de backup exatos e aprovados no manifesto, sem mudança de schema ou infraestrutura
- **THEN** o fluxo pode publicar somente `api` e `web`; o serviço e o timer de backup permanecem ausentes ou inativos, sem cópia real

#### Scenario: Arquivo ou blob de backup não revisado
- **WHEN** o candidato inclui módulo, worker, unidade, timer ou lock de dependências fora dos pins e caminhos exatos aprovados
- **THEN** o preflight MUST falhar antes de build, recriação ou outra mutação

### Requirement: Inventário e aprovação do release API/web são vinculados ao SHA
O inventário SHALL validar CI verde, SHA completo alcançável em `main`, checkout limpo, identidade do projeto, Compose resolvido, saúde dos serviços, versão da API, schema, portas e domínio. SHALL ser somente-leitura e gerar fingerprint minimizado vinculado ao SHA. A publicação SHALL aguardar aprovação humana protegida para o SHA/fingerprint exatos e recalcular o fingerprint antes de mutar.

#### Scenario: Inventário corresponde ao alvo
- **WHEN** os pré-requisitos de código, checkout, configuração efetiva, serviços e schema correspondem ao plano
- **THEN** o fluxo apresenta SHA atual e alvo, serviços, portas, domínio, fingerprint, impacto e rollback sem exibir valores secretos

#### Scenario: Inventário ou estado muda
- **WHEN** o checkout, configuração resolvida, versão da API, revisão do banco, saúde, portas ou domínio divergem entre inventário e aprovação
- **THEN** o release é recusado antes de trocar qualquer container

### Requirement: Destino SSH de release permanece vinculado ao preflight
O preflight SHALL registrar um digest não sensível do host, porta e usuário SSH efetivamente usados. A publicação SHALL comparar o destino SSH do environment `production` com esse digest e falhar antes do upload se houver divergência.

#### Scenario: Destino SSH diverge do preflight
- **WHEN** host, porta ou usuário do environment `production` diferem do destino registrado pelo preflight do mesmo run
- **THEN** o release MUST falhar antes de transferir o bundle ou iniciar a conexão de deploy, sem imprimir valores secretos

### Requirement: Preflight exporta imagem-base e CI produz bundle ARM64
O preflight SHALL permanecer somente-leitura e exportar por stdout somente o ID da imagem API ativa identificado no inventário; SHALL NOT ler volumes, variáveis ou dados do container. A CI SHALL construir a API ARM64 sobre esse ID-base e copiar exclusivamente `backend/app`, preservando runtime facial e dependências instaladas. A CI SHALL construir web pelo Dockerfile aprovado e vincular ao bundle o SHA de origem, plataforma e IDs imutáveis.

#### Scenario: Imagem-base corresponde ao inventário
- **WHEN** o preflight recebe um SHA aprovado e encontra a imagem API ativa registrada no inventário
- **THEN** ele exporta somente essa imagem por stdout, sem ler dados do container ou escrever no host

#### Scenario: Bundle ARM64 do SHA candidato
- **WHEN** o job de artefato roda em runner ARM64 com a imagem-base e o SHA do mesmo run
- **THEN** a CI constrói API/web, valida plataforma e IDs e cria o bundle vinculado a esse SHA

### Requirement: Release valida e consome bundle imutável API/web
Após os gates completos do mesmo run/SHA e aprovação `production`, o release SHALL validar digest, manifesto, IDs, ID-base, arquitetura e SHA de origem antes de carregar imagens. SHALL recriar somente `api` e `web` do projeto `markina-gallery` com `--no-build --no-deps`, sem migrations ou mudança de schema.

#### Scenario: Release sem migration
- **WHEN** os caminhos de migration e Docker/Compose estão vazios, o fingerprint aprovado continua válido, o bundle CI corresponde ao mesmo SHA/run e seu ID-base API ainda está ativo
- **THEN** somente `api` e `web` são carregadas/recriadas com seus IDs imutáveis e a revisão Alembic permanece idêntica

#### Scenario: Migration ou Compose mudou
- **WHEN** a diferença contém uma migration, arquivo Docker/Compose ou serviço fora do escopo
- **THEN** o fluxo termina antes da build ou de qualquer mutação

#### Scenario: Bundle diverge do inventário
- **WHEN** o hash, manifesto, arquitetura, SHA ou ID-base API do bundle diverge
- **THEN** a publicação falha sem carregar/recriar serviço e preserva os IDs de rollback

### Requirement: Release limita mudanças aos serviços e ativos Markina
O release SHALL NOT executar `compose build` no host, recriar workers, banco, Redis ou containers nginx, nem alterar Compose, `.env`, redes, volumes ou recursos de terceiros. Pode recarregar somente o processo nginx da Markina sem editar configuração. Checkout e imagens de recuperação ficam limitados ao projeto Markina.

#### Scenario: Somente API e web são recriados
- **WHEN** um release autorizado consome o bundle candidato
- **THEN** somente os containers `api` e `web` são recriados e os demais ativos e projetos permanecem intactos

#### Scenario: Caminho de build no host
- **WHEN** o release comum tenta executar `compose build` no host
- **THEN** o contrato do release recusa a operação e exige o bundle CI aprovado

### Requirement: Transferência do bundle usa chave SSH restrita
Após a aprovação `production`, a transferência SHALL usar chave SSH separada com forced command para wrapper root-owned dedicado. O wrapper SHALL aceitar somente SHA e digest completos, limitar o tamanho, validar o hash e gravar atomicamente em destino fixo; SHALL NOT extrair nem executar o payload. A chave do preflight permanece sem capacidade de escrita.

#### Scenario: Upload autorizado do bundle
- **WHEN** a aprovação `production` foi concedida e o cliente envia SHA, digest e payload válidos pela chave de upload restrita
- **THEN** o wrapper valida o hash e grava o bundle atomicamente no destino temporário fixo

#### Scenario: Comando ou payload de upload inválido
- **WHEN** a chave, comando, SHA, digest ou tamanho não corresponde ao contrato restrito
- **THEN** a transferência falha sem extrair ou executar o payload

### Requirement: Release verifica saúde e rollback de API/web
Após a troca, o sistema SHALL validar saúde de `api` e `web`, endpoints locais/públicos necessários e configuração efetiva dos serviços; SHALL registrar SHA anterior/alvo e imagens preservadas. Diante de falha, SHALL manter o erro visível, não declarar sucesso e disponibilizar inventário de rollback que também aguarda aprovação humana antes de restaurar somente `api` e `web`.

#### Scenario: Release saudável
- **WHEN** os dois serviços ficam saudáveis, os hashes resolvidos correspondem e os endpoints públicos respondem
- **THEN** o release registra SHA publicado, SHA anterior e estado saudável

#### Scenario: Smoke ou healthcheck falha
- **WHEN** um serviço ou endpoint não recupera saúde dentro do limite definido
- **THEN** o fluxo falha, mantém o histórico e as imagens de recuperação e não executa rollback automático

#### Scenario: Rollback autorizado
- **WHEN** o operador apresenta novo inventário e o proprietário aprova o SHA anterior e fingerprint de rollback
- **THEN** somente `api` e `web` são restaurados e novamente validados
