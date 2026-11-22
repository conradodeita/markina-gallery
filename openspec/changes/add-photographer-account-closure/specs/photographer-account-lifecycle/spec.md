# Spec Delta

## Purpose

Gerenciar o encerramento voluntário da conta do fotógrafo sem interromper as galerias já publicadas nem perder pedidos, pagamentos ou obrigações em andamento. Distinguir o encerramento da suspensão e aplicar o tratamento de dados por categoria.

## ADDED Requirements

### Requirement: Solicitação autenticada de encerramento

O sistema SHALL aceitar solicitação explícita somente do fotógrafo autenticado no próprio tenant, explicar os efeitos antes da confirmação e registrar a transição com identificador único e instante UTC. Repetições da mesma solicitação MUST NOT criar novos encerramentos.

#### Scenario: Fotógrafo solicita encerramento
- **WHEN** o fotógrafo autenticado confirma o encerramento do próprio tenant
- **THEN** o sistema registra uma única solicitação e apresenta o estado `Encerrando`

#### Scenario: Solicitação de tenant alheio
- **WHEN** uma sessão tenta solicitar encerramento para outro tenant
- **THEN** o sistema recusa sem alterar o estado nem revelar dados do tenant alvo

### Requirement: Consulta e acompanhamento do encerramento

O fotógrafo autenticado SHALL consultar somente estado, saldo e pendências do próprio tenant. Antes de confirmar, a interface SHALL explicar as consequências e exigir aceite dos Termos vigentes, confirmação explícita e saldo atual. Saldo divergente ou Termos indisponíveis/desatualizados SHALL recusar a solicitação. Pendências SHALL usar linguagem operacional, sem códigos internos ou detalhes de infraestrutura.

#### Scenario: Fotógrafo confere estado e pendências
- **WHEN** o fotógrafo autenticado abre Configurações durante `open` ou `closing`
- **THEN** recebe o saldo atual e, durante `closing`, somente pendências pertencentes ao próprio tenant, em linguagem clara e sem detalhes internos de armazenamento

#### Scenario: Saldo ou Termos mudaram
- **WHEN** o saldo mudou ou a versão vigente dos Termos não foi aceita desde a consulta
- **THEN** o sistema não inicia o encerramento e pede que o fotógrafo atualize os dados e aceite os Termos vigentes

### Requirement: Operação durante o encerramento

Após a solicitação, o tenant SHALL bloquear novas galerias e uploads, mantendo acesso limitado para tratar obrigações existentes. Galerias já publicadas SHALL permanecer disponíveis aos clientes dentro dos prazos vigentes para concluir seleção e compra.

#### Scenario: Tentativa de iniciar novo trabalho
- **WHEN** fotógrafo em encerramento tenta criar galeria ou enviar fotos
- **THEN** o backend recusa a operação sem aceitar arquivos ou reservar créditos

#### Scenario: Cliente usa galeria já publicada
- **WHEN** cliente autorizado acessa uma galeria publicada ainda dentro do prazo vigente
- **THEN** pode concluir seleção e compra conforme as regras já exibidas para aquela galeria

### Requirement: Conclusão condicionada às obrigações

O sistema SHALL concluir o encerramento após o fim das janelas publicadas, a conclusão dos pedidos e obrigações e a verificação do arquivamento da mídia pesada elegível pelo fluxo existente por pasta. Fonte indisponível mantém `closing`. Carrinho abandonado não bloqueia após a política de arquivo frio. Saldo remanescente não bloqueia após confirmação explícita.

#### Scenario: Existe obrigação pendente
- **WHEN** a verificação encontra pedido, pagamento ou outra obrigação ainda aberta
- **THEN** a conta permanece em `closing` e informa ao fotógrafo que o encerramento aguarda conclusão

#### Scenario: Fotógrafo confirma encerramento com créditos não utilizados
- **WHEN** a carteira contém créditos comprados não utilizados e o fotógrafo confirma que deseja encerrar mesmo conhecendo o saldo remanescente
- **THEN** o saldo e seu histórico permanecem registrados como dados financeiros históricos, não há estorno manual e a conta pode chegar a `closed` quando as demais condições forem satisfeitas

#### Scenario: Há prazo de galeria vigente
- **WHEN** alguma galeria ou pasta publicada ainda está na janela de acesso ou finalização de compra informada ao cliente
- **THEN** a conta permanece em `closing` e essa janela continua conforme as regras já publicadas

#### Scenario: Carrinho abandonado após janela normal
- **WHEN** as janelas publicadas e de arquivo frio terminaram e não há pedido ou outra obrigação aberta, mas existe seleção/carrinho sem pedido
- **THEN** a seleção sozinha não bloqueia o encerramento indefinidamente e as referências seguem a política de arquivo frio

#### Scenario: Obrigações concluídas
- **WHEN** as janelas publicadas terminaram, não há pedidos ou obrigações pendentes, o fotógrafo confirmou o encerramento mesmo que reste crédito, e a mídia pesada elegível foi arquivada e verificada
- **THEN** o sistema finaliza o encerramento e registra `closed` com instante e evento de auditoria

### Requirement: Avisos enfileirados não atrasam o encerramento

Para `NotificationDelivery`, `WhatsAppDelivery` e outboxes de vínculo, reabertura e busca facial, avisos `queued` não impedem `closed` nem são processados com a conta fechada; entregas `processing` bloqueiam. Claims, leases e reconciliações SHALL serializar pelo lock do tenant. A projeção de pagamento SHALL refletir o estado real da entrega WhatsApp.

#### Scenario: Avisos enfileirados durante a conclusão
- **WHEN** existem avisos push ou WhatsApp `queued` e todas as demais condições de encerramento foram satisfeitas
- **THEN** a conta pode passar a `closed`, os avisos permanecem `queued` e nenhum provedor é chamado enquanto a conta estiver fechada

#### Scenario: Entrega já em processamento
- **WHEN** uma entrega push ou WhatsApp está `processing`
- **THEN** ela continua sendo uma pendência de encerramento até que o processamento seja resolvido

#### Scenario: Claim concorre com o encerramento
- **WHEN** um worker e a finalização disputam o claim de um aviso push/WhatsApp do tenant
- **THEN** o claim e o encerramento SHALL ser serializados pelo tenant; se o claim ocorrer primeiro, `processing` SHALL bloquear o encerramento; se o encerramento ocorrer primeiro, o worker SHALL NOT alterar a fila nem chamar o provedor

### Requirement: Arquivamento de pastas nunca liberadas durante encerramento

Durante `closing`, pastas comprovadamente nunca liberadas aos clientes SHALL poder ser arquivadas diretamente, sem iniciar prazo de acesso ou esperar trinta dias. O sistema MUST conferir pedidos, obrigações, jobs, reservas e integridade pelo fluxo existente antes de remover bytes locais. Ausência de evidência de liberação não prova, por si só, que uma pasta legada nunca foi liberada.

#### Scenario: Pasta nunca liberada sem obrigações
- **WHEN** uma pasta do tenant em `closing` nunca foi liberada e não tem obrigações ou processamento pendente
- **THEN** o sistema pode enfileirar o arquivamento imediato e só remover os bytes locais após transferência e verificação íntegra

#### Scenario: Pasta liberada ou histórico incerto
- **WHEN** a pasta já foi liberada ou não é possível demonstrar que nunca foi liberada
- **THEN** a exceção de arquivamento direto não é aplicada e os prazos e bloqueios existentes permanecem

### Requirement: Capa isolada no encerramento

Quando uma galeria tiver capa sem nenhuma pasta de fotos, o encerramento SHALL arquivar essa capa pelo mecanismo de arquivo frio existente e permitir sua recuperação junto da conta, sem taxa adicional. Essa unidade técnica MUST NOT ser apresentada ou cobrada como pasta de fotos. Havendo pastas de fotos, permanece a regra de incluir a capa somente com a última pasta ativa.

#### Scenario: Galeria com somente capa
- **WHEN** o tenant encerra uma conta com galeria que contém somente capa e não há obrigações pendentes
- **THEN** a capa é arquivada com integridade verificada e sua recuperação administrativa não debita créditos adicionais

### Requirement: Acesso bloqueado após encerramento

Depois de `closed`, o fotógrafo MUST perder o acesso por login e sessões existentes e MUST NOT reativar a própria conta. O `PlatformOwner` pode reabrir o acesso após recuperar e verificar a mídia, com auditoria. A recuperação não tem limite automático de tempo enquanto a mídia existir. Aos dez anos há revisão manual, sem exclusão automática. Após esse marco, reabrir também exige confirmação de identidade e dados atuais do fotógrafo.

#### Scenario: Login após encerramento
- **WHEN** o fotógrafo tenta autenticar após a conta tornar-se `closed`
- **THEN** o sistema recusa o acesso e sessões anteriores não autorizam operações

#### Scenario: Reativação pelo próprio tenant
- **WHEN** o fotógrafo tenta reabrir ou recriar a conta encerrada usando o mesmo tenant
- **THEN** o sistema mantém o estado `closed` e não restabelece acesso

#### Scenario: Reabertura pelo proprietário em até dez anos
- **WHEN** o `PlatformOwner` solicita a recuperação da mídia existente antes de completar dez anos desde `closed` e todas as operações são concluídas com verificação íntegra
- **THEN** o proprietário pode reabrir o tenant e o sistema restaura o acesso conforme as regras de autenticação vigentes, registrando a ação na auditoria

#### Scenario: Pull concluído não reabre a conta automaticamente
- **WHEN** todas as operações do lote de recuperação terminam com sucesso
- **THEN** a conta permanece `closed` até o `PlatformOwner` executar separadamente a ação autenticada e auditada de reabertura

#### Scenario: Reabertura não remove suspensão
- **WHEN** o proprietário reabre uma conta encerrada que também está `suspended`
- **THEN** o sistema altera somente o lifecycle para `open` e mantém a suspensão até uma ação própria de ativação

#### Scenario: Reabertura após dez anos
- **WHEN** a mídia existente é recuperada após completar dez anos desde `closed`
- **THEN** a conta permanece fechada até o fotógrafo enviar o CPF que corresponde à impressão protegida do próprio tenant e fornecer dados atuais; depois disso, o proprietário pode concluir uma reabertura auditada conforme as regras de autenticação vigentes

#### Scenario: CPF não corresponde ao registro protegido
- **WHEN** o CPF enviado para reabertura após dez anos não corresponde à impressão protegida do tenant
- **THEN** a conta permanece fechada e o sistema não revela dados de outro tenant nem confirma a existência de uma conta associada ao CPF informado

#### Scenario: Dados atuais verificados sem autoativação
- **WHEN** o fotógrafo comprova o CPF no host canônico do próprio tenant e confirma o e-mail atual com código de uso único
- **THEN** o sistema atualiza os dados atuais, registra a verificação vinculada ao ciclo encerrado e mantém a conta fechada, sem criar sessão ou autenticar o fotógrafo

#### Scenario: Código inválido, expirado ou repetido
- **WHEN** um código de verificação excede cinco tentativas, expirou após dez minutos ou já foi consumido
- **THEN** o sistema recusa com resposta neutra, impede replay e não altera e-mail, nome, lifecycle ou acesso

#### Scenario: Host de outro tenant
- **WHEN** uma solicitação de identidade chega por host que não é o host canônico do tenant encerrado
- **THEN** o sistema não inicia verificação para o tenant, não revela sua existência e apresenta a mesma resposta pública neutra
- **AND** uma confirmação nesse host, inclusive se ele resolver outro tenant encerrado, não altera estado, tentativas ou material de um desafio do tenant original

### Requirement: Tratamento do perfil operacional após encerramento

Nome e e-mail mínimos do fotógrafo SHALL permanecer no PostgreSQL sob acesso restrito para permitir restauração pelo `PlatformOwner`. O décimo aniversário de `closed_at` SHALL iniciar revisão manual, sem exclusão automática. A revisão pode reduzir cópias redundantes que não sejam necessárias à restauração. Outras categorias SHALL seguir suas políticas próprias.

#### Scenario: Encerramento finalizado
- **WHEN** a conta passa a `closed` após resolver as obrigações
- **THEN** nome e e-mail mínimos ficam disponíveis sob acesso restrito para restauração pelo proprietário; os demais dados seguem a política de retenção aplicável à sua categoria e o fotógrafo não ganha acesso operacional

#### Scenario: Proprietário reduz CPF e endereço após dez anos
- **WHEN** o proprietário reautenticado confirma explicitamente a redução do perfil de uma conta encerrada cujo décimo aniversário venceu e cujas obrigações permitem a revisão
- **THEN** o sistema remove somente CPF e endereço cifrados do perfil, preserva nome/e-mail mínimos, impressão protegida versionada e registros financeiros/aceites, e registra a ação sem dados pessoais

#### Scenario: Conta reaberta após redução do perfil
- **WHEN** o proprietário reabre uma conta cujo CPF e endereço cifrados foram removidos na revisão
- **THEN** a compra de créditos permanece bloqueada até o fotógrafo preencher novamente CPF e endereço pelo cadastro autenticado existente

#### Scenario: Recuperação da conta após a retenção de nome e e-mail
- **WHEN** o proprietário recupera mídia após dez anos e solicita reabrir a conta
- **THEN** o acesso continua bloqueado até o CPF do fotógrafo corresponder à impressão protegida do mesmo tenant, o e-mail atual estar verificado e os dados atuais serem fornecidos; a revisão não apaga automaticamente o nome/e-mail mínimos retidos

### Requirement: Impressão protegida de CPF para recuperação tardia

O sistema SHALL manter uma impressão HMAC não reversível do CPF, ligada ao perfil do mesmo tenant enquanto houver mídia recuperável. MUST NOT expor a impressão nem registrar o CPF bruto em logs. Após a remoção explícita e auditada de toda a mídia recuperável do tenant, SHALL remover a impressão protegida.

#### Scenario: Conferência de CPF após dez anos
- **WHEN** o fotógrafo fornece CPF para reabrir a conta após dez anos
- **THEN** o backend compara o CPF ao registro protegido do mesmo tenant, sem revelar o CPF ou a impressão ao proprietário

#### Scenario: Mídia removida definitivamente
- **WHEN** toda a mídia arquivada do tenant é removida pelo fluxo explícito e auditado
- **THEN** o sistema remove também a impressão protegida de CPF usada somente para recuperação tardia

### Requirement: Versão da chave do verificador de CPF

Cada impressão SHALL identificar a versão da chave HMAC usada. Segredos permanecem fora do PostgreSQL, frontend e mídia; a chave anterior MUST NOT ser removida enquanto houver registros que dependam dela. Versão ausente falha fechada e a unicidade global de CPF continua válida entre versões.

#### Scenario: Rotação mantém chave anterior disponível
- **WHEN** a chave ativa muda e há perfis ligados à versão anterior
- **THEN** o sistema continua conferindo esses perfis com a versão registrada, verifica unicidade entre versões e recusa operação se a versão anterior não estiver disponível

#### Scenario: Versão ou chave indisponível
- **WHEN** um perfil exige uma versão de chave não configurada
- **THEN** a comparação ou gravação falha fechada com resposta genérica, sem CPF, impressão ou detalhe do tenant

### Requirement: Mídia em arquivo frio após encerramento

O encerramento da conta MUST NOT iniciar expurgo automático da mídia no arquivo frio. A exclusão dessa mídia SHALL depender de solicitação explícita e do fluxo de exclusão auditado aplicável.

#### Scenario: Conta encerrada com mídia arquivada
- **WHEN** a conta passa a `closed` e ainda há mídia no arquivo frio
- **THEN** o sistema mantém a mídia conforme a política vigente e não inicia exclusão por causa do encerramento

### Requirement: Barreira de novas operações faciais no encerramento

Desde `closing`, novas buscas e mudanças/reconciliações automáticas de política facial SHALL ser bloqueadas por tenant; a criação de buscas MUST serializar com a transição pelo lock do tenant. Jobs já iniciados podem concluir e enfileirar continuação até o marcador de limpeza. Após o marcador, novos claims e gravações em fila SHALL ser bloqueados. A limpeza desativa políticas sem apagar configuração ou prova, e aguarda jobs com lease válido.

#### Scenario: Busca ou política durante encerramento pendente
- **WHEN** uma nova busca, ativação de política ou reconciliação automática é solicitada com lifecycle `closing`, antes do marcador biométrico
- **THEN** nenhuma busca, política ou backfill novo é admitido; operações já iniciadas continuam sujeitas ao prazo de lease e à limpeza retomável

#### Scenario: Novos trabalhos após a barreira
- **WHEN** uma busca, enfileiramento ou claim é solicitado após o marcador
- **THEN** a operação é recusada sem afetar outros tenants

#### Scenario: Job com lease ativo
- **WHEN** a limpeza encontra job facial com lease válido
- **THEN** aguarda seu término e mantém os dados necessários até o lease terminar

### Requirement: Prova mínima de consentimento facial no encerramento

Antes de apagar cada request, o sistema SHALL copiar seus dados mínimos de autorização para uma prova tenant-scoped, versionada e idempotente. A prova MUST NOT conter imagem, região, embedding, representação livre ou resultado facial e não terá expurgo automático nesta mudança.

#### Scenario: Request removido com prova preservada
- **WHEN** um request facial operacional é removido no encerramento
- **THEN** sua prova mínima permanece uma única vez, sem conteúdo biométrico ou resultado

### Requirement: Limpeza biométrica antes do estado fechado

Antes de `closed`, o sistema SHALL remover embeddings, requests/resultados, candidatos, snapshots, jobs, referências faciais locais e payloads de notificação. Jobs enfileirados ou com lease expirado são cancelados. O arquivo frio e o pacote de reabertura MUST NOT receber esses dados. Falha mantém `closing` e permite retry seguro.

#### Scenario: Encerramento conclui com biometria limpa
- **WHEN** todas as obrigações e arquivos de mídia estão resolvidos e a limpeza facial foi confirmada
- **THEN** a conta pode passar a `closed`, preservando somente prova mínima versionada de consentimento e a trilha de auditoria sem imagem, embedding ou resultado facial

#### Scenario: Falha de remoção de artefato facial
- **WHEN** o sistema não consegue confirmar a remoção de referência ou dado facial operacional
- **THEN** a conta permanece em `closing`, a limpeza pode ser repetida sem duplicar efeitos e a interface apresenta apenas uma pendência operacional

### Requirement: Reabertura sem restauração de biometria

Reabrir um tenant MUST NOT restaurar índices apagados. Novo processamento SHALL seguir a política vigente e a autorização aplicável ao caminho; consentimento de upload anterior MUST NOT ser reutilizado. A busca por região segue o fluxo vigente sem diálogo adicional.

#### Scenario: Reabertura de tenant encerrado
- **WHEN** o proprietário restaura a mídia e reabre a conta
- **THEN** os índices faciais apagados não são restaurados; novo processamento exige a política vigente e a autorização aplicável ao caminho, sem reutilizar consentimento de upload de uma busca anterior; a busca por região segue o fluxo vigente sem diálogo adicional

### Requirement: Separação entre registros do banco e mídia pesada

O encerramento SHALL manter registros leves, compras, transações e histórico do Tenant no PostgreSQL sob suas regras próprias. Mídia de grande volume SHALL reutilizar o arquivo frio existente por pasta, sem criar cópia paralela do banco. O proprietário SHALL iniciar revisão manual ao completar dez anos do encerramento. Esse marco MUST NOT disparar expurgo automático; a mídia continua recuperável enquanto não for removida por decisão explícita e auditada.

#### Scenario: Mídia pesada arquivada
- **WHEN** arquivos de mídia de pasta do tenant se tornam elegíveis segundo a política existente de arquivo frio
- **THEN** a mídia segue o fluxo tenant-scoped por pasta; compras, transações e histórico permanecem no PostgreSQL

#### Scenario: Mídia pendente de arquivamento
- **WHEN** alguma mídia que precisa sair do servidor ainda não foi transferida ou verificada
- **THEN** o encerramento permanece em `closing`, as cópias locais não são removidas e a conta não é marcada `closed`

#### Scenario: Acesso à mídia fria
- **WHEN** mídia do tenant está armazenada no arquivo frio
- **THEN** permanece inacessível ao tenant e aos clientes até a recuperação verificada, sem link público nem credencial de armazenamento exposta

#### Scenario: Marco de dez anos sem exclusão explícita
- **WHEN** dez anos se completam desde `closed` e o proprietário ainda não concluiu uma exclusão explícita e auditada
- **THEN** a mídia permanece no arquivo frio e pode ser recuperada; o sistema apenas sinaliza revisão manual, sem expurgar ou bloquear a restauração

### Requirement: Console privado acompanha o ciclo de encerramento

O console SHALL exibir lifecycle, disponibilidade, ciclo atual, dias completos e revisão UTC de dez anos ao `PlatformOwner`. O marco usa anos de calendário (29/02 → 28/02) e MUST NOT expurgar mídia ou impedir recuperação. Recuperação e reabertura SHALL ser ações separadas, reautenticadas e auditadas; reabrir exige restauração verificada e os gates de identidade. Respostas e interface MUST NOT expor CPF, impressão protegida ou códigos técnicos.

#### Scenario: Ciclo atual e ciclo anterior
- **WHEN** uma conta atualmente encerrada tem um ciclo anterior reaberto e um novo ciclo encerrado
- **THEN** a idade e o prazo de revisão usam somente o `closed_at` do ciclo atual

#### Scenario: Revisão no aniversário UTC
- **WHEN** o instante observado atinge o aniversário UTC de dez anos, inclusive o corte de 29/02 para 28/02
- **THEN** o console sinaliza revisão manual sem iniciar exclusão nem bloquear o pedido de recuperação

#### Scenario: Recuperação e reabertura em ações distintas
- **WHEN** o proprietário pede recuperação ou consulta seus lotes
- **THEN** o console mostra estados por lote/operação; o pull concluído mantém lifecycle `closed` até ação separada de reabertura que satisfaz os gates

#### Scenario: Conta encerrada não pode ser ativada pelo controle de disponibilidade
- **WHEN** o proprietário usa o controle comum de suspensão/ativação em uma conta `closed`
- **THEN** a API recusa e preserva lifecycle e disponibilidade, exigindo o fluxo próprio de reabertura
