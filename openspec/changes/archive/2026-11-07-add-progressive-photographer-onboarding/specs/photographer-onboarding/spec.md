# Spec Delta

## ADDED Requirements

### Requirement: Ingresso exploratório após verificação e senha

O sistema SHALL ativar conta exploratória de fotógrafo após verificar e-mail e concluir senha válida, sem exigir TOTP nem aceite dos Termos operacionais nessa etapa. O provisionamento MUST ser atômico e idempotente, criar tenant finito sem saldo artificial e vínculo administrativo próprio, sem grants globais. Esta regra substitui o requisito de TOTP obrigatório na ativação de `add-photographer-signup-portal`.

#### Scenario: Ingresso leve
- **WHEN** candidato valida OTP de e-mail e define senha válida na sessão restrita
- **THEN** recebe conta e acesso administrativo somente ao próprio tenant para exploração, sem habilitar compra ou upload

#### Scenario: Replay ou falha parcial
- **WHEN** conclusão é repetida ou falha antes do commit
- **THEN** não há segundo tenant, vínculo ou sessão parcial

### Requirement: Aceite operacional progressivo antes da compra

O aceite de Termos operacionais SHALL ocorrer no cadastro completo, antes da primeira compra de créditos e upload, sem bloquear exploração. O backend MUST exigir versão vigente e ação afirmativa, preservar protocolo append-only com identidades das partes, texto integral/hash, instante UTC e evidência da ação. Esta regra substitui o aceite antes de ativar previsto na change anterior.

#### Scenario: Falta aceite
- **WHEN** fotógrafo tenta comprar ou enviar foto sem aceite válido
- **THEN** a ação é recusada e o painel aponta a etapa pendente em Configurações

#### Scenario: Documento real indisponível
- **WHEN** faltam texto aprovado ou identificação do provedor fora de prova sintética local
- **THEN** aceite de teste não libera compra nem upload real

### Requirement: Exploração e progresso de cadastro

O fotógrafo com e-mail verificado SHALL navegar no painel do próprio tenant sem dados operacionais completos. Configurações SHALL mostrar etapas concluídas, pendentes e opcionais e o servidor SHALL devolver os mesmos estados por tenant autenticado. Gates SHALL ocorrer na ação que requer requisitos adicionais e preservar retorno interno seguro e dados não sensíveis já preenchidos.

#### Scenario: Fotógrafo apenas exploratório
- **WHEN** fotógrafo abre painel, créditos ou configurações sem CPF/PIX/WhatsApp
- **THEN** vê as funcionalidades e pendências do próprio tenant, sem criar Order ou upload

### Requirement: Perfil operacional e checkout pré-preenchido

Cadastro operacional de pessoa física SHALL exigir a identidade informada no ingresso verificado, CPF válido, endereço do pagador e aceite vigente. Configurações MUST solicitar CPF e endereço, sem repetir nome/e-mail. Telefone e complemento SHALL ser opcionais.

#### Scenario: Fotógrafo completa o perfil
- **WHEN** CPF e endereço válidos são salvos pelo fotógrafo autenticado com nome já registrado no ingresso
- **THEN** a etapa de perfil fica concluída e o checkout usa esses dados como preenchimento inicial

#### Scenario: Endereço ainda não informado
- **WHEN** fotógrafo salva CPF sem os campos obrigatórios de endereço
- **THEN** o perfil permanece incompleto e a compra de créditos é bloqueada com indicação da pendência em Configurações

#### Scenario: Endereço estruturado para checkout
- **WHEN** fotógrafo salva endereço no perfil
- **THEN** o sistema exige CEP, logradouro, número ou S/N, bairro, cidade e UF e pode aceitar complemento vazio

### Requirement: Identidade pré-preenchida na compra de créditos

O checkout SHALL pré-preencher nome, e-mail verificado, CPF e endereço do cadastro autenticado; a Order MUST enviar os dados válidos do pagador efetivo em `payer.address` sem mudar o perfil contratual.

#### Scenario: Dados do titular
- **WHEN** fotógrafo inicia a compra de créditos
- **THEN** os campos do checkout são preenchidos com os dados do perfil para evitar redigitação

#### Scenario: Pagador diferente
- **WHEN** fotógrafo ajusta dados do pagador no checkout
- **THEN** apenas a transação usa os valores editados e o perfil continua inalterado

#### Scenario: Endereço conforme dados de pagador
- **WHEN** fotógrafo completa o endereço do cadastro
- **THEN** o checkout pré-preenche CEP, logradouro, número, bairro, cidade e UF do pagador e permite ajustes apenas para a transação em curso

### Requirement: Unicidade global do CPF operacional

Um CPF SHALL pertencer a um único tenant no cadastro operacional, mesmo quando outro e-mail for usado. A recusa de duplicidade MUST NOT revelar identidade, e-mail ou dados do tenant que já o utiliza.

#### Scenario: Mesmo CPF em outro tenant
- **WHEN** fotógrafo tenta completar outro tenant com CPF já registrado
- **THEN** o cadastro operacional é recusado sem alterar o perfil existente ou permitir compra/upload pelo cadastro incompleto

### Requirement: Resumo de progresso recolhível

Configurações SHALL apresentar etapas obrigatórias e opcionais em itens recolhíveis, identificando visualmente cada item obrigatório concluído com um check e seu estado textual. Cada item MUST manter seu estado visível enquanto o conteúdo estiver recolhido; itens opcionais MUST ser diferenciados e não aumentar o total de requisitos obrigatórios.

#### Scenario: Etapas recolhidas
- **WHEN** fotógrafo abre Configurações
- **THEN** vê o resumo de progresso, cada etapa obrigatória com estado e check quando concluída, e pode expandir individualmente os detalhes e ações da etapa

#### Scenario: Perfil já informado no ingresso
- **WHEN** fotógrafo completa seu perfil operacional
- **THEN** informa apenas o CPF pendente e o sistema reutiliza nome e e-mail verificados do ingresso

### Requirement: Pré-requisitos operacionais de upload


Além da carteira e das restrições financeiras existentes, upload de fotógrafo SaaS SHALL exigir cadastro completo, aceite vigente, PIX recebedor configurado no próprio tenant e instância WhatsApp própria do fotógrafo configurada e funcional para notificar os seus clientes. Configuração de outro tenant ou apenas número informado MUST NOT satisfazer o gate. Mercado Pago do fotógrafo SHALL permanecer opcional. O frontend SHALL nomear o canal somente “WhatsApp”.

#### Scenario: Configuração pendente
- **WHEN** algum pré-requisito está pendente ou indisponível
- **THEN** nenhuma rota de upload ou reserva aceita a operação e Configurações indica a pendência correta sem bloquear navegação

#### Scenario: WhatsApp não conectado
- **WHEN** fotógrafo possui crédito mas não conecta WhatsApp
- **THEN** upload e nova reserva permanecem bloqueados até configurar o canal próprio
