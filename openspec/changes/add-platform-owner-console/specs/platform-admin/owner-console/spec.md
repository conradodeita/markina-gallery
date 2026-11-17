# platform-admin/owner-console Specification

## ADDED Requirements

### Requirement: Autorização explícita do proprietário

O sistema SHALL autorizar a área global por identidade administrativa persistida e permissão explícita. E-mail isolado MUST NOT conceder acesso. Grants técnicos do monitor e da instalação MUST NOT conceder acesso comercial ou mutação de tenant.

#### Scenario: Administrador sem grant global

- **WHEN** um fotógrafo ou operador técnico solicita a área global
- **THEN** o servidor recusa sem revelar dados de tenants

#### Scenario: Leitura com identidade permanente e revogação durante consulta

- **WHEN** o proprietário com sessão e vínculo ativos consulta o console
- **THEN** a propriedade persistida autoriza a leitura, independentemente dos grants técnicos, e a autorização é revalidada antes da resposta privada não cacheável
- **AND** perda de propriedade, vínculo ou sessão impede a entrega e limpa os dados exibidos na próxima revalidação da interface

### Requirement: Diretório global mínimo

O proprietário autorizado SHALL consultar tenants e informações mínimas/agregadas necessárias. A consulta MUST NOT expor fotos, biometria, clientes ou detalhes financeiros desnecessários.

#### Scenario: Tenant em estado suspenso

- **WHEN** o proprietário consulta o diretório
- **THEN** vê o estado ativo/suspenso e indicadores autorizados do tenant sem abrir seu acervo

#### Scenario: Consulta explícita e identidade ausente

- **WHEN** o proprietário abre o diretório sem filtro ou escolhe Todos, ordem alfabética, recentes ou pesquisa por e-mail
- **THEN** o estado inicial fica vazio e a consulta explícita retorna no máximo 20 tenants por página, incluindo contas suspensas ou sem carteira
- **AND** conta sem administrador ativo ou com identidade ambígua aparece com e-mail indisponível, sem inferir nome nem expor outro cadastro

#### Scenario: Resumo mínimo de tenant selecionado

- **WHEN** o proprietário seleciona um UUID do diretório
- **THEN** recebe somente identificação básica, estado, host e contagens de galerias/fotos, com origem e instante da consulta
- **AND** fotos, biometria, clientes, segredos, pedidos e caminhos de arquivos não integram a resposta

#### Scenario: Nome informado pelo cadastro automático

- **WHEN** o tenant possui nome fornecido pelo fotógrafo na ativação do website
- **THEN** o diretório autorizado permite pesquisar por nome ou e-mail e exibe somente essa identidade mínima
- **AND** contas legadas sem nome continuam consultáveis por e-mail sem inferência ou backfill fictício

### Requirement: Criação e suspensão preservam dados

Criação e suspensão SHALL exigir ação explicitamente autorizada e auditoria. Suspensão MUST NOT apagar registros, histórico comercial ou financeiro; ativação não reescreve nem publica dados anteriores.

#### Scenario: Suspensão de tenant

- **WHEN** o proprietário suspende um tenant
- **THEN** operações futuras respeitam o estado e os dados/history permanecem preservados

#### Scenario: Pagamento iniciado antes da suspensão

- **WHEN** callback autenticado ou job financeiro concilia uma obrigação já iniciada de tenant suspenso
- **THEN** o backend preserva a confirmação, idempotência e histórico financeiro, sem habilitar acesso, upload ou nova compra para o tenant
- **AND** mensagens e jobs não financeiros continuam pausados enquanto suspenso

#### Scenario: Mutação sensível e replay

- **WHEN** proprietário solicita mudança de estado com senha/TOTP válidos, estado esperado e UUID da intenção
- **THEN** mudança e auditoria são transacionais e o replay da mesma intenção não altera histórico nem reutiliza outro passo TOTP
- **AND** alvo proprietário, precondição divergente, identidade não autorizada ou credenciais inválidas são recusados sem mutação de tenant

#### Scenario: Concessão ou revogação de créditos

- **WHEN** o proprietário concede ou revoga créditos pela área de créditos usando senha atual, TOTP válido, tenant, operação, quantidade, referência e UUID de intenção
- **THEN** o servidor aplica o mesmo gate de reautenticação sensível do console, limita tentativas, revalida a sessão e a identidade `PlatformOwner` imediatamente antes do commit e grava o ledger e a auditoria na mesma transação
- **AND** o replay da mesma intenção retorna o resultado anterior sem consumir outro TOTP, enquanto reutilizar o UUID para outro tenant, operação ou conteúdo é recusado sem alteração financeira

#### Scenario: Alteração de pacotes ou revisão financeira

- **WHEN** o proprietário cria/altera um pacote de créditos ou libera/restringe uma compra contestada
- **THEN** a mutação exige senha atual, TOTP one-time, limite de tentativas, UUID de intenção e revalidação da mesma sessão/propriedade antes do commit
- **AND** a alteração e a auditoria administrativa são atômicas; replay da mesma intenção retorna o resultado anterior sem novo efeito e reutilização do UUID para conteúdo diferente é recusada
- **AND** justificativa e configuração comercial não são copiadas em texto livre para o log administrativo

#### Scenario: Corpo financeiro inválido com credenciais

- **WHEN** uma solicitação de concessão, revogação, criação/edição de pacote ou revisão financeira contém credenciais ou campos inválidos
- **THEN** o erro de validação é privado, não cacheável e sanitizado, sem devolver senha, TOTP ou o corpo recebido

#### Scenario: Sessão ou propriedade muda antes do commit

- **WHEN** a sessão do proprietário é revogada, trocada, ou sua propriedade/vínculo deixa de ser válido depois da autorização inicial e antes do commit de uma mutação sensível
- **THEN** o servidor revalida a mesma sessão, ator e tenant imediatamente antes do commit, reverte a transação e recusa a operação se qualquer dado de autorização tiver mudado
- **AND** nenhuma alteração de estado ou efeito enfileirado da mutação é persistido

#### Scenario: Sessão revogada ao gravar Termos

- **WHEN** a sessão muda após autorizar o salvamento do rascunho ou a publicação de Termos e antes do commit
- **THEN** o servidor recusa a operação e preserva rascunho anterior, versões publicadas, auditoria e último passo TOTP, sem persistir a tentativa

#### Scenario: Sessão revogada durante a resposta financeira

- **WHEN** a sessão ou propriedade muda durante a consulta que monta a resposta de uma concessão, revogação, alteração de pacote ou revisão financeira, inclusive em replay
- **THEN** o servidor revalida a mesma sessão e identidade antes de devolver o resultado privado e recusa a resposta se a autorização mudou
- **AND** uma operação já confirmada conserva seu histórico e idempotência, sem reaplicar a mutação nem consumir outro TOTP

#### Scenario: Tenant estável e feedback de mutação financeira

- **WHEN** uma concessão, revogação ou decisão de revisão financeira aguarda resposta, ou o proprietário troca o tenant antes de iniciar outra concessão/revogação
- **THEN** os controles que selecionam tenant e os campos da mutação pendente permanecem bloqueados até a resposta; ao mudar a busca/tenant, os campos de quantidade, referência, senha e TOTP da carteira são limpos
- **AND** erro ou confirmação de revisão financeira aparece junto à fila, mesmo sem uma carteira selecionada

#### Scenario: Ingresso automatizado no website

- **WHEN** fotógrafo ingressa pelo website pickyourpic.com.br
- **THEN** onboarding e ativação seguem a change do portal após verificar e-mail e MFA, sem aprovação manual, convite do console ou compartilhamento de senha/TOTP com o proprietário

### Requirement: Estado operacional com proveniência

Cada indicador de integração, armazenamento, jobs, backup e arquivamento SHALL informar fonte, escopo, instante e disponibilidade. Fonte ausente, desatualizada ou indisponível MUST NOT ser apresentada como íntegra/saudável.

#### Scenario: Fonte indisponível ou desatualizada

- **WHEN** o proprietário consulta um indicador cuja fonte está ausente, indisponível ou além do limite de atualização definido
- **THEN** a interface mostra a disponibilidade e o instante observável, identifica a fonte conhecida e não apresenta o estado como íntegro

#### Scenario: Autorização Google Drive registrada sem consulta externa

- **WHEN** o proprietário consulta fontes e existe registro de conexão Google Drive
- **THEN** o console apresenta somente o estado de autorização registrado, fonte, escopo e instante, mais a última quota já persistida quando disponível
- **AND** autorização registrada MUST NOT ser apresentada como disponibilidade atual/saúde do Drive
- **AND** a leitura do console MUST NOT chamar a API Google

#### Scenario: Conexão Google Drive ausente, revogada ou sem quota observada

- **WHEN** não há conexão persistida, a conexão está revogada/requer reautorização, ou não há observação de quota
- **THEN** o estado de conexão ou quota permanece desconhecido/indisponível conforme a evidência, sem inferir capacidade ou saúde

### Requirement: Auditoria administrativa global

Cada ação relevante SHALL registrar ator, tenant relacionado quando aplicável, ação, objeto, data, resultado e origem quando disponível. Logs MUST NOT conter segredos ou dados sensíveis desnecessários.

#### Scenario: Falha na operação

- **WHEN** uma ação autorizada falha ou é recusada
- **THEN** o resultado sanitizado é auditado sem expor credencial, token, foto ou PII desnecessária
