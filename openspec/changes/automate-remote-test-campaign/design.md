# Design

## Context

O produto autentica clientes com link autorizado e OTP via WhatsApp e fotógrafos com senha e TOTP. Não existe login Google. A change `add-small-multi-photographer-pilot` já contém um corpus sintético 2×3, um adaptador WhatsApp de registro somente local e um ensaio Playwright que percorre APIs e interface locais. O novo executor deverá atingir somente o serviço publicado de homologação e não reutilizar o ensaio manual A+B.

## Goals / Non-Goals

### Goals

- Reutilizar pytest, Vitest e o harness Python Playwright existente.
- Executar navegador e k6 em um runner dedicado contra o host HTTPS de homologação; não iniciar serviços da aplicação nem banco local.
- Manter contexto, cookie jar, sessão e identidade separados por fotógrafo/cliente e por VU.
- Bloquear alvos, operações e perfis não aprovados antes de enviar requisições.
- Automatizar etapas previamente aprovadas, com relatório sanitizado, limites máximos e parada automática.

### Non-Goals

- Reproduzir login de terceiros ou compartilhar sessões de Chrome reais.
- Medir biometria, qualidade estética, produção, capacidade máxima ou efeitos em clientes reais.
- Criar observabilidade nova no servidor durante a inspeção inicial.

## Decisions

### Executor remoto

Playwright e k6 serão executados em runner externo dedicado, por workflow manual/controle equivalente. O browser acessará apenas o frontend e a API do host permitido. O código SHALL conferir uma allowlist exata antes de iniciar; localhost, IPs diretos, produção e URLs arbitrárias serão recusados. O grupo de concorrência da campanha SHALL impedir sobreposição com o ensaio A+B e com outra campanha.

### Identidades e autenticação

Não será adicionado Google OAuth. Cada identidade de teste terá conta, contexto de navegador, cookie jar e sessão próprios. Playwright manterá estado autenticado em memória durante uma execução; arquivos de estado persistente não serão necessários. k6 mapeará cada VU para uma identidade exclusiva e nunca compartilhará cookies ou token entre VUs.

O adaptador `RecordingWhatsApp` atual não entrega OTP remotamente e não é um mecanismo de autenticação do servidor. Até que o sink de teste dedicado esteja publicado e habilitado somente para os tenants sintéticos, os cenários que dependem de OTP ficam bloqueados. Segredos TOTP e de runner são obtidos de um secret store protegido, fora do Git, da linha de comando e dos logs; ausência de credencial bloqueia o cenário correspondente.

Em 08/10/2026, o proprietário autorizou um mecanismo de OTP exclusivo para a campanha. O desenho escolhido é um sink efêmero no backend, habilitado somente em `homolog`, desligado por padrão e limitado a uma allowlist explícita de tenants sintéticos. Para esses tenants, o fluxo SHALL armazenar o OTP cifrado no Redis com TTL máximo de 10 minutos, sem criar entrega WhatsApp nem fallback; a leitura remota SHALL exigir segredo aleatório dedicado do runner e consumir a chave atomicamente uma única vez. Challenge, tenant e estado/expiração serão revalidados antes de devolver o código; falha de Redis ou configuração SHALL falhar fechada. O endpoint e a configuração não podem ser habilitados no ambiente `production`. O Compose fornece as variáveis somente à API. A publicação autorizada está limitada à substituição da API, sem migration nem reinício de outros serviços; o schema remoto deverá continuar em `20261001_0071`.

### Dados e mídia

Os testes usarão contas e registros sintéticos isolados. O diretório candidato de 72 imagens foi comparado em modo somente leitura com os 12 JPEGs canônicos gerados por `pilot_fixture.py`: 36 correspondem byte a byte e entram no manifesto permitido; 36 sem correspondência são recusados. O verificador comprova MIME e dimensões e não altera originais. Antes de qualquer envio remoto, o executor SHALL recalcular os hashes e comparar com o manifesto. Lotes de 50 arquivos encontrados na área de ensaios faciais não serão reutilizados nesta campanha, pois sua proveniência sintética não está confirmada. Se o runner não puder acessar com segurança os arquivos validados, fluxos de mídia permanecem bloqueados sem impedir jornadas independentes.

### Operações permitidas e carga

Por padrão, cenários remotos poderão autenticar, ler bibliotecas/galerias/prévias, exercitar negativas entre contas e criar/remover seleções de teste em registros sintéticos isolados. Pagamentos, confirmações, envio de mensagens, exclusões, configuração administrativa, upload fora do lote sintético e busca facial ficam bloqueados.

Os perfis smoke, carga esperada, pico, estresse e estabilidade deverão fixar VUs, duração, ramp-up, ramp-down, taxa máxima e thresholds. Nenhum perfil de carga será executado até esses números serem aprovados para o host compartilhado. Smoke e carga gradual precederão qualquer perfil maior. Sinais de healthcheck falho, erro acima do limite aprovado, latência acima do limite aprovado ou fila/recursos fora do envelope causarão parada imediata. Limites não poderão ser ampliados automaticamente após falha.

### Métricas e relatórios

k6 produzirá métricas de cliente como requisições/s, latências p50/p95/p99, erros e checks. O monitor existente `capacity-report/v1` é somente leitura e cobre o pool da API respondente, conexões PostgreSQL e filas documentadas; será coletado antes/durante/depois por uma identidade autorizada, mantendo timestamps e indicador de cache.

CPU, memória e disco do host não são medidos por esse contrato. Só serão adicionados se houver fonte read-only autorizada e escopo limitado aos serviços Markina. Quando indisponíveis, o relatório deverá indicar a lacuna, nunca preencher com zero ou estimativa. O relatório não calculará capacidade máxima nem afirmará SLO sem perfil de carga e critérios aprovados.

### Artefatos e privacidade

Relatórios e resultados funcionais usarão IDs sintéticos e sem PII. Screenshots e traces só conterão dados sintéticos. O trace bruto ficará em diretório efêmero protegido no runner, será sanitizado para remover cookies, tokens, OTP, cabeçalhos de autenticação, corpos sensíveis e parâmetros privados, e somente a cópia sanitizada poderá ser anexada ao relatório. Relatórios e capturas não serão versionados no Git. Segredos e respostas de autenticação não aparecerão em stdout, traces entregues nem resultados k6.

### Workflow e ambiente

O workflow de testes será separado do workflow de deploy. Uma execução não poderá disparar build/deploy nem executar migration. O ambiente alvo será `homolog` e terá secrets de teste próprios, distintos dos secrets de deploy. Se esses secrets ou o canal de teste não estiverem provisionados, o preflight falhará antes de gerar tráfego autenticado.

## Risks / Trade-offs

- As sessões, duas contas autenticadas no Chrome e os canais A/B atualmente usados pertencem ao ensaio A+B e não poderão ser reutilizados até seu encerramento e revisão.
- O ambiente é compartilhado com outros projetos. Sem limites explícitos e fonte de métricas host autorizada, a carga progressiva não pode avançar além de um smoke previamente aprovado.
- O acesso SSH local não está configurado. O deploy usa secrets de GitHub Actions; esses secrets não fornecem identidade de teste nem foram lidos. Um caminho de leitura remota para métricas host continua pendente.
- O acesso SSH de inspeção passou a estar disponível e foi autorizado pelo proprietário. Foram provisionados dois fotógrafos sintéticos isolados, mas não há binding de canal nos tenants e o provider sandbox descarta conteúdo. O sink foi implementado localmente. Em 08/10/2026, o proprietário autorizou configurar o segredo/allowlist de homologação e substituir somente a API; a aplicação e a verificação do OTP ainda estão pendentes.
- O diretório candidato de imagens é externo ao repositório e precisa de hash/manifesto confirmado antes de upload; arquivos faciais de proveniência não confirmada são excluídos.

## Migration Plan

1. Revisar esta change, confirmar contas sintéticas independentes, origem das imagens, credenciais por secret store e limites por perfil.
2. Implementar harness/runner e barreiras de alvo/operações; executar somente verificações estáticas e testes unitários próprios do runner, sem iniciar a aplicação local.
3. Validar preflight remoto sem mutação e, após autorização, executar fumaça de baixa carga no ambiente permitido.
4. Correlacionar Playwright/k6 com `capacity-report/v1`; avançar perfil apenas quando o anterior passar e os limites autorizados permanecerem válidos.
5. Parar ao primeiro limite excedido, preservar artefatos sanitizados, diagnosticar automação e repetir apenas a etapa segura afetada.

## Open Questions

- A execução autenticada ficará bloqueada até o sink passar pela validação automatizada em homologação.
- Quais credenciais de teste existem no secret store do runner, e quais contas/tenants são exclusivamente sintéticos e fora do ensaio A+B?
- Qual perfil máximo de VUs, duração, requisições/s e thresholds o proprietário autoriza para smoke e carga esperada na homologação compartilhada?
- Como o runner aprovado terá acesso efêmero ao subconjunto de 36 imagens validadas sem versionar mídia ou registrar referências locais? Os lotes de 50 fotos da campanha facial permanecem excluídos.
- Existe fonte atual read-only de CPU, memória e disco por serviço Markina? Sem ela, esses campos serão registrados indisponíveis.
