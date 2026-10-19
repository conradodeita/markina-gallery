# Plano da publicação web-only de segurança

## Estado final — 19/10/2026

**PUBLICADO** no SHA `4b464f081dfa2451472848622853460398834e6d`, às 11:04:45 UTC, com verificação independente final às 11:08:13 UTC. Engenharia dos PRs #227/#228, CI, autorização específica e publicação concluídos.

Histórico dos PRs #226–#228, identidades completas e evidências: [publicação de produção](../remediate-frontend-dependency-vulnerabilities/production-publication-2026-10-19.md). Regressão e CI: [validação Health opcional](optional-health-validation.md) e [integração #228](optional-health-integration.md).

## Procedimento executado

Fonte: [runbook web-only](../../../docs/DEPLOY-PROD-WEB.md), na versão do SHA autorizado. Foram conferidos origem/commit/blobs, saúde, recursos, Compose, ausência de concorrência/tentativas e recuperação exata antes das mutações.

1. Obtenção do commit aprovado, sem troca antecipada do runtime.
2. Reconciliação auditável da imagem ativa `sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573`, originada em `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`, e preservação sob referência dedicada validada por ID.
3. Inventário final e revalidação sob lock; snapshot incluiu migrate histórico sem Health.
4. Build exclusivamente web e substituição apenas desse serviço, sem recriar dependências. Nova imagem: `sha256:6aef1935d8a4ba4bfc125a1bf5bea52ae6e26db361ef4942a1fedc55c4efc20a`.
5. Verificação de identidade, versões, saúde/HTTPS, asset público, recibos/histórico e preservação dos não-web. 15 serviços ativos saudáveis, migrate parado preservado; pagamentos 200 e Estatísticas 404, sem OTP/transações reais.
6. Rollback-inventory aprovado por leitura para a imagem/checkout anteriores exatos. Recuperação não necessária nem executada.

API, banco/migrations, workers, Redis, Nginx/proxy, volumes/fotos, configurações/segredos e terceiros preservados. Nenhuma limpeza ou instalação do wrapper remoto.

## Bloqueio histórico resolvido

A tentativa no SHA `34d2afd5b8f407adb70b0dee165fa8d55a83b478` parou em reconcile-inventory por Health ausente no migrate histórico, antes de adoção/tag/build. Apenas fetch preparatório ocorreu. O PR #228 corrigiu Health/Status opcionais, com falha antes/sucesso depois e preservação dos parados/campos obrigatórios. O proprietário então concedeu nova autorização para o SHA exato de #228; pedidos anteriores são históricos, não instruções atuais de retomada.

## Continuidade

Esta consolidação é somente documental, sem acesso Oracle. Futuro deploy exige nova autorização específica e repetição dos gates mutáveis; a evidência de 19/10 não congela o ambiente. Sincronização das specs principais e arquivamento continuam sujeitos à revisão humana.
