# Design: Restauração do runtime facial

> **Decisão substitutiva expressa do proprietário — 02/11/2026:** reativar a busca para todos independentemente de calibração; a nova pasta de ensaio fica restrita ao cliente de teste do proprietário. Esta decisão substitui a escolha anterior de exigir medição antes da ativação. O modo operacional `owner-authorized-general-restore-v1` restaura a compatibilidade das políticas ativas com `FACIAL_REQUIRE_EXPLICIT_ROLLOUT=false` e `FACIAL_REQUIRE_PRODUCTION_CALIBRATION=false`, sem criar aprovação de calibração. O padrão de código permanece exigindo calibração. A autorização e o modo são vinculados ao manifesto/recibo; só `stage=general` pode usá-los. Os demais trechos que exigem rollout estrito e calibração descrevem o modo `strict` e continuam válidos nele. OTP, vínculo, tenant ativo, política/versões, consentimento, modelos, limiares, retenção e gates comerciais permanecem obrigatórios. Medição pendente SHALL ser registrada como pendente, nunca aprovada por inferência.

## Context

Ver `proposal.md` e a evidência sanitizada em `investigation.md`. A indisponibilidade começou no corte ambiental autorizado de 30/10. O estado ativo combina uma API com patch pontual saudável e workers anteriores compatíveis com schema `0090`; as imagens não devem ser substituídas pela worktree SaaS, cujo desenvolvimento contém migrations posteriores não publicadas.

A configuração habilitada foi validada somente em um subprocesso, sem modificar containers: ambiente, chave de 32 bytes e versões obrigatórias passaram sem checar assets; a validação completa recusou o cache inexistente. A API também não tem OpenCV/NumPy. O marcador dos modelos existe na imagem parada de busca, mas os bytes dos pesos ainda não foram verificados nesta investigação.

O código real `rollout_is_active` exige calibração aprovada em produção e permite o fallback legado quando não existe rollout em nenhum ambiente. Portanto, zero rollouts não prova uma allowlist vazia: depois de uma aprovação de calibração, a flag poderia alcançar galerias além do escopo inicial.

## Goals / Non-Goals

**Goals:**

- Restaurar o recurso no contexto atual com identificação de dependências, versões e imagens, sem regressão dos contratos já ativos.
- Tornar o candidato, o escopo e a recuperação verificáveis antes da etapa mutável.
- Usar um modo explícito de rollout para a restauração gradual, com negação padrão fora do escopo aprovado.
- Manter evidências e pendências no repositório para outro executor continuar.

**Non-Goals:**

- Publicar o SaaS, trocar modelos/limiares, reindexar todo o acervo ou rotacionar chaves por causa de seus nomes.
- Declarar aprovação jurídica, calibração representativa ou capacidade com base em ordem de ativação, healthcheck ou inventário de RAM.
- Voltar para `staging`, iniciar os containers parados com sua configuração antiga, aplicar migrations ou usar scripts antigos com seus schemas fixos alterados à mão.

## Decisions

### 1. Empacotar sobre os baselines observados

O pacote operacional partirá de base Git limpa correspondente à `main` revisada, mas cada imagem preservará o código/dependências da sua versão saudável por digest. A API usa `sha256:0d14e294a7581f0f863e19a030f158ef2b59c6e409cf0c4a763124906459ef6f`; o worker geral usa `sha256:06e3c1127212fab1629157f7e9c90f801d88e8a949b67795c8d22186a105e815`.

Antes de construir, inventariar Python, SO, arquitetura, pacotes e hashes dos módulos afetados em cada baseline. Acrescentar somente dependências faciais já revisadas e fixadas para ARM64, assets comprovados e o delta mínimo de admissão descrito abaixo. Não copiar arbitrariamente bibliotecas compiladas entre imagens. A comparação de módulos deve provar preservação do patch Overview e de todos os módulos fora da allowlist; `APP_VERSION` isolado não é essa prova.

Alternativa recusada: rebuild geral da worktree local ou troca da API pela imagem facial antiga. Ambos poderiam remover correções atuais ou incluir mudanças SaaS não publicadas.

Preparar um candidato separado para cada serviço consumidor, sempre sobre seu próprio digest baseline; o candidato do worker geral não substitui os três workers faciais. Se o baseline da API ou do worker geral não contiver o manifesto facial, o candidato pode acrescentar somente o manifesto de SHA fixado com os pesos já verificados. Workers faciais que já contêm o manifesto devem preservá-lo sem alteração; dependências faciais já presentes nesses baselines não devem ser reinstaladas.

### 2. Reutilizar pesos somente depois de provar sua integridade

Os pesos preservados são candidatos: YuNet `2023mar` e SFace `2021dec`. Conferir tamanho, SHA-256 e marcador contra o manifesto da API e contra o manifesto da imagem doadora antes de incluir bytes no candidato. A preparação não pode fazer download implícito nem considerar só a presença do marcador como verificação dos pesos.

O nome da chave ativa contém `homolog`, porém a chave está presente e o contexto de credencial é `production`; isso não prova origem, rotação ou adequação jurídica, mas também não autoriza uma troca. Validar cofre/contexto e preservar o chaveiro de destino autenticado do corte anterior. Nenhum valor de chave entra no relatório.

### 3. Acrescentar admissão estrita somente para o rollout revisado

Proposta de configuração técnica: um modo explícito de exigência de rollout, desabilitado por padrão para manter compatibilidade fora desta operação, habilitado em todos os consumidores participantes da restauração. Nesse modo, ausência de rollout ativo no ambiente corrente recusa indexação e busca, inclusive em galerias novas. Os gates existentes de calibração, autorização e versões continuam obrigatórios.

Testes devem provar que o modo legado preserva seu comportamento anterior e que o modo estrito não permite fallback nem alias de `staging` para `production`. A operação prepara rollouts `dark` e ativa somente a allowlist aprovada, sem suspender galerias para conseguir bloqueio: suspensão/revogação no código vigente agenda purge de índices. Qualquer mudança desse desenho exige revisão dos artefatos antes do código.

### 4. Separar preparação, exposição e promoção

O operador terá fases explícitas de inventário, preparação isolada, aplicação `dark`, ativação, verificação e recuperação. A aplicação `dark` é uma fase operacional com a flag falsa, sem claim de galerias reais; não exige executar workers incompatíveis com o estado desligado. Imagens são verificadas antes da troca, e workers começam a processar somente após os gates e o escopo estarem registrados.

API, worker geral e três workers faciais devem concordar em ambiente, configuração, modelos e modo de admissão. Reusar manifests efetivos sob controle protegido, comparando fontes/destinos/permissões de mounts e hashes por serviço. Não recalcular tudo a partir do Compose local ignorando patches e overlays ativos. A pausa é curta e delimitada aos consumidores aprovados; não há promessa de interrupção zero para esses consumidores.

Na comparação de `HostConfig.Dns`, `[]` e `null` representam a ausência de servidores DNS explícitos e SHALL ser normalizados para o mesmo valor. Qualquer lista não vazia permanece estrita; nenhuma outra divergência de configuração pode ser normalizada por conveniência.

#### Separação do estado operacional compartilhado

O adaptador real SHALL executar com UID/GID root, pois precisa ler o manifesto root-only e arquivos Compose protegidos. Execução com outra identidade MUST falhar antes de acessar Docker ou alterar estado. O diretório fixo `/var/lib/markina-gallery/deploy-state` é compartilhado por fluxos de release e pertence a `ubuntu:ubuntu`, modo `0700`. O operador facial SHALL validá-lo nesse proprietário e modo, sem exigir que o diretório pertença ao UID efetivo do operador. MUST NOT alterar proprietário, modo ou conteúdo preexistente do diretório compartilhado.

O lock global `/var/lib/markina-gallery/deploy-state/production-release.lock` permanece no local usado pelos demais releases. O operador SHALL abrir e bloquear esse arquivo sem truncá-lo, validando arquivo regular, único hard link, proprietário/grupo `ubuntu:ubuntu` e modo `0600`; SHALL NOT substituí-lo, recriá-lo, alterar dono ou modo. Os marcadores conhecidos na lista fixa `PENDING` SHALL continuar sendo verificados diretamente no diretório compartilhado. A conversão de `OSError` para erro de lock SHALL cobrir somente aquisição e validação do lock; falhas lançadas pelo corpo protegido SHALL manter seu diagnóstico próprio.

Diários, recibos e snapshots cifrados da restauração facial SHALL ficar somente em `/var/lib/markina-gallery/deploy-state/facial-runtime-restoration`, diretório filho fixo `root:root 0700`. `inventory` não o cria. `prepare` pode criá-lo uma única vez com `mkdir` sem recursão e confirmar dono, grupo, modo e ausência de symlink; estado existente incompatível MUST interromper a operação sem reparo automático. Diários faciais legados no pai compartilhado também SHALL ser verificados para impedir concorrência durante a transição.

O manifesto fixo `/var/lib/markina-gallery/deploy-state/facial-runtime-candidates.json` continua no diretório compartilhado, com arquivo regular, proprietário root, modo `0600` e caminho não configurável pela CLI. Sua leitura valida separadamente o diretório pai de `ubuntu:ubuntu 0700` e o arquivo de root. Arquivos Compose protegidos podem continuar nesse diretório compartilhado; o inventário SHALL aceitar apenas arquivos regulares, protegidos contra gravação por grupo/outros, sob as raízes fixas de código ou de estado compartilhado.

#### Proveniência do suporte e dos candidatos

O manifesto e o checkout de suporte existentes estão vinculados ao SHA `775f84e83a64bb5a0e60581f3b386ddb5f0fc7de`. Depois do merge do operador revisado, o suporte SHALL ser disponibilizado em um novo checkout Git detached, limpo e root-only `facial-runtime-support-<12 caracteres do SHA do merge>`, sem substituir o checkout anterior nem atualizar a árvore de aplicação `/opt/markina-gallery`. O checkout SHALL apontar exatamente para o SHA de `main` revisado, e o operador SHALL verificar esse SHA e o estado Git limpo antes de ler o manifesto.

O manifesto existente SHALL permanecer no lugar; antes de `prepare`, sob o lock global, uma atualização controlada pode alterar somente o campo `support_sha` do SHA antigo para o SHA do merge. A gravação SHALL ser atômica, preservar owner/group root e modo `0600`, e conferir que todos os demais valores JSON permaneceram idênticos. Registrar SHA-256 antigo e novo do arquivo. Depois, `prove_images`/`validate_images` SHALL comprovar os cinco candidatos contra o novo checkout; qualquer diferença de módulo, dependência, imagem ou outro campo mantém a operação bloqueada. O manifesto não será regenerado a partir de ambiente local nem seus candidatos reconstruídos por causa apenas da troca de suporte.

Para os cinco consumidores, `prepare` SHALL habilitar `--profile facial` tanto ao resolver o modelo Compose quanto ao calcular `config --hash`; perfil precisa estar ativo também para workers faciais perfilados. Cada hash observado SHALL corresponder ao label do container inventariado. A validação dos modelos e hashes SHALL terminar antes de reservar o diretório privado da operação; uma falha de Compose deixa o diretório da operação ausente e não altera containers.

#### Protocolo de parada cooperativa e CLI

Não exigir um arquivo ACK em `/run`: nenhum processo atual o escreve e um arquivo antigo não provaria que o processo está ocioso agora. O recibo cooperativo será produzido pelo próprio host ao observar o encerramento do container exato que inventariou. Antes do primeiro sinal, o operador SHALL conferir ID, imagem, comando, ambiente/configuração, horário de início e `docker diff` de todos os consumidores. Para cada processo em execução, SHALL registrar a intenção no journal, desativar temporariamente sua política de reinício, enviar somente `SIGTERM` e aguardar no máximo 120 segundos. Uvicorn conclui requisições em andamento; o worker geral usa o encerramento gracioso já existente; cada worker facial SHALL instalar handlers que apenas solicitem parada e sair depois do ciclo atual, sem iniciar outro ciclo. O recibo SHALL vincular operação, serviço, ID, imagem, digest da configuração, início, código de saída zero e fase do journal.

O operador SHALL revalidar o mesmo ID e código de saída zero e consultar `docker diff` após a parada. Se o sinal falhar, exceder o prazo, o processo sair com erro, a identidade mudar ou a camada gravável deixar de estar vazia, SHALL abortar antes da primeira troca, restaurar a política de reinício e iniciar o mesmo container original que foi parado. MUST NOT enviar `SIGKILL` automaticamente. Essa retomada não recria o container nem altera banco, mounts ou filas.

Os candidatos SHALL usar root filesystem somente leitura, `PYTHONDONTWRITEBYTECODE=1` e apenas `/tmp` e `/run` como `tmpfs` temporários com limites explícitos. Dados duráveis continuam nos mounts existentes. A recuperação SHALL confirmar `ReadonlyRootfs`, mounts idênticos e `docker diff` vazio antes de remover/recriar qualquer candidato; uma divergência interrompe a remoção e preserva o container para revisão manual. `docker compose` SHALL continuar sem `--volumes`/`-V`.

A CLI SHALL oferecer somente inventário, preparação e fases fixas (`dark`, `activate`, `verify`, `recover`), usando o projeto, host, diretórios e serviços constantes do operador. Não aceitar host, projeto, serviço, comando Docker ou caminho de estado arbitrário. Preparação e cada fase que grava SHALL exigir confirmação interativa que vincule operação e fase; fingerprints, allowlist e stage são argumentos tipados, validados e limitados. A saída SHALL conter somente status, operação e fingerprint, sem ambiente, config cifrada, credenciais, SQL ou dados pessoais. Esta interface prepara uma operação futura e não autoriza nem executa produção nesta mudança local.

Comandos de referência no host fixo do operador (não executados nesta revisão):

```text
python3 scripts/facial_runtime_restoration_cli.py inventory --support-sha <sha40>
python3 scripts/facial_runtime_restoration_cli.py prepare --support-sha <sha40> --operation <id>
python3 scripts/facial_runtime_restoration_cli.py execute --support-sha <sha40> --operation <id> --phase dark --fingerprint <sha256>
python3 scripts/facial_runtime_restoration_cli.py execute --support-sha <sha40> --operation <id> --phase activate --fingerprint <sha256> --allowlist <gallery-uuid> --stage canary
python3 scripts/facial_runtime_restoration_cli.py execute --support-sha <sha40> --operation <id> --phase verify --fingerprint <sha256> --allowlist <gallery-uuid> --stage canary
python3 scripts/facial_runtime_restoration_cli.py execute --support-sha <sha40> --operation <id> --phase recover --fingerprint <sha256>
```

`prepare` lê somente `facial-runtime-candidates.json` protegido em `/var/lib/markina-gallery/deploy-state/`, sob as regras de proprietário/modo descritas acima; não recebe caminho por argumento. Antes de cada gravação, a CLI pede a frase `CONFIRMO <FASE> <id>`. Nenhuma fase muda portas ou ingressos: somente API/worker geral na fase `dark`, os cinco consumidores na ativação; Nginx, web, PostgreSQL, Redis e outros serviços preservam imagem, identidade, configuração e bind. Depois de cada substituição da API, o operador valida e recarrega graciosamente o Nginx no mesmo container para atualizar a resolução do upstream, sem alterar configuração ou container. A verificação usa o HTTPS existente em `/api/health` e `/healthz`. Uma falha após troca exige `recover`, que restaura imagens/configuração por fase sem tocar o banco; divergência de camada ou mount recusa a remoção.

Se a tentativa de recuperação recriar a API baseline mas falhar antes de persistir o retorno por erro no reload ou na checagem HTTPS, a CLI manterá a intenção no journal. Uma nova execução reconhece o baseline já ativo somente quando sua imagem, configuração, política de restart e saúde correspondem ao recibo, repete a validação/reload do mesmo Nginx e então conclui o passo. Qualquer divergência mantém a recusa segura.

### 5. Evidências operacionais não são inferidas

Autorização de reativação já recuperada do outro chat; não pedir novamente uma autorização genérica para ligar a flag. O proprietário confirmou que as fotos reais já foram utilizadas e dispensou um documento jurídico adicional para a retomada. Registrar essa decisão sem declarar parecer jurídico ou aprovação de medição que não foi fornecida. Preparação de modelos e operador pode avançar após revisão deste desenho, mesmo que uma etapa técnica permaneça bloqueada.

Registrar separadamente: calibração compatível com versão/limiar e grupos; capacidade ARM com ensaio sintético isolado; prova de recuperação; escopo/etapa; decisão do proprietário sobre o uso e revisão técnica/operacional, preservando consentimentos vigentes. A revisão de consentimento em `simplify-mobile-gallery-face-search` substitui os requisitos antigos apenas no escopo que ela define. A tarefa atual não restaura a exigência antiga de representação administrativa prévia nem desabilita o aceite aplicável.

Provas privadas exigidas por `prepare` ou execução SHALL falhar com código de recusa específico quando estiverem ausentes. A ausência de recibo nunca pode ser interpretada como lock ocupado nem contornada por um recibo inferido ou fabricado.

### 6. Recuperar imagens e configuração sem apagar dados concorrentes

Preservar imagens/manifests saudáveis, recibo de fases e backup restaurável antes da aplicação. A operação não muda schema. Falhas antes de exposição recuperam somente serviços/configuração; falhas depois exigem bloquear novas admissões e reconciliar jobs/referências pelas rotinas existentes, preservando embeddings anteriores, pedidos e pagamentos. Não restaurar um dump sobre transações posteriores nem disparar suspensão/revogação com purge como atalho de rollback.

Antes e depois da parada graciosa, o operador consulta `docker diff` de cada consumidor. Conteúdo ou diretórios estruturais não comprovados fazem o operador restaurar o mesmo container e abortar antes de substituição. Candidatos usam root filesystem somente leitura; seus únicos caminhos temporários graváveis são `tmpfs`, fora da camada persistente. A recuperação comprova essa condição e a identidade dos mounts antes de recriar a imagem/configuração anterior. Uma camada gravável inesperada bloqueia a recriação, sem copiar nem apagar conteúdo desconhecido.

### 7. Preservar os fluxos do Mercado Pago

Os baselines da API e do worker SHALL permanecer nos digests saudáveis identificados após 30/10/2026. A mudança facial só pode sobrepor os módulos e dependências explicitamente permitidos para cada serviço; módulos de checkout, Mercado Pago, webhooks e processamento de pagamentos, configurações comerciais e schema SHALL permanecer byte a byte no baseline. Antes de aceitar candidatos, comparar os hashes completos dos módulos e pacotes e executar os testes direcionados de checkout, Orders, webhooks, worker, projeções e persistência. Qualquer diferença fora da allowlist ou falha nesses testes mantém o gate fechado. Essa evidência reduz risco de regressão, mas não constitui promessa de risco zero nem substitui monitoramento após eventual release.

## Risks / Trade-offs

Refinamento operacional de 02/11: `docker diff` pode conter somente diretórios que o Docker criou para montar volumes, mesmo sem dados gravados na camada. Esse caso SHALL ser aceito apenas com exportação TAR em streaming: cada caminho alterado deve ser diretório e destino de mount declarado ou ancestral; o conteúdo subjacente dos mounts não pode conter arquivo, link ou entrada especial; identidade, mounts e diff devem coincidir antes/depois da prova. A checagem ocorre antes e depois da parada e antes de recuperação, sem extrair ou persistir a exportação. Qualquer outra alteração continua bloqueando a recriação. Isso preserva o requisito de ausência de dados na camada, sem descartar diretórios estruturais como se fossem dados desconhecidos.

O inventário SHALL exigir manifests reproduzíveis/protegidos somente dos cinco consumidores que podem ser recriados. Serviços preservados são vinculados por ID, imagem, configuração efetiva, mounts e portas; seus manifests históricos não serão executados nem terão permissões alteradas por esta operação. Git recebe `safe.directory` apenas para as duas raízes fixas via argumento por comando, sem configuração global; Docker retorna IDs integrais com `--no-trunc`.

Se houver containers históricos parados com os mesmos labels de projeto/serviço, a recuperação SHALL usar o ID integral da imagem candidata salvo em `active_ids`, validar seus labels/imagem/configuração e recusar qualquer concorrente ativo. A seleção sem identidade persistida permanece fail-closed.

**Registro operacional (02/11/2026, BRT):** a primeira tentativa da fase `dark` foi recusada com `identidade_invalida` porque `_current` chamava `docker ps -aq` sem `--no-trunc`; o Docker retornou IDs curtos, recusados pelo próprio validador de `inspect`. O journal ficou em `applying_dark`, sem `stop_intent`, `stop_restore`, serviços parados ou substituídos; inventário independente confirmou API, worker e serviços preservados saudáveis nas imagens anteriores. Corrigir o consumidor de IDs integrais e reconciliar o journal somente pela fase `recover` do operador atualizado, preservando o recibo original.

- [Imagem sem dependência, arquivo ou ABI compatível] → Inventário por baseline, dependências fixadas, validação ARM64 isolada e recusa anterior à troca de serviços.
- [Flag não torna o recurso funcional] → Verificar configuração completa, calibração, admissão, claims, resultado autenticado e caixas faciais na UI.
- [Fallback legado amplia o canary] → Modo estrito em todos os consumidores, cenários para galerias novas e allowlist revisada.
- [Gates externos sem evidência] → Manter tarefas correspondentes abertas e continuar somente preparações independentes autorizadas; não fabricar registros.
- [Operação paralela ou drift] → Lock exclusivo da Markina, inventário recente, fingerprint e recusa antes da primeira mutação.
- [Rollback apaga índice ou movimento financeiro] → Recuperação por fase, sem migration, dump indiscriminado ou transição que agenda purge.

## Migration Plan

1. Revisar os artefatos e implementar/validar o operador e o modo estrito em base isolada; nenhuma migration faz parte desta change.
2. Conferir `main`, CI, criar checkout root-only separado do suporte no SHA exato do merge e revalidar os cinco candidatos após rebind controlado somente do campo `support_sha` no manifesto.
3. Conferir imagens, módulos, schema e recuperação, e produzir fingerprint atual com o plano concreto de serviços/portas para a janela operacional autorizada.
4. Construir/verificar os candidatos sem dados reais; ensaiar falhas, recuperação e capacidade ARM com dados sintéticos.
5. Satisfeitos os gates, aplicar a fase `dark` preservando schema/configuração e conferir saúde e não regressão dos fluxos comerciais.
6. Registrar evidência verdadeira de calibração e escopo; ativar a etapa aprovada e fazer a busca autenticada sob autorização para os dados usados.
7. Observar SLOs; promover somente com evidência e revisão da etapa ou recuperar conforme o recibo. Não declarar disponibilidade geral com base em canary.

## Gates externos atuais

O proprietário respondeu sobre o acervo real previamente utilizado e dispensou documento jurídico adicional. Permanecem a reconciliação técnica da calibração exigida pelo runtime, o escopo inicial, a verificação atual de backup/restore e a revisão deste desenho. São critérios explícitos de execução, não parâmetros a preencher com valores inventados. `investigation.md` distingue fatos confirmados de trabalho ainda não executado.
