# Spec Delta

## Purpose

Permitir ingresso automatizado pelo website com e-mail verificado e ativação segura. Decisão de 03/11/2026 substitui aprovação manual anterior; prova local simples autorizada, sem publicação.

## RENAMED Requirements

- FROM: `### Requirement: Aceite operacional progressivo antes da compra`
- TO: `### Requirement: Aceite operacional somente para novos uploads`

## MODIFIED Requirements

### Requirement: Aceite operacional somente para novos uploads

O aceite de Termos SHALL exigir versão vigente e ação afirmativa antes de novos uploads, sem bloquear criação da conta, ativação exploratória, navegação, configuração ou compra de créditos. Compra permanece sujeita a e-mail verificado, perfil completo e controles financeiros próprios, conforme `billing/mercadopago-credit-purchases`. O protocolo SHALL ser append-only e preservar identidades das partes, texto integral/hash, instante UTC e evidência da ação.

#### Scenario: Falta aceite
- **WHEN** fotógrafo tenta enviar foto sem aceite válido ou com versão desatualizada
- **THEN** o upload é recusado e o painel aponta a etapa pendente em Configurações, enquanto exploração e compra seguem seus requisitos próprios

#### Scenario: Documento real indisponível
- **WHEN** faltam versão publicada ou identificação necessária do provedor fora de prova sintética local
- **THEN** a compra continua sujeita apenas ao perfil/e-mail e aos controles financeiros, o aceite de teste não libera uploads reais, e novos uploads permanecem bloqueados

#### Scenario: Candidato aceita a versão atual
- **WHEN** fotógrafo com conta exploratória ativa confirma a versão vigente no cadastro operacional
- **THEN** o servidor registra o aceite íntegro e libera novos uploads somente quando os demais gates estiverem completos

## ADDED Requirements

### Requirement: Cadastro público com nome e verificação de e-mail

O portal SHALL coletar nome informado e e-mail, verificar posse do e-mail por OTP protegido, de uso único e expiração limitada, com rate limit e respostas neutras. O nome MUST ser preservado no tenant ativado sem inferência por e-mail ou cadastro de cliente.

#### Scenario: E-mail verificado
- **WHEN** visitante conclui OTP válido
- **THEN** recebe autorização restrita para definir senha, sem depender de aprovação do proprietário ou receber sessão administrativa antecipada

#### Scenario: OTP inválido, expirado ou repetido
- **WHEN** visitante usa desafio inválido, expirado ou já consumido
- **THEN** cadastro não avança e a resposta não revela se há conta existente

### Requirement: Declaração de maioridade do fotógrafo

O portal SHALL exigir declaração afirmativa de maioridade do fotógrafo antes de iniciar a candidatura e registrar seu instante UTC. MUST NOT coletar data de nascimento/documento para esse fim nem apresentar a declaração como verificação independente. Sem confirmação, SHALL NOT persistir candidatura ou enfileirar OTP.

#### Scenario: Candidato confirma maioridade
- **WHEN** candidato confirma a declaração de maioridade e informa nome, e-mail e prova anti-bot válida
- **THEN** o sistema registra a confirmação e pode prosseguir com verificação de e-mail conforme limites e demais controles

#### Scenario: Declaração ausente ou não confirmada
- **WHEN** candidato não confirma a maioridade ou envia valor falso/ausente
- **THEN** a candidatura não é persistida, OTP não é enfileirado e nenhum tenant é criado

### Requirement: Acesso de clientes menores sem gate geral de idade

O fluxo normal de clientes SHALL continuar permitindo que clientes menores entrem em galerias, selecionem fotos e comprem, sem exigir vínculo geral de responsável ou introduzir um novo campo/gate de idade. Esta regra não altera controles específicos de funcionalidades, nem conclui a avaliação regulatória aplicável.

#### Scenario: Cliente menor usa o fluxo existente
- **WHEN** cliente menor conclui a autenticação e autorização existentes para uma galeria
- **THEN** pode selecionar e comprar fotos segundo os mesmos controles de acesso, pagamento e privacidade aplicáveis aos demais clientes

### Requirement: Ativação automática após verificação e senha

O sistema SHALL ativar automaticamente o fotógrafo após verificar e-mail e definir senha válida, sem exigir TOTP ou aceite dos Termos operacionais nessa etapa e sem aprovação manual ou convite do proprietário. TOTP é opcional no ingresso; quando ativado depois, será exigido nos logins seguintes segundo `add-progressive-photographer-onboarding`. Provisionamento MUST ser atômico e idempotente, criar somente tenant finito sem saldo artificial e vínculo administrativo próprio, sem grants globais.

#### Scenario: Configuração concluída
- **WHEN** fotógrafo verificado define senha válida na sessão restrita vigente
- **THEN** sistema cria administrador, tenant e vínculo próprios em uma transação, preserva nome e operação legada e permite login administrativo somente nessa conta

#### Scenario: Replay ou falha parcial
- **WHEN** conclusão é repetida ou falha antes do commit
- **THEN** nenhum segundo tenant, vínculo ou saldo é criado e nenhuma conta parcialmente configurada recebe acesso

#### Scenario: Ingresso sem TOTP
- **WHEN** fotógrafo conclui verificação de e-mail e define senha sem configurar TOTP no signup
- **THEN** a conta e o tenant próprio são ativados automaticamente, com TOTP opcional para configuração posterior

### Requirement: Expiração e cancelamento

Candidatura cancelada ou expirada SHALL invalidar OTP e sessão restrita. Nome e e-mail de cadastros sem verificação SHALL ser eliminados após 30 dias, conforme decisão do proprietário em 07/11/2026. O sistema MUST NOT apagar cadastro verificado, conta ativa, registro financeiro ou protocolo de aceite por esta regra. Credenciais/OTP/sessões de clientes MUST NOT autorizar ativação de fotógrafo.

#### Scenario: Sessão restrita expirada
- **WHEN** sessão restrita expirou ou foi invalidada antes da definição da senha
- **THEN** nenhum tenant ativo ou sessão administrativa é criado

#### Scenario: Material temporário vencido

- **WHEN** rotina local de expiração encontra OTP ou sessão restrita além do prazo
- **THEN** invalida os desafios e remove digest/cifra temporários sem apagar identidade, histórico ou tenant ativo
- **AND** nome e e-mail da candidatura não verificada são eliminados ao atingir 30 dias; dados de outras finalidades seguem políticas próprias

#### Scenario: Expurgo de candidatura antiga não verificada
- **WHEN** rotina habilitada encontra candidatura não verificada com pelo menos 30 dias
- **THEN** elimina a candidatura e limpa destinatário/corpo cifrados da outbox associada, preservando auditoria sanitizada sem nome/e-mail
- **AND** cadastros verificados e contas ativas permanecem intactos

### Requirement: Portal protegido contra abuso e habilitação prematura

O portal SHALL permanecer fechado por padrão para acesso público até validar gates R14, domínio/DNS/TLS, transporte de e-mail, proteção anti-bot server-side e retenção. Prova local isolada SHALL usar dados sintéticos e fronteiras externas simuladas sem enviar OTP em respostas HTTP. A ativação automática MUST NOT dispensar verificação de e-mail, senha válida, limites, políticas de sessão ou isolamento; TOTP permanece opcional no signup.

#### Scenario: Configuração externa incompleta
- **WHEN** operador tenta abrir cadastro público sem os gates configurados
- **THEN** o sistema recusa submissão sem provisionar acesso

#### Scenario: Prova local de backend
- **WHEN** testes isolados injetam e-mail e anti-bot sintéticos
- **THEN** o fluxo completo pode ser validado sem criar contas reais, publicar o site ou inventar aceite jurídico

### Requirement: Verificação anti-bot com Turnstile

O cadastro SHALL usar o widget Cloudflare Turnstile e validar o token no Siteverify antes de persistir candidatura ou enfileirar OTP. O servidor SHALL exigir `success=true`, hostname exato e ação `photographer_signup`; MUST rejeitar tokens vazios ou acima de 2048 caracteres. O token MUST NOT aparecer em logs ou respostas, e o servidor MUST NOT encaminhar o IP do visitante.

#### Scenario: Desafio válido
- **WHEN** o candidato envia token ainda válido e Siteverify confirma `success`, hostname esperado e ação `photographer_signup`
- **THEN** o cadastro pode prosseguir para as validações e limites existentes

#### Scenario: Token inválido, expirado ou repetido
- **WHEN** o Siteverify rejeita o token, ou a resposta não corresponde ao hostname/ação esperados
- **THEN** o cadastro é recusado antes de criar candidatura ou enfileirar e-mail OTP

#### Scenario: Configuração ausente ou falha de Siteverify
- **WHEN** a flag está desligada, falta chave pública/secreta, a resposta é malformada, ocorre timeout ou Siteverify falha
- **THEN** a submissão não cria candidatura nem envia/enfileira OTP e retorna uma falha sanitizada

### Requirement: Configuração segura do Turnstile

A chave secreta MUST existir somente na configuração segura do backend; a interface SHALL receber apenas a chave pública.

#### Scenario: Interface recebe a chave pública
- **WHEN** o cadastro está habilitado com as chaves necessárias
- **THEN** o endpoint de configuração entrega somente a chave pública, nunca o segredo

### Requirement: Ativação explícita dos canais do cadastro

As flags `PHOTOGRAPHER_SIGNUP_TURNSTILE_ENABLED` e `PHOTOGRAPHER_SIGNUP_EMAIL_DELIVERY_ENABLED` MUST permanecer desligadas por padrão. A integração SHALL ficar disponível somente quando ambas estiverem habilitadas e o canal SMTP existente estiver pronto.

#### Scenario: Flags desligadas ou SMTP indisponível
- **WHEN** uma flag estiver false ou o canal SMTP não estiver pronto
- **THEN** a API mantém o cadastro fechado e a interface não recebe uma chave pública utilizável

### Requirement: Falha fechada no Siteverify

Timeout, resposta malformada, erro HTTP ou configuração incompleta SHALL falhar fechado. O sistema SHALL NOT repetir automaticamente a validação de um token.

#### Scenario: Falha externa sem retry
- **WHEN** a chamada Siteverify falha ou não retorna JSON válido
- **THEN** o endpoint responde com erro sanitizado e não reenvia o token

### Requirement: Edição e versionamento dos Termos

O proprietário autorizado SHALL poder editar os Termos em rascunho e visualizar uma prévia. Cada versão publicada SHALL ser imutável e possuir conteúdo integral, número de versão e hash. Edições posteriores SHALL criar um novo rascunho, sem alterar texto ou protocolos aceitos anteriormente.

#### Scenario: Edição em rascunho
- **WHEN** o proprietário autorizado altera o texto ainda em rascunho
- **THEN** a versão vigente e os protocolos de aceite existentes permanecem inalterados

### Requirement: Publicação explícita dos Termos

O proprietário autorizado SHALL publicar cada nova versão por ação explícita; salvar ou editar um rascunho MUST NOT torná-lo vigente. Alteração material SHALL preservar os aceites anteriores e aplicar a política aprovada de reaceite.

#### Scenario: Publicação da versão editada
- **WHEN** o proprietário publica explicitamente uma nova versão
- **THEN** o sistema registra conteúdo, versão, hash e instante da publicação e a torna vigente sem alterar protocolos anteriores

#### Scenario: Nova versão publicada
- **WHEN** uma versão revisada é publicada explicitamente
- **THEN** o sistema sela conteúdo e hash, mantém versões/protocolos anteriores e aplica o gate de reaceite aprovado

### Requirement: Preenchimento com dados aprovados das partes

O template SHALL usar os dados obrigatórios aprovados do fotógrafo e a identidade jurídica vigente do provedor. O servidor MUST NOT inventar dados, reutilizar checkout de clientes nem exigir novos campos sem revisão de necessidade, finalidade, transparência e retenção.

#### Scenario: Identificação do provedor incompleta
- **WHEN** falta dado jurídico ou contato obrigatório para renderizar o documento
- **THEN** o aceite e as operações dependentes ficam indisponíveis sem revogar a conta exploratória

#### Scenario: Campo adicional do fotógrafo não aprovado
- **WHEN** o template solicita CPF/CNPJ, razão social ou dado fora do cadastro aprovado
- **THEN** o sistema não passa a coletar o campo sem revisão específica; a conta exploratória permanece ativa e operações sujeitas aos Termos ficam bloqueadas

### Requirement: Protocolo íntegro no histórico do fotógrafo

O sistema SHALL preservar texto integral, versão, hash, instante UTC, identidade das partes e ação afirmativa do aceite em protocolo append-only. O proprietário autorizado SHALL consultar o protocolo no histórico do fotógrafo; o fotógrafo SHALL poder obter uma cópia. Segredos de autenticação MUST NOT ser incluídos.

#### Scenario: Proprietário consulta o aceite
- **WHEN** proprietário autorizado abre o histórico do fotógrafo
- **THEN** consulta a data/hora UTC, identidade do fotógrafo e do provedor, versão, texto integral e hash, sem senha, OTP ou segredo TOTP

#### Scenario: Nova versão material dos Termos
- **WHEN** os Termos mudam materialmente
- **THEN** o sistema preserva o protocolo anterior e exige novo aceite quando a política aprovada determinar

### Requirement: Retenção do protocolo de aceite

O sistema SHALL manter o protocolo enquanto a conta estiver ativa e por até dez anos após o encerramento, com acesso restrito. Ao final, SHALL eliminar ou anonimizar o protocolo, salvo obrigação legal ou disputa documentada que justifique retenção adicional.

#### Scenario: Fim do prazo de retenção
- **WHEN** terminam dez anos do encerramento da conta e não existe obrigação ou disputa documentada que justifique extensão
- **THEN** o sistema elimina ou anonimiza o protocolo e restringe seu acesso durante o prazo de retenção

### Requirement: Limites do aceite perante clientes e LGPD

O aceite do fotógrafo MUST NOT ser tratado como consentimento ou autorização dos clientes, nem como exoneração geral do provedor. Cada parte SHALL responder pelos deveres legais aplicáveis às operações que efetivamente decide ou executa.

#### Scenario: Funcionalidade exige base legal ou autorização de cliente
- **WHEN** uma operação de dados do cliente exige base legal, informação ou autorização própria
- **THEN** o aceite do fotógrafo não substitui a medida exigida no fluxo correspondente
