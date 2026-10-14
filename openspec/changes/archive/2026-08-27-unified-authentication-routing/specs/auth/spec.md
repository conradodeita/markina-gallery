## Purpose

Definir a autenticação unificada da Markina Gallery e a separação segura entre o fotógrafo administrador e clientes/responsáveis.

## ADDED Requirements

### Requirement: Tela única de entrada

O sistema SHALL disponibilizar uma única tela/rota de entrada para os contextos `Cliente` e `Fotógrafo`, com escolha explícita do contexto e campos correspondentes na mesma experiência visual.

#### Scenario: Seleção do contexto cliente

- **WHEN** o visitante escolhe `Cliente`
- **THEN** a tela apresenta nome completo e telefone, sem solicitar senha administrativa

#### Scenario: Seleção do contexto fotógrafo

- **WHEN** o visitante escolhe `Fotógrafo`
- **THEN** a tela apresenta e-mail e senha, sem solicitar nome de pessoa fotografada

### Requirement: OTP de cliente por WhatsApp

O sistema SHALL autenticar cliente/responsável mediante nome completo, telefone normalizado em E.164 e OTP de uso único enviado pelo adaptador WhatsApp.

#### Scenario: Cliente solicita código

- **WHEN** o cliente informa dados válidos e solicita entrada
- **THEN** o sistema cria desafio OTP com expiração curta, envia o código pelo WhatsApp e exibe a etapa de validação sem revelar se o telefone está cadastrado

#### Scenario: Cliente valida código

- **WHEN** o cliente informa o OTP correto dentro do prazo
- **THEN** o sistema invalida o desafio, cria sessão com papel `client` e encaminha o cliente conforme suas galerias autorizadas

#### Scenario: OTP inválido, usado ou expirado

- **WHEN** o cliente informa código inválido, já usado ou expirado
- **THEN** o sistema rejeita a autenticação, registra a tentativa, mantém resposta neutra e aplica rate limit

### Requirement: Autenticação forte do fotógrafo

O sistema SHALL autenticar o fotógrafo mediante e-mail verificado, senha válida e código TOTP válido de segundo fator.

#### Scenario: Senha válida exige TOTP

- **WHEN** o fotógrafo informa e-mail e senha corretos
- **THEN** o sistema solicita o código TOTP e não cria sessão administrativa antes da validação do segundo fator

#### Scenario: TOTP válido

- **WHEN** o fotógrafo informa TOTP válido dentro da janela aceita
- **THEN** o sistema cria sessão com papel `admin` e redireciona para a área administrativa

#### Scenario: Falha de senha ou TOTP

- **WHEN** a senha ou o TOTP são inválidos
- **THEN** o sistema rejeita o acesso, registra a tentativa, aplica rate limit e não revela qual fator falhou de maneira enumerável

### Requirement: Roteamento por papel e autorização

O backend SHALL determinar o destino e autorizar cada rota usando o papel e as relações persistidas da sessão, nunca somente dados enviados pelo frontend.

#### Scenario: Administrador acessa rota administrativa

- **WHEN** uma sessão `admin` acessa `/admin`
- **THEN** o sistema permite a entrada na área administrativa

#### Scenario: Cliente acessa galeria única

- **WHEN** uma sessão `client` possui uma única galeria autorizada
- **THEN** o sistema redireciona o cliente diretamente para essa galeria

#### Scenario: Cliente possui várias galerias

- **WHEN** uma sessão `client` possui duas ou mais galerias autorizadas
- **THEN** o sistema redireciona o cliente para sua biblioteca para escolher a galeria

#### Scenario: Papel incompatível

- **WHEN** uma sessão `client` tenta acessar `/admin` ou uma galeria sem autorização
- **THEN** o sistema responde com acesso negado sem revelar a existência do recurso e registra o evento
