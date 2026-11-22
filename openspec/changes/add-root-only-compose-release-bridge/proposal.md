# Proposal

## Why

O inventário API/web usa um conjunto canônico de arquivos Compose, mas os containers ativos foram criados por snapshots protegidos, gerados pelos fluxos faciais e de preview. O helper não reconhece esses serviços e bloqueia o release; expor os snapshots à conta SSH comum ou ignorar a divergência destruiria a garantia de proveniência e o rollback.

## What Changes

- Aprovação adicional: inventariar privadamente os 12 históricos API/web já parados como testemunhas por ID/nome/imagem/configuração, vinculados ao fingerprint. Não selecionar, iniciar, renomear ou remover testemunhas; não ignorar parados genericamente. Alteração de identidade/estado bloqueia o gate.

- Refinamento aprovado após ensaio: cada nova tentativa usa projeto Compose derivado internamente por geração e nomes operacionais fixos dos containers. Validar labels nativos esperados por geração e IDs registrados; redes/volumes continuam externos e existentes. Isso impede que o Compose remova um candidato retido de outra geração. Não acrescentar ambiente/servidor nem aceitar projetos arbitrários.

- Revisão do plano aprovada em 19/11/2026 após falha da primeira troca: distinguir adoção da configuração de transferência do controle operacional ao Compose. Preparar transição explícita por IDs, sob lock e novo fingerprint, parando/renomeando somente API/web comprovados para nomes fixos de recuperação e preservando os containers anteriores. Aprovação documental não executa nem autoriza uma nova operação de produção.
- Cobrir interrupções em cada fronteira, inclusive serviço ausente após stop/rename, seleção inequívoca entre ativos e retidos e recuperação explicitamente inventariada/aprovada. Não fabricar config-hash, remover containers antigos ou apagar marcadores para contornar o bloqueio. Resolver configuração e executar dry-run não bastam para declarar a primeira troca validada.

- Decisão do proprietário em 19/11/2026: preparar adoção explícita do runtime saudável como nova base privada quando os labels apontarem para snapshots históricos divergentes. Essa decisão aprova o planejamento; não autoriza automaticamente instalação, captura persistente de credenciais ou deploy. O inventário normal continua falhando fechado até existir base adotada, comprovada e aprovada por operação protegida.
- Separar diagnóstico read-only, prova de reprodução do modelo ativo e adoção persistente protegida. Vincular a base aos IDs exatos de containers/imagens, configuração efetiva, fontes históricas e aprovação; preservar snapshots e valores TOTP existentes, sem editar `.env` ou recriar containers para corrigir labels.

- Criar uma ponte operacional root-only, com interface fixa e comandos allowlistados para inventário, release e rollback somente de `api` e `web`.
- Validar os arquivos Compose pelos labels dos containers, limitar caminhos às raízes persistentes aprovadas, verificar tipo, symlink, proprietário/modo e hashes, e manter o conteúdo fora de logs e artefatos do GitHub.
- Fazer o preflight read-only usar a ponte exclusivamente para produzir inventário minimizado e fingerprint; permitir mutação somente pelo workflow protegido `production` após correspondência do fingerprint.
- Validar a origem Git por allowlist exata em HTTPS, URI SSH ou formato SCP do OpenSSH, somente para o host e repositório autorizados, sem reescrever `origin`.
- Preservar os snapshots originais e as imagens antes do release, e exigir novo inventário e aprovação próprios para rollback.
- Manter schema, `.env`, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, workers, banco, Redis, nginx, backup, dados e recursos de outros projetos fora do escopo.

## Capabilities

### New Capabilities

- `deployment-operations/root-only-app-compose-bridge`: acesso privilegiado restrito para inventariar e publicar/recuperar API/web quando a configuração ativa vem de snapshots Compose protegidos.

### Modified Capabilities

Nenhuma. O contrato geral do release API/web continua sendo o da change `add-production-app-release-workflow`; esta change adiciona a fronteira privilegiada necessária para atender a configuração existente.

## Impact

Afeta o helper de release API/web, o wrapper SSH de preflight, o workflow CI, os instaladores root-owned, testes de contrato/segurança e o runbook. A instalação e o primeiro uso no host ocorrerão somente depois de CI/PR verdes e por workflow protegido; nenhuma configuração de produção será lida ou alterada por esta proposta.

O diagnóstico read-only de 19/11 confirmou que os labels apontam para snapshots anteriores ao runtime `bfe511f`: API difere em ambiente, usuário, labels e mounts; web difere em ambiente, comando, entrypoint, usuário e labels. As imagens referidas pelas fontes não são as ativas. Naquele diagnóstico inicial, o comparador recusava `tmpfs` da API e havia `CgroupnsMode` não padrão em ambos; a tradução e a adoção posteriores estão evidenciadas em validation.md. A primeira troca de containers permanece pendente da revisão descrita acima. Os valores de segredos não foram exibidos. A adoção não declara esses snapshots equivalentes: registra uma nova origem explicitamente aprovada e exige prova independente de que seu modelo reproduz o runtime.


A tentativa autorizada no SHA 850fce24 preservou as fontes, imagens e todos os containers, mas falhou na primeira recriação. A reprodução sintética com Compose 5.6.1 demonstrou conflito de nome quando o container existente não possui config-hash. O stderr original foi suprimido: essa reprodução e a fase/estado observados sustentam a revisão, sem afirmar recuperação do erro textual original. A nova cobertura SHALL executar a troca real no laboratório e validar preservação/recuperação, não somente o modelo resolvido.
