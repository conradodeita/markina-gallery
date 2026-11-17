# Spec Delta

## MODIFIED Requirements

### Requirement: Segredos fora do Git

Segredos e chaves de API SHALL existir somente em configuração não versionada ou store seguro do servidor, com acesso restrito. O repositório SHALL manter `.env*` ignorado com exceção de `.env.example`. O contrato específico de custódia DNS-01 SHALL prevalecer para a credencial do wildcard, sem migrar outros segredos por inferência.

#### Scenario: Verificação de ignore
- **WHEN** `.env`, `.env.local`, `.env.homolog` ou `.env.prod` existem no projeto
- **THEN** o Git os ignora e `.env.example` permanece versionável

#### Scenario: Varredura de segredos
- **WHEN** a varredura de segredos é executada no repositório
- **THEN** nenhum segredo ou chave é encontrado

## ADDED Requirements

### Requirement: Custódia isolada da credencial DNS-01

A credencial DNS-01 do wildcard SHALL permanecer cifrada em repouso fora do banco compartilhado do NPM, com acesso limitado ao emissor e escopo mínimo na zona autorizada. Valor bruto MUST NOT aparecer em banco NPM, Git, frontend, argumentos de processo, logs ou relatórios. Sua materialização SHALL ser temporária e restrita ao emissor.

#### Scenario: Emissão ou renovação autorizada
- **WHEN** o emissor materializa a credencial para uma operação autorizada
- **THEN** somente o emissor acessa seu valor e o consumidor NPM recebe apenas o material de certificado necessário
- **AND** o material temporário da credencial é descartado ao encerrar a execução, inclusive em falha

#### Scenario: Custódia ou alcance incompatível
- **WHEN** a integração exige persistir token no NPM ou ampliar o alcance além da zona/finalidade autorizadas
- **THEN** a operação permanece bloqueada e não solicita nem grava uma credencial real

### Requirement: Instalação verificável e recuperação do certificado

A instalação SHALL validar nome, chave correspondente, validade e cadeia antes de trocar o material em uso. Falha de emissão, validação ou instalação SHALL preservar o certificado saudável anterior e permitir recuperação delimitada. A automação MUST NOT receber shell arbitrário, socket Docker ou escolha livre de container, caminho ou comando privilegiado.

#### Scenario: Certificado candidato inválido
- **WHEN** o material candidato não satisfaz as validações
- **THEN** o certificado em uso permanece ativo e o relatório sanitizado registra a falha

#### Scenario: Renovação e recuperação ensaiadas
- **WHEN** a renovação e a instalação são exercitadas em laboratório isolado
- **THEN** a evidência comprova troca válida, preservação em falha e retorno à referência anterior sem expor credenciais

### Requirement: Continuidade e autorização da operação DNS-01

Toda aplicação externa SHALL exigir inventário atual, mecanismo revisado e autorização operacional específica. O emissor e o instalador SHALL limitar-se ao wildcard Pick-your-Pic e MUST NOT desativar serviços ou hosts existentes por inferência. Um ensaio local SHALL usar somente credenciais e certificados sintéticos e não transmitir desafio DNS ou solicitação ACME reais.

#### Scenario: Plano exige interrupção
- **WHEN** o mecanismo não consegue preservar atendimento de raiz, markina ou projetos vizinhos
- **THEN** a aplicação externa fica bloqueada até revisão e consentimento específico para o impacto indispensável
