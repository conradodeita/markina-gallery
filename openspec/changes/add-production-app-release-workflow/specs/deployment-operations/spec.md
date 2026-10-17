# Spec Delta

## ADDED Requirements

### Requirement: Release de aplicação em produção é separado da manutenção facial
O workflow SHALL oferecer um release protegido e independente para alterações de aplicação que exijam atualizar `api` e/ou `web`. Esse fluxo SHALL NOT usar a autorização de manutenção facial como autorização de aplicação. O gate facial existente SHALL permanecer ativo e independente.

#### Scenario: Alteração comercial de API e web
- **WHEN** uma mudança aprovada altera somente caminhos de aplicação permitidos pelo manifesto de release, sem mudanças em Docker/Compose ou migrations
- **THEN** o fluxo de aplicação pode preparar inventário e release somente de `api` e `web`, enquanto o fluxo facial não é executado para esse escopo

#### Scenario: Escopos misturados ou não permitidos
- **WHEN** a mudança inclui caminhos faciais não autorizados, workers, migration, Docker/Compose, Monitor do sistema ou outro caminho fora do manifesto
- **THEN** o preflight compara o diff desde o checkout ativo de produção e falha fechado antes de qualquer mutação, mesmo quando a mudança facial já está em `main`, exigindo plano OpenSpec/release compatível

### Requirement: Inventário e aprovação do release API/web são vinculados ao SHA
Antes de publicar, o sistema SHALL validar CI verde, SHA completo alcançável em `main`, árvore remota limpa, identidade do projeto, configuração Compose resolvida, estado e saúde dos serviços, versão ativa da API, revisão do banco, portas e domínio. O inventário SHALL ser somente-leitura, minimizar dados e gerar fingerprint que vincula esses fatos ao SHA candidato. A publicação SHALL aguardar aprovação humana protegida específica para o inventário/fingerprint e SHA exatos, e SHALL recalcular o fingerprint imediatamente antes de mutar.

#### Scenario: Inventário corresponde ao alvo
- **WHEN** os pré-requisitos de código, checkout, configuração efetiva, serviços e schema correspondem ao plano
- **THEN** o fluxo apresenta SHA atual e alvo, serviços, portas, domínio, fingerprint, impacto e rollback sem exibir valores secretos

#### Scenario: Repetição manual do preflight de aplicação
- **WHEN** um operador seleciona explicitamente `app-release` em `main` após integração e CI completo
- **THEN** o workflow executa o mesmo classificador, validação de manifesto, inventário somente-leitura e gate de aprovação protegida; a operação manual padrão permanece inerte e não inicia rollback

#### Scenario: Runtime ativo contém mudanças fora do manifesto
- **WHEN** o checkout ativo de produção ao SHA candidato inclui mudanças faciais ou outros caminhos fora do escopo API/web
- **THEN** o inventário falha fechado antes de emitir fingerprint ou solicitar aprovação do release

#### Scenario: Inventário ou estado muda
- **WHEN** o checkout, configuração resolvida, versão da API, revisão do banco, saúde, portas ou domínio divergem entre inventário e aprovação
- **THEN** o release é recusado antes de trocar qualquer container

### Requirement: Release API/web não executa migrations nem altera dependências
Após a aprovação exata, o release SHALL construir e recriar somente `api` e `web` de `markina-gallery`, com `--no-deps`, preservando o schema e os serviços ativos. O fluxo SHALL NOT recriar workers (inclusive workers faciais), banco, Redis ou nginx, nem alterar configuração Compose, arquivos `.env`, redes, volumes ou recursos de terceiros. Caso necessário para resolver upstreams, ele pode testar e recarregar somente o processo do nginx da Markina, sem editar configuração. A alteração do checkout e a criação de imagens anteriores SHALL ser limitadas ao projeto Markina.

#### Scenario: Release sem migration
- **WHEN** os caminhos de migration e Docker/Compose estão vazios e o fingerprint aprovado continua válido
- **THEN** somente `api` e `web` são construídos/recriados e a revisão Alembic permanece idêntica

#### Scenario: Migration ou Compose mudou
- **WHEN** a diferença contém uma migration, arquivo Docker/Compose ou serviço fora do escopo
- **THEN** o fluxo termina antes da build ou de qualquer mutação

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
