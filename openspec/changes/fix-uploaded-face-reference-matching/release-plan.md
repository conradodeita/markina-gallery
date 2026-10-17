# Plano de publicação para revisão — não autorizado

## Estado e inventário

PR #213 contém a correção funcional aprovada (upload/câmera 500, toque 600, firme 750, direcionamento ao resultado). A aprovação funcional não autoriza mutação remota. `maintenance_release.authorized=false` no manifesto operacional existente impede reutilizar a autorização da captura anterior; os gates de primeira ativação continuam pendentes e independentes.

Diagnóstico somente leitura de 17/10/2026: `/opt/markina-gallery`, projeto `markina-gallery`, checkout `0779b3e4400f8511980c2d18e79ef8eea586a341`, domínio `markina.pickyourpic.com.br`, entrada Markina `127.0.0.1:8080`. API, web e face-search-worker saudáveis; API aproximadamente 195 MiB e worker 159/512 MiB no inventário inicial. Modelo SFace/128, índice highres-v1 atual, limiar 750 e faixa ambígua geral ausente. Repetir inventário protegido após merge/antes de aprovar qualquer execução; estes dados não são um inventário futuro.

## Escopo proposto de impacto

Atualizar somente `web`, `api` e `face-search-worker`, mantendo modelo, banco e índice. O worker recebe duas faixas numéricas adicionais; a comparação e a retenção continuam no mesmo job. Não há migration ou reindexação. Os demais serviços, volumes, redes, projetos, portas, proxy externo, firewall, DNS e certificados ficam fora da operação. Pode ocorrer breve indisponibilidade da aplicação e pausa no consumo da fila durante recriação desses três serviços; não prometer indisponibilidade zero da Markina.

Nenhuma alteração em `.env`/secrets é necessária para os defaults aprovados. Compose acrescenta somente as duas variáveis não secretas da configuração facial, preservando vazio explícito. A configuração resolvida e os hashes dos serviços deverão ser conferidos no inventário, sem imprimir segredos.

## Gates que precisam de revisão operacional

O script atual `deploy-prod-facial-services.sh` recusa mudanças em `docker/`; o avaliador atual também não admite os novos arquivos compartilhados de apresentação como runtime revisado. Esses controles continuam intactos. O workflow existente não está apto a publicar esta change: não basta tornar a flag de manutenção verdadeira.

Antes da execução, preparar/revisar um escopo de manutenção que fixe exatamente os novos arquivos de runtime, os testes relacionados e o blob específico de Compose, em vez de liberar alterações genéricas em Docker ou frontend. Caso o script de inventário precise mudar, seu blob pinado e o wrapper root-owned também exigirão revisão e autorização operacional próprias. Isso deverá integrar o plano definitivo autorizado, nunca ser contornado por SSH avulso ou deploy manual fora do gate.

O rollback deverá cobrir imagens dos três serviços e Compose anterior, sem restauração/destruição de dados. O fluxo `app-rollback` isolado não cobre o worker facial e não deve ser presumido suficiente. Fixar revisões/imagens e confirmar o procedimento no plano definitivo antes de aprovar a publicação.

## Validação posterior autorizada

Depois da publicação aprovada, confirmar saúde, versão, faixas efetivas e manutenção da revisão do banco. Repetir a referência `DSC07382.jpg` na galeria autorizada e conferir presença de `LIV00862.jpg`, classificação como possibilidade e exclusão da referência. Repetir as outras duas referências e a busca por toque sem tratar todas as candidatas como identidade confirmada. Conferir desktop/mobile, câmera/upload, conclusão com ampliação aberta e título dos resultados no viewport/foco. Registrar revisão humana da qualidade separadamente dos testes automatizados. Nenhuma compra ou seleção é necessária.

## Bloqueio atual

CI/revisão da PR e autorização operacional do plano definitivo estão pendentes. Não houve merge, publicação, mudança de configuração remota, índice ou banco nesta execução. A task de publicação e validação visual permanece aberta; os testes locais automatizados não foram executados conforme a preferência vigente.
