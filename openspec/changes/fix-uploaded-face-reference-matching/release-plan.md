# Plano de publicação para revisão — não autorizado

## Estado e inventário

PR #213 contém a correção funcional aprovada (upload/câmera 500, toque 600, firme 750, direcionamento ao resultado). A aprovação funcional não autoriza mutação remota. `maintenance_release.authorized=false` no manifesto operacional existente impede reutilizar a autorização da captura anterior; os gates de primeira ativação continuam pendentes e independentes.

Diagnóstico somente leitura de 17/10/2026: `/opt/markina-gallery`, projeto `markina-gallery`, checkout `0779b3e4400f8511980c2d18e79ef8eea586a341`, domínio `markina.pickyourpic.com.br`, entrada Markina `127.0.0.1:8080`. API, web e face-search-worker saudáveis; API aproximadamente 195 MiB e worker 159/512 MiB no inventário inicial. Modelo SFace/128, índice highres-v1 atual, limiar 750 e faixa ambígua geral ausente. Repetir inventário protegido após merge/antes de aprovar qualquer execução; estes dados não são um inventário futuro.

## Escopo proposto de impacto

Atualizar somente `web`, `api` e `face-search-worker`, mantendo modelo, banco e índice. O worker recebe duas faixas numéricas adicionais; a comparação e a retenção continuam no mesmo job. Não há migration ou reindexação. Os demais serviços, volumes, redes, projetos, portas, proxy externo, firewall, DNS e certificados ficam fora da operação. Pode ocorrer breve indisponibilidade da aplicação e pausa no consumo da fila durante recriação desses três serviços; não prometer indisponibilidade zero da Markina.

Nenhuma alteração em `.env`/secrets é necessária para os defaults aprovados. Compose acrescenta somente as duas variáveis não secretas da configuração facial, preservando vazio explícito. A configuração resolvida e os hashes dos serviços deverão ser conferidos no inventário, sem imprimir segredos.

## Gates que precisam de revisão operacional

O script publicado `deploy-prod-facial-services.sh` recusa mudanças em `docker/`; o avaliador anterior também não admite os novos arquivos compartilhados de apresentação como runtime revisado. A adequação preparada nesta PR inclui esses arquivos exatos e aceita somente o Compose principal com blob autorizado, após o aceite separado do proprietário. Sua validação CI está pendente; a autorização operacional permanece falsa e o wrapper instalado no servidor continua intacto.

Antes da execução, preparar/revisar um escopo de manutenção que fixe exatamente os novos arquivos de runtime, os testes relacionados e o blob específico de Compose, em vez de liberar alterações genéricas em Docker ou frontend. Caso o script de inventário precise mudar, seu blob pinado e o wrapper root-owned também exigirão revisão e autorização operacional próprias. Isso deverá integrar o plano definitivo autorizado, nunca ser contornado por SSH avulso ou deploy manual fora do gate.

O rollback deverá cobrir imagens dos três serviços e Compose anterior, sem restauração/destruição de dados. O fluxo `app-rollback` isolado não cobre o worker facial e não deve ser presumido suficiente. Fixar revisões/imagens e confirmar o procedimento no plano definitivo antes de aprovar a publicação.

Procedimento de recuperação preparado para revisão: antes do release, o script já preserva tags `markina-gallery-rollback-<serviço>-<SHA ativo>`, referências de imagem e `facial-previous.sha` no estado exclusivo Markina. Após novo inventário e autorização específica, conferir checkout limpo, SHA anterior e as três imagens preservadas; restaurar somente essas referências e o checkout anterior, resolver os mesmos overlays/env protegidos e recriar exclusivamente `web api face-search-worker` com `--no-deps --no-build`, espera de saúde limitada e `APP_VERSION` anterior. Validar/recarregar somente o Nginx Markina e conferir HTTPS/schema antes de atualizar o marcador saudável. Não executar migration reversa, restauração de banco, prune, remoção de volumes ou reinício de outros serviços. Esse procedimento não foi executado nem autoriza rollback automático; a execução deverá ser revisada e aprovada como operação de recuperação própria se necessária.

## Adequação proposta para aceite antes do código operacional

- Incluir na lista exata de runtime revisado `docker/docker-compose.yml`, `frontend/app/gallery-presentation.tsx` e `frontend/app/public-galleries/[galleryId]/page.tsx`, mantendo validação por blob Git e recusando qualquer arquivo fora do escopo. Acrescentar somente os dois testes diretamente relacionados hoje ausentes da lista operacional: configuração facial e apresentação compartilhada.
- Substituir a recusa genérica de qualquer mudança Docker por regra que permita exclusivamente `docker/docker-compose.yml` quando o blob alvo coincidir com o manifesto de manutenção autorizado. Qualquer outro arquivo em `docker/`, mudança sem autorização, manifesto incompleto ou hash divergente continuará recusado. Não mudar os serviços permitidos, portas, volumes ou limites de recursos.
- Atualizar no repositório o hash pinado do script de inventário e seus testes de política. A cópia root-owned do wrapper no servidor só poderá ser atualizada após aprovação operacional específica; este aceite inicial permite preparar e testar o código, sem mutação remota.
- Manter `maintenance_release.authorized=false` durante a preparação. A revisão/execução final continuará exigindo CI, inventário/fingerprint do alvo exato e aprovação no ambiente protegido. Preservar todos os gates de primeira ativação.
- Preparar rollback restrito às imagens e configuração dos mesmos três serviços, com hashes de origem/destino e sem migration ou operação de dados. Não reutilizar o rollback exclusivo de API/web.

O proprietário respondeu “Aprovar a preparação do gate restrito” em 17/10/2026. A adequação foi preparada conforme esse aceite e aguarda CI; não há autorização implícita para instalação remota ou publicação. A resolução do Compose anterior após build usa apenas YAML versionado em memória e relê o ambiente atual, sem gravar JSON resolvido/segredos.

## Validação posterior autorizada

Depois da publicação aprovada, confirmar saúde, versão, faixas efetivas e manutenção da revisão do banco. Repetir a referência `DSC07382.jpg` na galeria autorizada e conferir presença de `LIV00862.jpg`, classificação como possibilidade e exclusão da referência. Repetir as outras duas referências e a busca por toque sem tratar todas as candidatas como identidade confirmada. Conferir desktop/mobile, câmera/upload, conclusão com ampliação aberta e título dos resultados no viewport/foco. Registrar revisão humana da qualidade separadamente dos testes automatizados. Nenhuma compra ou seleção é necessária.

## Bloqueio atual

CI/revisão da PR e autorização operacional do plano definitivo estão pendentes. Não houve merge, publicação, mudança de configuração remota, índice ou banco por este executor. A task de publicação e validação visual permanece aberta; os testes locais automatizados não foram executados conforme a preferência vigente.

## Inventário atualizado e revisão de destino — 17/10/2026, 13:47–13:51 BRT

Nova consulta somente leitura confirmou atualização externa do servidor para `25cd338f7243a114e8151e6bda3d03204b12ae43`, PR #212 em `develop`, e banco `20261017_0083`. Checkout limpo, serviços Markina saudáveis, entrada exclusiva `127.0.0.1:8080` e HTTPS `/api/health` saudável. Consulta da revisão do banco usou transação `READ ONLY`; não foi executada migration. Worker continua com `APP_ENV=staging`, limiar 750, faixa geral vazia, faixas específicas ausentes e os mesmos modelos/qualidade.

`origin/main` permanece em `b695b2e`, enquanto `origin/develop` está em `25cd338`. A atualização externa inclui suporte de lote por pasta, migration 0083 e correções administrativas, além da reconciliação da homologação nas PRs #210/#212. Nenhum desses arquivos foi revertido. Os arquivos de busca facial/apresentação/Compose desta correção permanecem iguais ao baseline do diagnóstico; a descoberta não invalida a causa reproduzida, mas invalida o plano operacional anterior para este servidor.

O script de produção preparado exige schema 0082 e descendência de main; não está apto ao servidor atual. Proposta para revisão do proprietário: redirecionar PR #213 para `develop`, integrar a linha atual preservando integralmente a atualização externa, resolver os conflitos operacionais e repetir os gates afetados. A publicação passaria pelo fluxo protegido `homolog` vigente, conservando banco 0083 e sem nova migration funcional desta correção; aprovação de publicação e testes reais continuam separadas. A integração não deve transferir essas atualizações para main implicitamente nem reaproveitar aprovação de produção. Até aceite da revisão de destino, nenhuma adaptação dependente será implementada.

Aceite recebido em 17/10/2026: “Integrar na develop atual e validar”. Integração e CI autorizados; preservar o workflow de homologação e a separação vigente dos gates de produção. Publicação, instalação do wrapper e qualquer mutação remota continuam sem autorização. O plano de produção/0082 acima permanece histórico e não será aplicado a este servidor; o gate de produção preparado não se torna elegível por essa decisão.
