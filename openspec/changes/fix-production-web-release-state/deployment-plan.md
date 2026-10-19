# Plano da publicação web-only de segurança

## Estado

Engenharia em validação. Não autoriza produção. O SHA final será o merge desta change em main e constará do registro final da execução. Não usar automaticamente o SHA antigo do PR #226.

## Fonte do procedimento

Runbook completo: `docs/DEPLOY-PROD-WEB.md`. Os scripts do SHA aprovado e seus helpers pinados são carregados por Git em memória; o checkout antigo não precisa conter cópias atualizadas. Obter o objeto na Oracle é escrita operacional ainda não autorizada.

## Sequência proposta sob autorização conjunta futura

1. Obter somente o commit exato aprovado e conferir main, CI, árvore limpa, saúde, recursos de build, portas e domínio, seis Compose/hashes, ausência de tentativas pendentes e identidade real web/API. Não trocar checkout nesta preparação.
2. Revalidar nos logs o vínculo da imagem ativa com commit. Referência observada: origem fe1f3bc6e1a483bd1ac5f4e71149f903e724873f, ID sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573. Caso já seja outro runtime, interromper a operação afetada e apresentar nova evidência.
3. Se recibo ausente, reconcile-inventory e reconcile com SHA/ID explicitamente conferidos e fingerprint novo. Preservar imagem por ID e registrar adoção em histórico. Não copiar marcador antigo nem apagar conflito.
4. Executar inventário final sem escrita, conferir fingerprint, lock existente, imagens e estado não-web. A autorização conjunta permite ao executor calcular e consumir os códigos somente se todos os gates coincidirem com seu escopo.
5. Publicar somente web do SHA aprovado: preservar recibo/checkouts e imagem, build web, revalidar estado e recriar web com no-deps/no-build/force-recreate. API, banco, migrations, workers, Redis, nginx/proxy, redes, volumes, fotos e terceiros não são alvos.
6. Validar ID/configuração/saúde, HTTPS, disponibilidade de Vendas/pagamentos e Estatísticas 404, sem transações/OTP reais. Conferir snapshots não-web preservados. Registrar imagem/recibo saudável e evidência de versão, sem declarar publicação antes dessas verificações.
7. Se falhar, usar recover-inventory/recover do mesmo SHA de procedimento para restaurar imagem anterior por ID e checkout, sem rebuild, somente web. Build falho com container anterior saudável dispensa recriação. Restaurar somente a imagem atual preservada; não usar referências históricas app/web como atalho. Erro ou drift fora do plano conserva bloqueio e requer análise.

## Limites da autorização a solicitar

Uma única autorização: preparação Oracle + publicação web-only + validação + recuperação contingencial, no SHA exato integrado. Inclui fetch do alvo, tags verificadas apenas do web, recibos/histórico, checkout, cache/build e substituição exclusiva do web. Inclui restauração contingencial dessa mesma imagem/checkout se necessário. Não inclui wrapper remoto, nginx reload, banco/migrations, limpeza, configuração, fotos, outros serviços ou operações destrutivas.

Possível breve interrupção web durante recriação/recuperação; DNS dinâmico nginx já versionado deve ser confirmado sem alterar seu processo. Saúde/HTTPS, capacidade de build e preservação das imagens são gates imediatos. Se alguma divergência impedir a segurança, parar a operação afetada; não contornar.

## Retomada pontual do inventário

O inventário anterior foi bloqueado por Health ausente no migrate histórico, antes de adoção/build. A correção atual preserva o container parado e trata somente Health/Status opcionais; validação e revisão em optional-health-validation.md. O novo SHA será determinado após integração/CI e exigirá autorização operacional específica, sem reutilizar a autorização de 34d2afd5. Durante esta engenharia não executar escrita Oracle. Antes da retomada autorizada, repetir todos os gates mutáveis do runbook, preservar exatamente a imagem ativa revalidada e manter os demais serviços intocados.
