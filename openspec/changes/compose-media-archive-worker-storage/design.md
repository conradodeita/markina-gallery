# Design

## Context

Ver [proposal.md](proposal.md) para a motivação e [specs/media-storage/spec.md](specs/media-storage/spec.md) para os requisitos observáveis. Em `backend/app/worker.py`, `configure_media_archive_storage` injeta um único objeto e o dispatcher valida gate e staging antes de descobrir/reivindicar trabalho; essa injeção não declara o tenant do objeto. `backend/app/media_archive_worker.py::claim_next_operation` seleciona globalmente operações de qualquer tenant ativo e mantém um único coordenador/lease. `GoogleDriveMediaArchiveStorage` recebe token, raiz e tenant fixos por construtor.

O design da change `add-gallery-media-archive` mantém o adapter Google fora do runtime e exige composição explícita, gate inativo por padrão, staging válido e seleção de tenant antes de qualquer chamada de transporte. O runbook de reaproveitamento separa a identidade de mídia do backup global e orienta preservar a fila/coordenador, leases, estados incertos e reconciliação. A task operacional 1.4 continua aberta; o backup global ainda é pré-requisito. `My Drive/Oracle Production Ensaios` permanece indicada exclusivamente para fixtures sintéticas e não é raiz operacional de mídia.

## Goals / Non-Goals

**Goals:**

- Criar uma fronteira explícita de composição e identidade de tenant antes da descoberta e do claim.
- Permitir apenas o tenant do proprietário no primeiro piloto, sem reivindicar nem despachar jobs de outros tenants.
- Preservar o coordenador global, a exclusividade do lease, os contratos do executor e a compatibilidade do backup Workspace.
- Demonstrar o fluxo local com storage/transporte sintéticos e comprovar ausência de chamadas externas em configuração fechada ou inválida.
- Manter o worker inativo por padrão e deixar a task 1.4 como gate operacional independente.

**Non-Goals:**

- Selecionar, provisionar ou usar credencial/raiz real, medir quota, fazer upload/readback/restore real ou habilitar tenants.
- Ligar automaticamente o adapter Drive por `APP_ENV`, Compose, scheduler ou descoberta de credenciais.
- Alterar o fluxo global de backup, OAuth/Picker, runtime publicado, banco, migrations, workflows ou configuração de host.
- Definir a arquitetura de roteamento de storage para todos os tenants após o piloto.

## Decisions

### Contrato proposto: vínculo explícito anterior ao claim

1. A inicialização fornece um vínculo de storage explícito para um tenant autorizado. Antes de descoberta ou claim, a composição confere que o tenant selecionado coincide com a identidade de tenant declarada pelo vínculo, que a raiz/namespace pertencem ao contexto de mídia e que a configuração está completa. A verificação local de formato não substitui a prova operacional de autorização do Drive.
2. O piloto usa uma allowlist de um único tenant do proprietário. A restrição vale para jobs em fila e para retomadas de lease. Um lease global pertencente a outro tenant não é retomado, liberado nem transferido; a operação permanece preservada e bloqueia novo claim até o fluxo autorizado resolvê-la.
3. O coordenador global continua serializando no máximo um lease. O filtro do piloto altera apenas quais operações esse dispatcher pode reivindicar; FIFO e prioridade existentes permanecem dentro do conjunto permitido. Outros tenants continuam sem execução pelo piloto.
4. O gate `MEDIA_ARCHIVE_WORKER_ENABLED` continua `false` por padrão. Apenas `true` não configura adapter. Gate fechado, vínculo incompleto/divergente, staging inválido ou falta da prova operacional impedem descoberta, claim e transporte. `APP_ENV=production` é somente uma guarda técnica do adapter, não aprovação ou autorização.
5. Fixtures usam tenant/galeria/pasta/ciclo sintéticos e transporte falso. Casos recusados verificam zero chamadas ao transporte; o caso positivo prova o dispatcher, upload/readback/restauração e isolamento sem rede. A pasta remota de ensaio, se usada numa fase autorizada futura, não participa desses testes locais.

### Identidade dedicada e injeção sintética

A decisão aprovada em `add-gallery-media-archive/design.md:130,155` exige identidade Workspace dedicada distinta da conta/credencial do backup e raiz própria de mídia. Não há alternativa de compartilhar a identidade do backup. Provisão, custódia, rotação, consentimento OAuth, permissões e quota reais continuam no gate operacional 1.4.

Nesta implementação local, o chamador fornece um binding sintético explícito com tenant selecionado, tenant declarado pelo adapter, raiz sintética, namespace e propósito de mídia. O binding não carrega tokens nem constrói o adapter Google e não habilita operação real. A factory do backup permanece excluída.

### Claim filtrado por tenant

Mapa de chamadas no SHA base: `worker.py::process_next_media_archive_operation` é o único consumidor de aplicação de `media_archive_worker.claim_next_operation`. Os demais consumidores estão em testes. `worker.py::process_next_gallery_lifecycle_operation` usa o homônimo importado de `gallery_lifecycle`, independente.

Escolha: filtro opcional UUID por tenant no claim de mídia, preservando callers existentes sem filtro. O filtro restringe fila e retomada; lease global fora do tenant é preservado e bloqueia claim. Não alterar prioridade/FIFO, coordenador, exclusividade ou contrato do lifecycle. A descoberta do piloto recebe o mesmo filtro para não criar ciclos/avisos de terceiros.

### Rollout, gates e compatibilidade

- A entrega desta change deve primeiro ser aprovada como arquitetura e validada localmente com fixtures. Nenhum commit, publicação, configuração de host ou ativação decorre deste rascunho.
- Após implementação e revisão, o gate operacional da task 1.4 continua exigindo release/ambiente autorizado, backup global comprovado, vínculo OAuth do app com a pasta adequada, identidade/root/permissões/limites verificados e ensaio sintético do proprietário. A pasta `Oracle Production Ensaios` está limitada a ensaios sintéticos; root operacional de mídia para dados reais permanece não selecionado.
- Rollback de código deve manter o worker desligado e remover somente a injeção explícita aprovada pelo fluxo de release. Não executar rollback remoto nesta change.
- `WorkspaceDriveBackupStore`, suas credenciais, seu runtime e seus testes permanecem inalterados; validar seus consumidores de forma read-only/compatível na fase de implementação.

## Risks / Trade-offs

- **Um lease de outro tenant pode bloquear o piloto:** preservar a exclusividade global evita concorrência e reatribuição incorreta; preflight deve detectar e parar sem mutação.
- **Um token OAuth disponível pode não autorizar a pasta:** não inferir acesso a partir do conector, da UI ou de configuração do backup; somente o gate operacional aprovado pode comprovar identidade, raiz, escopo e capacidade.
- **Uma configuração incompleta pode reivindicar trabalho antes de falhar:** validar vínculo e staging antes da descoberta/claim, e testar que a fronteira falha sem efeitos.
- **Uma futura ampliação multi-tenant pode exigir roteamento diferente:** manter esse piloto fixo e não inferir modelo futuro a partir de uma factory singleton.
- **`APP_ENV=production` pode ser confundido com aprovação:** documentar e testar que essa variável não cria binding nem abre o gate desabilitado.

## Migration Plan

Não há migration de dados nem alteração de runtime neste rascunho. Após decisão arquitetural, a implementação local deve preservar o estado atual inativo, validar contratos sintéticos e submeter um diff próprio à revisão antes de publicação. A retomada da task operacional 1.4 permanece posterior e depende dos gates existentes; nenhuma raiz ou credencial será provisionada por esta change.

## Open Questions

- Antes de liberar qualquer tenant além do proprietário, decidir e especificar o modelo multi-tenant (resolver por tenant ou workers/claims particionados), incluindo concorrência com o coordenador global. Essa decisão pode aguardar o resultado do piloto; não pode ser inferida nem ativada nesta change.

## Evidência local — 24/11/2026

A composição sintética usa `SyntheticMediaArchiveBinding` em `worker.py`, com tenant selecionado e tenant declarado pelo chamador, root `synthetic:` e namespace/finalidade explícitos. Esse binding é uma declaração para fixtures locais, não prova de identidade OAuth do app ou autenticação do proprietário. A injeção direta local de storage e callers de claim sem filtro mantêm compatibilidade; nenhum factory real foi conectado. O chamador do futuro piloto operacional exigirá uma fronteira própria comprovada no gate 1.4.

O claim e as duas descobertas recebem filtro UUID opcional. O filtro ocorre na consulta antes do limite, evitando starvation pelo lote de terceiros; o claim recusa retomar lease global fora do tenant antes de qualquer transição. Sem filtro, os consumidores existentes mantêm sua semântica.

## Fronteira corrigida: composição sintética somente no harness

O storage em memória não é durável: permitir sua seleção no loop poderia satisfazer readback e fazer o executor remover a origem local. Por isso `configure_media_archive_storage` recusa toda tentativa; não armazena binding. O dispatcher sem argumento retorna antes de acessar staging/banco/claim/cleanup, ignorando o slot legado mesmo que indevidamente preenchido. Não há vínculo operacional implementado ou ativável por esta change.

`SyntheticMediaArchiveBinding` e o tipo concreto `SyntheticMediaArchiveStorage` são utilizados apenas em chamadas diretas de harness local. Em `APP_ENV=production`, inclusive chamadas diretas são recusadas antes de consultar banco ou executar o storage/executor. O harness positivo injeta SessionLocal SQLite em memória e raízes temporárias por teste; upload/readback, recuperação e cleanup operam somente nessas fixtures descartáveis. A injeção direta de callers sintéticos locais permanece compatível.

UUIDs e raiz `synthetic:` são apenas metadados de fixture, sem prova de proprietário, identidade OAuth, autorização ou durabilidade. O gate 1.4 e uma fronteira operacional durável própria continuam pré-requisitos para qualquer futura ativação. Regressões de development/production provam recusa do registro, loop fechado mesmo com global indevidamente preenchido, zero banco/cleanup e preservação dos bytes locais.
