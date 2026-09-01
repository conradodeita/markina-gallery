## Purpose

Definir a entrega durável e segura de e-mails transacionais da Markina Gallery sem acoplar autenticação ao fornecedor SMTP nem expor links, tokens ou credenciais sensíveis.

## ADDED Requirements

### Requirement: Entrega transacional assíncrona

O sistema SHALL registrar cada e-mail transacional em caixa de saída durável e SHALL processá-lo fora do ciclo HTTP por um `EmailProvider` substituível. A aceitação da solicitação HTTP SHALL NOT depender da disponibilidade momentânea do SMTP.

#### Scenario: E-mail de recuperação é solicitado

- **WHEN** um fluxo autorizado solicita o envio de link de recuperação, verificação ou aviso
- **THEN** o sistema persiste uma entrega idempotente, responde sem aguardar rede externa e disponibiliza o item ao worker

#### Scenario: Repetição da mesma intenção

- **WHEN** a mesma finalidade e o mesmo objeto de origem são enfileirados novamente com a mesma chave idempotente
- **THEN** o sistema reutiliza a entrega existente e não envia mensagens duplicadas

#### Scenario: SMTP temporariamente indisponível

- **WHEN** o provider informa falha transitória antes de aceitar a mensagem
- **THEN** o sistema registra erro sanitizado e agenda retentativa limitada com atraso progressivo

### Requirement: Provedores sandbox e SMTP isolados

O sistema SHALL oferecer provider sandbox sem efeito externo e provider SMTP transacional configurado somente por segredos do servidor. Host, porta, autenticação, remetente e política TLS SHALL NOT ser aceitos do navegador, persistidos em tabela comum ou expostos por API pública.

#### Scenario: Ambiente sem ativação explícita do SMTP

- **WHEN** o provider real não está habilitado pela configuração segura do ambiente
- **THEN** o sistema usa o sandbox, não abre conexão externa e não escreve link, OTP ou corpo sensível em logs

#### Scenario: SMTP real habilitado

- **WHEN** o ambiente possui configuração completa, remetente autorizado e TLS válido
- **THEN** o worker entrega pelo provider SMTP e registra somente identificador externo, estado, tentativa e diagnóstico sanitizado

#### Scenario: Configuração real incompleta ou insegura

- **WHEN** faltam credenciais, remetente, TLS obrigatório ou origem pública permitida para compor links
- **THEN** o canal permanece indisponível em fail closed e a pendência operacional é exibida sem revelar valores secretos

### Requirement: Proteção dos destinatários e links sensíveis

O sistema SHALL manter destinatário e conteúdo necessários à entrega protegidos durante a fila, SHALL armazenar tokens de autenticação somente cifrados no payload efêmero e como hash na fonte de validação e SHALL eliminar o payload recuperável após estado terminal. Links SHALL usar origem HTTPS explicitamente permitida pelo servidor.

#### Scenario: Entrega sensível aguardando worker

- **WHEN** uma mensagem com link de uso único está pendente
- **THEN** a caixa de saída mantém payload autenticadamente cifrado e impressão irreversível do destinatário, sem token bruto em coluna consultável, API ou log

#### Scenario: Entrega aceita, expirada ou definitivamente falha

- **WHEN** a entrega alcança estado terminal
- **THEN** o sistema apaga o payload cifrado recuperável e preserva somente metadados mínimos de auditoria, correlação e diagnóstico

#### Scenario: Origem do link não autorizada

- **WHEN** a configuração tenta gerar link fora da origem HTTPS aprovada para o ambiente
- **THEN** o sistema não enfileira conteúdo sensível e registra uma pendência operacional sanitizada

### Requirement: Estado observável e retentativa segura

O sistema SHALL distinguir pelo menos os estados `queued`, `processing`, `accepted`, `failed` e `expired`, controlar tentativas de forma atômica e impedir que uma entrega vencida seja enviada. Timeout após resultado ambíguo SHALL NOT causar reenvio cego de link de autenticação.

#### Scenario: Worker aceita a entrega

- **WHEN** o provider confirma aceitação da mensagem ainda válida
- **THEN** a entrega avança para `accepted`, registra o horário e elimina o payload sensível quando não for mais necessário

#### Scenario: Prazo termina antes do envio

- **WHEN** o link associado ou a entrega expira antes da tentativa
- **THEN** o worker marca a entrega como `expired`, elimina o payload sensível e não contata o provider

#### Scenario: Resultado de envio é ambíguo

- **WHEN** ocorre timeout ou interrupção depois de a mensagem poder ter sido aceita
- **THEN** o sistema interrompe retentativa automática cega, registra estado seguro para reconciliação e não cria outro token válido para contornar a incerteza

### Requirement: Prontidão operacional do e-mail real

O uso de SMTP real em homologação ou produção SHALL exigir configuração própria do ambiente, domínio/remetente autorizados e evidência operacional de SPF, DKIM e DMARC, sem compartilhar credenciais entre ambientes.

#### Scenario: Ativação do canal real

- **WHEN** o operador pretende habilitar e-mails externos em um ambiente
- **THEN** o inventário identifica provider, origem HTTPS, remetente, isolamento de segredos, DNS de autenticação, healthcheck e rollback antes da autorização de deploy

#### Scenario: Requisitos de domínio não comprovados

- **WHEN** SPF, DKIM, DMARC ou o remetente do ambiente não estão validados
- **THEN** os fluxos locais permanecem testáveis em sandbox, mas o canal real não é declarado pronto para uso humano
