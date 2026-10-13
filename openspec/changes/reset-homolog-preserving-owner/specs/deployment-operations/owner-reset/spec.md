## Purpose

Permitir um reset inventariado dos dados de teste em homologação, preservando somente a conta proprietária e suas configurações, com isolamento operacional verificável.

## ADDED Requirements

### Requirement: Registro inerte e seleção explícita da ref de homologação
O workflow SHALL estar registrado na branch padrão `main` com o mesmo contrato de inputs da versão operacional em `develop`. A versão em `main` SHALL recusar a manutenção sem checkout, Environment, secrets ou SSH. A versão operacional SHALL conservar o gate protegido `homolog` e exigir ref `develop` para modos `owner-*`.

#### Scenario: Operador seleciona main
- **WHEN** o operador dispara o workflow registrado na ref `main`
- **THEN** o job encerra com orientação para selecionar `develop`, sem acesso ao servidor ou dados

#### Scenario: Operador seleciona develop
- **WHEN** o operador dispara `owner-inventory` ou `owner-execute` na ref `develop`
- **THEN** o GitHub usa o workflow operacional daquela ref e o Environment `homolog` exige aprovação humana antes do acesso ao servidor

### Requirement: Identidade proprietária inequívoca
O reset SHALL exigir ambiente de homologação, proprietário exato, identidade `platform_owner` correspondente e único vínculo ativo de fotógrafo. Contexto ausente, ambíguo ou incompatível MUST impedir qualquer mutação.

#### Scenario: Proprietário válido
- **WHEN** o e-mail solicitado identifica o proprietário e seu único tenant ativo
- **THEN** o inventário mostra elegibilidade e contagens por categoria sem expor e-mails adicionais, segredos, hashes de senha, cookies ou mídia

#### Scenario: Identidade divergente
- **WHEN** falta proprietário, há múltiplos vínculos ou a identidade técnica é diferente
- **THEN** a execução é recusada sem alteração de banco, arquivos ou filas

### Requirement: Preservação da conta e das configurações proprietárias
O reset SHALL preservar integralmente credenciais, TOTP, sessões administrativas, vínculos/privilégios e configurações do proprietário, incluindo marca, PIX, InfinityPay, WhatsApp, notificações, preços e processamento. Evolution, segredos externos e observabilidade global MUST permanecer preservados.

#### Scenario: Cinco fotógrafos de teste
- **WHEN** o reset de homologação é autorizado para conservar somente a conta proprietária
- **THEN** permanece exatamente um admin e seu tenant/vínculo, as demais contas e suas configurações são removidas, e a comparação das linhas/ativos preservados confirma o mesmo estado

#### Scenario: Referência incompatível
- **WHEN** uma configuração preservada referencia conta ou linha que seria removida
- **THEN** a execução aborta antes de excluir qualquer linha, sem reatribuição silenciosa

### Requirement: Remoção integral do acervo de teste
O reset SHALL zerar dados operacionais de todas as contas: clientes, galerias, pastas, fotos, interações, compras, pagamentos de teste, entregas, dados faciais, filas e mídia exclusiva. Ativos de marca do proprietário SHALL conservar os mesmos bytes; arquivos de outras contas SHALL ser removidos dentro das raízes aprovadas.

#### Scenario: Resultado vazio
- **WHEN** a execução termina com os writers pausados
- **THEN** as contagens operacionais e de arquivos de acervo são zero e os ativos/configurações do proprietário continuam disponíveis

#### Scenario: Link para mídia externa
- **WHEN** uma raiz é symlink ou um caminho aponta para fora do volume autorizado
- **THEN** a operação recusa a raiz ou remove somente o link interno, sem seguir ou excluir arquivos externos

### Requirement: Isolamento de operação e classificação fechada
O reset SHALL conferir SHA publicado, schema, topologia, volumes, origem HTTPS e writers exclusivos. Toda tabela e serviço SHALL ter classificação explícita; novos itens desconhecidos MUST bloquear execução. A limpeza operacional antiga SHALL continuar recusando multiplicidade de fotógrafos.

#### Scenario: Writer ou tabela desconhecido
- **WHEN** o inventário encontra item não classificado
- **THEN** nenhuma exclusão ocorre e o motivo é registrado sem ampliar o escopo automaticamente

#### Scenario: Serviços vizinhos ativos
- **WHEN** o reset pausa os writers da Markina
- **THEN** somente API/workers Markina inventariados são parados e retomados; Evolution e projetos vizinhos conservam containers, configuração, redes, portas e volumes

#### Scenario: Metadados de retomada sem prontidão
- **WHEN** o diretório fixo de retomada está ausente, tem symlink, dono diferente do operador, modo diferente de 0700 ou não permite escrita/acesso
- **THEN** inventário e execute recusam a operação antes de pausar writers, excluir dados ou ampliar permissões do diretório pai

#### Scenario: Snapshot Docker confiável
- **WHEN** um contêiner não tem o campo Health ou Docker inspect falha
- **THEN** ausência de Health é representada como none, falha de inspect impede a operação, e o snapshot só é aceito com exatamente os três serviços Evolution ativos

#### Scenario: Listagem de writers indisponível
- **WHEN** Docker não consegue listar os serviços ativos para o inventário ou para conferir a pausa
- **THEN** a execução é recusada sem iniciar a exclusão, em vez de assumir uma lista vazia de writers

### Requirement: Execução sem novo backup, exclusão autorizada de dumps e retomada honesta
O reset SHALL exigir autorização específica, inventário e sinalização sem dump. Após conclusão, SHALL excluir somente os 164 `.dump` regulares na raiz fixa da Markina, com contagem e bytes iguais ao manifesto autorizado; divergência MUST bloquear. Demais arquivos e snapshots SHALL permanecer. Falha após commit MUST ser reportada como parcial e manter writers pausados para retomada segura, sem alegar reversão.

#### Scenario: Reset e remoção dos dumps autorizados
- **WHEN** o proprietário autoriza o reset sem backup e separadamente autoriza excluir os 164 dumps inventariados após publicar o domínio
- **THEN** o procedimento não cria dump, não refaz deploy/migration, compara preservação e só exclui os `.dump` se o manifesto fixo continuar idêntico, mantendo snapshots e demais tipos

#### Scenario: Manifesto de dumps divergente
- **WHEN** caminho, tipo, contagem ou tamanho dos dumps diferem do inventário aprovado
- **THEN** nenhum arquivo `.dump` é removido e os writers permanecem pausados para inspeção

#### Scenario: Falha após remoção do banco
- **WHEN** a exclusão de arquivos falha depois do commit
- **THEN** a fase parcial é explicitada, os writers permanecem pausados e repetir o procedimento para o mesmo proprietário/SHA conclui a mídia sem duplicar efeitos nem alterar suas configurações
