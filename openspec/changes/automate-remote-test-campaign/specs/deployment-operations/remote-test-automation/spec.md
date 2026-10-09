# Remote Test Automation Specification

## Purpose

Definir execução remota reproduzível e limitada de testes funcionais e de carga da Pick-your-Pic, com isolamento de identidades, dados sintéticos, salvaguardas de operação e relatórios verificáveis.

## ADDED Requirements

### Requirement: Alvo remoto fechado

O executor de testes SHALL aceitar somente o host HTTPS de homologação explicitamente configurado e validado por allowlist exata. SHALL NOT iniciar backend, frontend, banco, worker ou cópia local da aplicação para testes. SHALL NOT aceitar localhost, IP direto, produção ou host arbitrário.

#### Scenario: Alvo autorizado

- **WHEN** uma execução é iniciada com o host exato de homologação e uma configuração válida
- **THEN** Playwright e k6 enviam tráfego somente ao ambiente de servidor permitido e nenhum serviço da aplicação é iniciado localmente

#### Scenario: Alvo não permitido

- **WHEN** o host está ausente, é produção, localhost, IP direto ou não corresponde à allowlist
- **THEN** o executor termina no preflight antes de criar sessão ou emitir requisição de teste

### Requirement: Isolamento de identidades e autenticação

Cada fotógrafo, cliente e VU SHALL usar identidade, contexto de navegador, cookie jar e sessão próprios. O sistema MUST NOT compartilhar sessão entre identidades independentes. Credenciais, OTP, cookies e tokens SHALL NOT aparecer em stdout, logs, relatórios, traces publicados ou arquivos versionados.

#### Scenario: Sessões concorrentes

- **WHEN** duas ou mais contas realizam jornadas em paralelo
- **THEN** cada contexto autentica a identidade esperada e mantém seus cookies e operações isolados

#### Scenario: OTP sintético indisponível

- **WHEN** um cenário exige OTP e não há adaptador de teste aprovado e isolado
- **THEN** o cenário de autenticação é bloqueado sem chamar o provedor real e os cenários independentes continuam conforme o plano

#### Scenario: Segredo de teste ausente

- **WHEN** o secret store não fornece o TOTP ou segredo exigido para a conta de teste
- **THEN** a etapa protegida falha fechada sem imprimir o valor ou reutilizar credencial de outra identidade

#### Scenario: OTP sintético isolado habilitado

- **WHEN** um challenge pertence a tenant sintético explicitamente allowlisted em homologação e o sink está habilitado
- **THEN** o OTP é cifrado no Redis com TTL curto, nenhuma entrega ou fallback WhatsApp é criada, e a leitura autenticada o consome atomicamente uma única vez

#### Scenario: Sink OTP desabilitado, tenant divergente ou segredo inválido

- **WHEN** o sink está desligado, o tenant não está na allowlist ou a credencial do runner não confere
- **THEN** nenhum OTP é devolvido ou enviado por WhatsApp; a operação falha fechada com resposta neutra e sem registrar o segredo ou código

### Requirement: Dados sintéticos e preservação de mídia

Execuções remotas SHALL usar somente contas e registros sintéticos isolados. Arquivos de mídia existentes SHALL ser verificados por manifesto/hash, tipo MIME e dimensões antes do uso, lidos sem alteração e preservados integralmente. Arquivos de proveniência desconhecida ou associados a lote facial não SHALL ser reutilizados.

#### Scenario: Envio de imagem sintética

- **WHEN** a etapa aprovada requer upload e o arquivo corresponde ao corpus sintético validado
- **THEN** o runner transmite a cópia para a conta sintética isolada e comprova que o arquivo de origem permanece inalterado

#### Scenario: Arquivo sem proveniência

- **WHEN** o arquivo não tem proveniência sintética verificável ou pertence a lote biométrico não autorizado para esta campanha
- **THEN** o arquivo é recusado e não é transmitido ao servidor

### Requirement: Efeitos colaterais e escopo de operações

Por padrão, a campanha SHALL limitar-se a autenticação autorizada, leituras, negativas de isolamento e mutações reversíveis em dados sintéticos. Pagamentos, confirmações, mensagens externas, exclusões, alteração de configuração, biometria ou mutações em contas reais SHALL ser bloqueados por allowlist antes da requisição.

#### Scenario: Operação bloqueada

- **WHEN** uma etapa tenta executar operação fora do conjunto aprovado
- **THEN** o runner recusa a ação e registra apenas a categoria sintética do bloqueio

### Requirement: Limites de carga e parada automática

Cada perfil k6 SHALL declarar VUs máximos, taxa máxima, duração, ramp-up, ramp-down, thresholds e critérios de parada antes da execução. Estresse e estabilidade prolongada SHALL NOT executar-se em servidor compartilhado sem autorização operacional explícita e limites aprovados.

#### Scenario: Limite excedido

- **WHEN** erro, latência, healthcheck, fila ou recurso medido viola um limite aprovado
- **THEN** a campanha interrompe novos requests, preserva dados/serviços e registra a condição de parada sem ampliar limites automaticamente

#### Scenario: Perfil incompleto

- **WHEN** limite ou threshold obrigatório não está definido ou aprovado
- **THEN** o perfil permanece inelegível e não envia carga

### Requirement: Relatórios sanitizados e métricas ausentes

Cada execução SHALL reportar SHA/versão, ambiente, perfil, duração, VUs, taxa de operações, latências p50/p95/p99, erros, checks funcionais, métricas disponíveis, evidências, limitações e recomendação próxima. Métricas indisponíveis SHALL ser identificadas como indisponíveis e MUST NOT ser representadas como zero. O relatório MUST NOT inferir capacidade máxima sem campanha válida e perfil declarado.

#### Scenario: Coleta incompleta do host

- **WHEN** CPU, memória, disco ou outra métrica de host não possui fonte read-only autorizada
- **THEN** o relatório identifica a métrica ausente e mantém a conclusão restrita às evidências coletadas

#### Scenario: Traces com falha

- **WHEN** Playwright falha em identidade ou jornada sintética
- **THEN** o runner gera artefato de diagnóstico sanitizado e temporário, removendo credenciais, OTP, cookies, tokens, conteúdo pessoal e cabeçalhos de autorização antes de anexá-lo

### Requirement: Campanha sequencial e não concorrente com ensaio humano

O runner SHALL impedir sobreposição com outra campanha e SHALL respeitar o lock/estado operacional do ensaio A+B. Resultados de execução manual anterior ou de ambiente local MUST NOT ser apresentados como execução remota atual.

#### Scenario: Ensaio A+B ativo

- **WHEN** o bloqueio de ensaio A+B estiver ativo ou sua conclusão ainda não tiver sido informada
- **THEN** o runner não inicia campanha que compartilhe contas, galerias, canal ou recurso de servidor
