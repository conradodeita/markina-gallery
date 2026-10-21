# Spec Delta

## ADDED Requirements

### Requirement: Piso de segurança para novo checkout de cartão

O Pick-your-Pic SHALL aceitar nova reserva por cartão InfinitePay somente quando o total autoritativo das fotos com cobrança for pelo menos 100 centavos. A validação SHALL preceder reserva de fotos, gravação de tentativa, alteração de rascunho PIX e chamada externa. A mensagem SHALL informar o mínimo de R$ 1,00 e orientar aumentar a seleção ou escolher PIX quando disponível. O limite MUST NOT se aplicar ao preço unitário, ao PIX manual ou a seleções sem cobrança.

#### Scenario: Total abaixo do mínimo
- **WHEN** a cliente tenta novo checkout por cartão com total entre 1 e 99 centavos, inclusive por chamada direta à API
- **THEN** a emissão é recusada antes dos efeitos, as mesmas fotos continuam selecionadas e o PIX válido permanece utilizável

#### Scenario: Total mínimo com fotos baratas
- **WHEN** os preços individuais são inferiores a R$ 1,00 e a soma das fotos com cobrança é de pelo menos 100 centavos
- **THEN** o mínimo não impede o checkout de cartão e o sistema preserva preços e totais reais

#### Scenario: Tentativa histórica abaixo do mínimo
- **WHEN** a cliente repete a chave e revisão de uma tentativa já existente de poucos centavos
- **THEN** o sistema devolve a tentativa histórica sem emitir outra, liberar suas fotos ou alterar seu estado financeiro

### Requirement: Gateway no primeiro clique explícito

A ação de continuar com cartão SHALL redirecionar a cliente na mesma aba após receber `awaiting_payment` com URL de checkout HTTPS permitida, sem exigir um segundo clique. SHALL conservar a compra e um link de retomada caso a navegação não ocorra. A UI MUST NOT navegar ou emitir pagamento automaticamente ao carregar, atualizar ou focar a página.

#### Scenario: Checkout válido no primeiro envio
- **WHEN** a cliente clica uma vez em continuar com cartão e a API devolve um checkout válido
- **THEN** a UI solicita uma única navegação para essa URL e uma única preparação de cartão

#### Scenario: Duplo clique durante o envio
- **WHEN** a cliente clica novamente antes de chegar a resposta
- **THEN** apenas uma solicitação é enviada e a navegação usa o checkout dessa solicitação

#### Scenario: Resposta sem checkout utilizável
- **WHEN** a resposta é incerta, falhou antes de emitir, é terminal ou não contém URL permitida
- **THEN** a UI não redireciona e conserva as regras publicadas de reserva, idempotência, acompanhamento e recuperação administrativa

#### Scenario: Retomar compra existente
- **WHEN** uma compra aguardando pagamento já está presente ao carregar o carrinho
- **THEN** a UI oferece seu link de retomada sem emitir novo checkout nem navegar sem ação explícita

### Requirement: Preparação restrita do candidato API e web

O candidato SHALL identificar o baseline publicado e os blobs exatos dos três arquivos de runtime afetados, mantendo a revisão0084 e os controles operacionais existentes. Arquivos semelhantes não listados, alterações sem blob revisado, cofre, migrations, workers e dependências novas MUST NOT ser admitidos por essa preparação. Aprovação de CI SHALL NOT equivaler a autorização de merge ou publicação.

#### Scenario: Candidato exato para revisão
- **WHEN** o candidato inclui somente o delta de mínimo e redirecionamento com os blobs do manifesto e seus testes/documentação
- **THEN** os gates locais reconhecem somente API/web e conservam a necessidade de aprovação operacional e inventário antes da publicação

#### Scenario: Runtime adulterado ou ampliação indevida
- **WHEN** um arquivo admitido diverge do blob ou um arquivo adicional não listado é acrescentado
- **THEN** o gate recusa o candidato em vez de aceitar wildcard ou ignorar a divergência
