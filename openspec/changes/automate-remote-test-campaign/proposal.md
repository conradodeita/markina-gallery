# Proposal

## Why

A campanha de validação multitenant precisa repetir jornadas com identidades independentes e avaliar concorrência sem iniciar cópias locais da aplicação nem depender de perfis manuais do Chrome. O repositório já possui pytest, Vitest e um ensaio opt-in com Python Playwright, mas não oferece um executor remoto reproduzível de carga HTTP com k6, autenticação remota automatizável ou limites versionados.

## What Changes

- Criar execução funcional remota com Playwright, reaproveitando pytest, Vitest e o harness de piloto existente.
- Criar cenários de carga HTTP/API com k6, identidades independentes por usuário virtual e perfis explicitamente limitados.
- Permitir somente o ambiente de homologação autorizado por URL exata e usar dados sintéticos isolados.
- Fornecer um caminho de autenticação de teste não interativo para OTP e TOTP, sem tocar no transporte real de mensagens nem nas credenciais de contas não destinadas ao teste.
- Registrar relatório sanitizado com versão, ambiente, perfil, duração, latências p50/p95/p99, taxa de operações, erros, verificações funcionais e métricas de servidor disponíveis.
- Preservar os arquivos de imagem originais: os testes poderão lê-los e enviá-los sem alterar ou remover a fonte.

## Capabilities

### New Capabilities

- `deployment-operations/remote-test-automation`: execução remota, confinamento, autenticação segura, limites, relatório e critérios de parada para testes funcionais e de carga.

### Modified Capabilities

- Nenhuma capability do produto é alterada. Qualquer mecanismo de autenticação exclusivo de testes SHALL permanecer fora do fluxo normal do cliente/fotógrafo e desligado por padrão.

## Impact

O escopo provável inclui harnesses Python/Playwright, cenários k6, comandos ou workflows de execução manual controlada, fixtures sintéticas, filtro de artefatos e documentação operacional. Os requests funcionais e de carga serão direcionados somente a `https://markina-homolog.duckdns.org`; nenhum backend, frontend, banco ou worker será iniciado localmente.

O diagnóstico inicial não encontrou credenciais de teste acessíveis ao executor, canal remoto SSH local nem adaptador remoto de captura de OTP aprovado. O harness existente tem `RecordingWhatsApp` somente para testes e fixture local. Esses gates deverão ser resolvidos por canal seguro antes de automação autenticada remota.

## Non-goals

- Adicionar autenticação Google/OAuth.
- Usar ou alterar o ensaio A+B que está em andamento.
- Executar carga, estresse, estabilidade prolongada, pagamentos, mensagens externas, exclusões, alterações de configuração ou busca facial como parte da inspeção inicial.
- Alterar produção, banco, containers, volumes, redes, proxy, DNS, firewall, certificados ou recursos de terceiros.
- Inferir capacidade máxima, SLO ou quota a partir de uma campanha pequena ou de um único processo de navegador.
- Usar fotos reais ou lote facial de proveniência não confirmada.

## Review

Em 08/10/2026, o proprietário autorizou continuar com os testes automatizados e, posteriormente, provisionar duas contas sintéticas independentes, armazenar as credenciais TOTP em `homolog-tests`, implementar um sink OTP isolado e definir limites explícitos. As contas e secrets foram preparados e um perfil read-only baixo foi executado com resultados intermitentes. A campanha autenticada permanece bloqueada até a configuração do segredo/allowlist no servidor e o deployment do sink em homologação. Estresse, estabilidade prolongada, operações destrutivas e interferência no ensaio A+B continuam excluídos; deployment ainda requer autorização operacional explícita.
