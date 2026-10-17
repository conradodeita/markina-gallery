# Spec Delta

## ADDED Requirements

### Requirement: Manutenção de captura é distinta da primeira ativação
A entrega autorizada da captura SHALL atualizar somente o runtime já ativo no baseline de produção verificado `fe0a05a74dd1d6941b160e75c2081c78dad3bc05`, que sucede a referência histórica `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`. O workflow SHALL conferir autorização versionada, baseline, escopo e blobs revisados, CI, inventário e aprovação protegida de produção. A manutenção SHALL NOT aprovar gates de primeira ativação ou expansão.

#### Scenario: Atualização corretiva de recurso existente
- **WHEN** o proprietário autoriza a atualização e todos os contratos de manutenção são conferidos
- **THEN** a pendência documental dos gates de primeira ativação não bloqueia a entrega; configuração, flag ativa, acesso, modelo, índice, limiar, consentimento e retenção permanecem preservados e o job mutável aguarda a aprovação protegida

#### Scenario: Estado ou escopo exige primeira ativação
- **WHEN** a flag atual está desligada, o baseline diverge ou há alteração fora dos arquivos/blobs autorizados
- **THEN** a manutenção é recusada, sem ativar recurso nem substituir as aprovações necessárias à expansão

### Requirement: Job de produção é disparado automaticamente após CI
Um workflow SHALL iniciar automaticamente a publicação do SHA aprovado para `main` após CI e validações obrigatórias concluírem com sucesso. O job SHALL aguardar aprovação do ambiente protegido e SHALL repetir inventário de produção, conferir o SHA e limitar mutações aos serviços Pick-your-Pic explicitamente incluídos no plano aprovado.

#### Scenario: CI verde após merge
- **WHEN** um PR aprovado é integrado à `main` e todos os jobs obrigatórios terminam com sucesso
- **THEN** o GitHub inicia automaticamente o job de publicação e o mantém aguardando aprovação do ambiente `production` antes de qualquer mutação remota

#### Scenario: CI falha ou aprovação não é concedida
- **WHEN** uma validação obrigatória falha ou o ambiente protegido não aprova a execução
- **THEN** nenhum comando de mutação é executado em produção

#### Scenario: Inventário ou SHA diverge
- **WHEN** o inventário imediatamente anterior não corresponde ao plano aprovado, o SHA não é o candidato aprovado ou serviços/portas de terceiros seriam afetados
- **THEN** o job falha fechado antes de alterar o ambiente e registra o motivo sem expor segredos

#### Scenario: Publicação de alteração facial atravessa serviços
- **WHEN** a versão altera API, web ou workers faciais
- **THEN** o workflow publica o conjunto de serviços necessário conforme inventário e plano aprovados, sem usar o procedimento limitado ao serviço `web` como substituto de uma publicação integral

### Requirement: Correção iterativa e merge automático após CI
O executor SHALL iterar correções verificáveis de CI dentro do escopo sem aprovação por push. O PR SHALL usar merge automático condicionado aos checks obrigatórios e às revisões exigidas pela política do repositório. Não SHALL haver push adicional apenas para iniciar o deploy.

#### Scenario: Correção iterativa do CI
- **WHEN** um check obrigatório falha por problema verificável dentro do escopo
- **THEN** o executor consulta os logs, corrige, publica commit/push e acompanha outro CI sem pedir aprovação por push, repetindo até ficar verde ou até encontrar uma decisão/acesso humano necessário

#### Scenario: Merge automático e mesmo run de publicação
- **WHEN** checks obrigatórios e revisões exigidas estão aprovados
- **THEN** o PR é integrado automaticamente e o mesmo fluxo GitHub executa preflight e release sem push separado para iniciar deploy

### Requirement: Preflight anterior à aprovação única de produção
Após CI e merge, o workflow SHALL executar preflight somente-leitura antes de qualquer aprovação, com credencial SSH separada, restrita à rotina de inventário e sem capacidade de escrita. O preflight SHALL fornecer evidência revisável. Apenas o job mutável SHALL usar o environment protegido `production`, para uma única aprovação antes da mutação.

#### Scenario: Preflight antes da única aprovação
- **WHEN** CI e merge concluem com sucesso
- **THEN** o workflow executa inventário somente-leitura com chave SSH separada e restrita, apresenta SHA, host/projeto, serviços, portas/subdomínio, fingerprint, impacto e rollback, e só então aguarda aprovação do environment `production` no job mutável

#### Scenario: Credencial somente-leitura ausente
- **WHEN** não existe chave SSH separada e restrita à rotina de inventário
- **THEN** o workflow falha fechado antes de conectar ao servidor e não reutiliza a chave de deploy nem reduz a proteção de produção

### Requirement: Inventário compara a configuração efetiva e verifica a troca
O preflight e o release SHALL comparar os labels ativos com hashes da configuração Compose efetivamente resolvida, incluindo `env_file` e o metadado operacional `APP_VERSION`. O JSON resolvido MUST permanecer em memória e SHALL NOT ser impresso ou persistido. Divergência real SHALL impedir o release. O script SHALL verificar novamente os hashes após a troca, esperar os serviços saudáveis por até 120 segundos e validar/recarregar somente o nginx da Markina antes de conferir HTTPS.

#### Scenario: Hash direto omite resolução do env_file
- **WHEN** a versão do Compose omite `env_file` no hash direto, mas o hash da configuração resolvida corresponde ao container
- **THEN** o inventário aceita a correspondência efetiva, preserva o gate de igualdade e não altera serviços nem segredos

#### Scenario: Configuração efetiva diverge
- **WHEN** o hash resolvido não corresponde ao label de um serviço aprovado
- **THEN** o inventário falha sem produzir aprovação válida e sem alterar o serviço

#### Scenario: Serviço é recriado no release aprovado
- **WHEN** web, API e worker de busca são recriados
- **THEN** a liberação somente registra sucesso após espera limitada por saúde, leitura dos novos hashes, reload confinado ao nginx Markina e smoke HTTPS aprovados

### Requirement: Migration facial aditiva é validada e aplicada de forma isolada
Após publicação da ampliação aditiva da constraint de declaração facial, o workflow de manutenção SHALL verificar que o banco está exatamente na revisão `20261016_0082` e preservar essa revisão, sem reaplicar migrations. Divergência de revisão SHALL interromper o release antes da recriação de qualquer serviço. O preflight e fingerprint SHALL incluir a revisão atual do banco.

#### Scenario: Banco está na revisão esperada
- **WHEN** a aprovação de produção está vigente e o inventário confirma `20261016_0082`
- **THEN** o job preserva a revisão e segue com a recriação coordenada dos serviços Pick-your-Pic

#### Scenario: Banco diverge da revisão esperada
- **WHEN** o inventário ou a revalidação pós-aprovação encontra outra revisão ou múltiplas cabeças
- **THEN** o job falha fechado sem migration, recriação ou alteração de serviços

### Requirement: Smoke HTTPS tolera apenas transição limitada do proxy
Após saúde dos containers e reload confinado ao Nginx Markina, o smoke SHALL tentar novamente respostas HTTP transitórias como 502, com no máximo cinco retentativas, intervalo de dois segundos e orçamento de quarenta segundos para novas tentativas por endpoint. Cada requisição SHALL ter timeout de cinco segundos. Falha persistente SHALL manter o job vermelho e SHALL NOT registrar release saudável.

#### Scenario: Primeiro request ocorre durante reload
- **WHEN** o primeiro request recebe 502 e um seguinte responde com sucesso dentro do orçamento
- **THEN** o release continua para os demais endpoints e só registra sucesso após todos passarem

### Requirement: Manutenção parte do último release saudável
O preflight SHALL confirmar que o checkout ativo corresponde exatamente ao SHA registrado em `/var/lib/markina-gallery/deploy-state/facial-last-healthy.sha`. O SHA alvo MUST descender desse checkout e ser o HEAD atual de `origin/main`. Marcador ausente, inválido, divergente ou histórico não ancestral SHALL interromper o preflight sem mutação. Isso SHALL permitir releases corretivos sucessivos sem fixar no código o SHA do deploy anterior.

#### Scenario: Release saudável anterior
- **WHEN** o marcador, checkout e versão ativa da API concordam e o alvo atual da `main` descende do checkout
- **THEN** o preflight prossegue com a verificação de configuração e inventário existentes

#### Scenario: Baseline remoto diverge ou falta
- **WHEN** o marcador está ausente, inválido, diverge do checkout ou o candidato não descende do checkout
- **THEN** o preflight falha fechado antes de qualquer aprovação ou mutação
