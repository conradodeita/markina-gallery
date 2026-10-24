# Design

## Context

Ver `proposal.md` e `specs/deployment-operations/spec.md`. A migration `20261022_0087` descende de `20261021_0086` e remove configuração/credenciais InfinitePay, a URL operacional e a finalidade OTP exclusiva, mantendo o histórico financeiro. O release API/web atual rejeita migrations e Compose; o release facial tem a revisão fixa `20261016_0082` e usa outro conjunto de serviços/configuração. O manifesto API/web registra baseline e schema `0084`, portanto precisa ser reconciliado com inventário remoto antes de qualquer publicação. A porta/domain do deployment definido no repositório são `127.0.0.1:8080` e `https://markina.pickyourpic.com.br`; isso não confirma a topologia atualmente ativa.

## Goals / Non-Goals

**Goals:**

- Criar caminho manual, protegido e isolado para exatamente esta migration e publicação da aposentadoria.
- Amarrar autorização a SHA, revisão corrente, Compose efetivo, serviços, domínio/porta, fingerprint e backup verificado.
- Preservar todos os registros financeiros e confirmar as duas compras históricas somente por leitura.
- Remover apenas o mount e o arquivo de binding InfinitePay exclusivos, sem revelar conteúdo nem afetar terceiros.

**Non-Goals:**

- Implantar Mercado Pago ou habilitar checkout com cartão/PIX do Mercado Pago.
- Revogar links já emitidos no provedor, alterar compras, migrar dados PIX ou editar migrations históricas.
- Modificar `.env`, segredos de outros provedores, serviços compartilhados, proxy, firewall, DNS ou certificados.
- Tentar downgrade Alembic para reverter a remoção de credenciais.

## Decisions

- Usar workflow manual dedicado, executável somente a partir de `main`, com ambientes protegidos de preflight e produção. Não ampliar o release rotineiro API/web nem reutilizar o release facial de alvo fixo.
- O classificador geral da CI deve concluir com sucesso ao identificar um delta `protected`, sem autorizar publicação automática; o release de aposentadoria só pode ocorrer pelo workflow manual dedicado. Deltas `mixed` continuam falhando fechados.
- O preflight remoto é somente leitura e coleta minimizada: SHA/checkout, revisão Alembic, serviços e health, Compose efetivo e suas fontes, publicação de portas/domínio e metadados do binding (caminho, tipo, mount/consumidores), sem conteúdo de segredos, PII ou dados de pagamento. O gate para se qualquer valor for inesperado ou ambíguo.
- A publicação 0086 mantém `/var/lib/markina-gallery/deploy-state/payments0086-active-images.compose.json`, SHA-256 `899df26fa54fbdd369d66aa0f446340853591e9163a27ae5963564961f0d8e60`, que fixa somente as imagens/APP_VERSION de api, web e migrate. API/web carregam esse overlay na proveniência Docker; nginx conserva os seis arquivos Compose anteriores. O inventário deve verificar o arquivo e seu hash, incluí-lo apenas ao calcular o estado ativo e validar a proveniência específica de cada serviço. O Compose candidato ao release continua sem esse overlay para não fixar as imagens antigas 0086.
- A prova de exclusividade do binding examina recursivamente as raízes de configuração compartilhadas, segue links de diretório com detecção de ciclos por dispositivo/inode e inspeciona os mounts bind de todos os containers existentes no daemon Docker. Erro de leitura ou inspeção incompleta SHALL bloquear o inventário e a remoção; nunca deve ser interpretado como ausência de referência.
- O script de inventário pode ser executado a partir do wrapper SSH antes do checkout de produção conter a change. Dependências auxiliares de leitura devem vir do mesmo SHA aprovado, com blob Git fixado e verificado antes da execução; o preflight não pode depender de arquivos ainda não publicados no checkout ativo.
- O release cria e valida backup consistente do banco e registra evidência agregada de contagens/digests financeiros antes da migration. A remoção do binding é uma etapa pós-publicação e saúde; seu caminho deve ser exatamente o inventariado e exclusivo da Markina.
- Aplicar somente `20261022_0087` quando a revisão real for exatamente `20261021_0086`; qualquer outra revisão bloqueia a execução e exige reconciliação humana.
- Em falha anterior ao início da migration, recuperar API e worker iniciando os mesmos containers que foram pausados e aguardar healthchecks saudáveis; não recriá-los com o Compose alvo nem depender de um nome de imagem original, pois a publicação 0086 identifica API/web por digest.
- Construir as imagens de `api`, `web` e `worker` no SHA aprovado enquanto a versão atual atende. Pausar API e worker antes do backup/migration porque o worker importa o modelo de pagamentos e pode consultar colunas removidas; aplicar a migration explicitamente antes de iniciar a versão nova, publicar os três serviços com o projeto/Compose `markina-gallery`, e verificar a revisão final, saúde e HTTPS. Não recriar nginx nem outros serviços; se a mudança de upstream exigir reload do Nginx, bloquear e exigir plano/aceite específico antes dessa ação.
- Como a migration é de avanço e remove dados de configuração, recuperação após sua aplicação restaura o backup validado e a versão anterior como operação coordenada, limitada ao banco da Markina; não executar downgrade Alembic.
- Manter o manifesto de runtime fechado. Atualizar baseline, blobs e schema apenas com SHA integrado e evidência do inventário do servidor; hashes não constituem aprovação. O fingerprint remoto e o gate protegido seguem obrigatórios.

## Risks / Trade-offs

- [O estado real do servidor diverge de `0086` ou do manifesto conhecido] → interromper antes de mutação e reconciliar o estado com inventário protegido.
- [Backup existe, mas não pode ser restaurado] → exigir verificação técnica de integridade e evidência de restauração em ambiente descartável antes da aprovação.
- [Arquivo de binding tem uso compartilhado ou localização diferente] → não apagá-lo; remover somente o mount da versão aprovada e registrar bloqueio de limpeza do arquivo.
- [Scanner não consegue ler uma raiz de configuração ou inspecionar todos os containers] → falhar fechado e exigir que a cobertura de inventário seja completada antes de aprovar exclusividade.
- [Falha de API/web/worker após migration] → manter serviços anteriores/imagens identificadas, parar novos passos, restaurar backup se necessário e validar a versão anterior com o schema restaurado.
- [Evidência agregada pode expor valores financeiros] → registrar apenas totais/contagens e hashes estáveis aprovados; nunca escrever tokens, payloads, nomes ou conteúdo de recibos nos logs.

## Migration Plan

1. Integrar a change local de aposentadoria por PR revisado em `main`; executar CI completo e preparar manifesto com blobs exatos.
2. Executar inventário remoto somente leitura em produção. Exibir ao proprietário SHA, schema, serviços/saúde, Compose, domínio/porta, binding identificado, impacto, backup/recuperação e fingerprint; aguardar aprovação explícita do inventário e do plano.
3. Confirmar schema `20261021_0086`, preservar evidência agregada financeira e gerar/validar backup antes de aplicar qualquer migration.
4. Executar migration `20261022_0087`, confirmar schema e invariantes financeiros, publicar API/web/worker da versão aprovada e verificar healthchecks locais e HTTPS.
5. Confirmar PIX próprio e histórico das duas compras InfinitePay em leitura somente; remover exclusivamente o arquivo de binding inventariado depois da saúde dos serviços e confirmar que nenhum serviço da Markina ainda o monta.
6. Em falha pré-migration, abortar sem alteração. Em falha após o início/aplicação da migration, parar e usar recuperação coordenada de backup e versão anterior; não executar downgrade. Registrar evidência e não marcar o release concluído até todos os checks passarem.

## Open Questions

- O inventário remoto precisa confirmar se o backup previsto pelo procedimento atual cobre a restauração consistente do banco e apresentar evidência de restauração previamente testada. O código local ainda não confirmou essa evidência nem oferece um executor de restauração isolado; sem isso, os passos mutáveis da migration/release permanecem bloqueados.
- O wrapper SSH root-owned foi atualizado em 2026-10-23 para o blob `1d37ee3b4c0ef6edbda4fe6661f8f7840152059b`, proprietário `root:root`, modo `0755`, SHA-256 `a19c30887bbe1cd0d585098057cad3768e9e4cae797c8c02d35e9207ebc61ce6`; a versão anterior foi preservada em `/var/backups/markina-gallery/preflight-ssh-wrapper-20261023T203245Z-ace79e48`. As regras anteriores de preflight app/facial foram mantidas, e a nova rota aceita somente inventário.
- O run manual `40003998285` passou CI, mas foi recusado pelo wrapper antigo antes do inventário. O run `40020083809` expôs que `docker compose config --format json` omitia referências `env_file`; o run `40032437683` validou a correção em CI, mas o preflight falhou porque `retirement_host_references.py` não existe no checkout de produção anterior à publicação. Após integrar a dependência pelo SHA validado, o run `40040189223` falhou porque `/etc/xdg/systemd/user` é um link de diretório e o scanner recusava todos esses links; a inspeção read-only identificou também dois links para diretórios Snap sob `/root/snap`. Nenhum job mutável foi executado. O scanner seguirá links com controle de ciclos por dispositivo/inode e continuará falhando diante de erros de leitura ou inspeção incompleta.
- O caminho/tipo do arquivo de binding e a existência de consumidores fora da Markina são desconhecidos até o preflight; qualquer ambiguidade mantém a remoção física bloqueada.
- O preflight `40046086906` recusou corretamente a origem Compose da API: a publicação 0086 adicionou um sétimo arquivo somente à proveniência de API/web, enquanto o inventário esperava seis para todos. O overlay foi lido somente como configuração de imagens; seu modo/owner/hash coincidem com o registro da publicação. Corrigir a coleta sem propagar o overlay ao Compose candidato; o inventário e seu fingerprint ainda precisam ser produzidos novamente.
- O manifesto API/web está registrado em `0084`, enquanto a migration da aposentadoria exige que o runtime esteja exatamente em `0086`. Só atualizar baseline e blobs após o inventário remoto e SHA integrado comprovarem o estado real; divergência bloqueia a publicação.
