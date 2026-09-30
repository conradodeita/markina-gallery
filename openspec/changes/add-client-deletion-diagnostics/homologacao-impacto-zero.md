# Homologação e impacto zero

## Inventário de referência

- Último deploy saudável verificado: run `36660152673`, SHA `abd4d21f8fec1efd0f18eb0a8eebe4c0f2444293`, concluído em 2026-09-30 02:43 UTC. O job `deploy-homolog` terminou com sucesso.
- O inventário sanitizado daquele deploy registrou 13 containers Markina saudáveis, incluindo Evolution API, banco e Redis conectados. O banco permaneceu em `20260929_0069 (head)`; esta change não adiciona migration.
- Endereço público atual: `https://markina-homolog.duckdns.org/`.
- Porta publicada no host: somente Nginx em `127.0.0.1:8080`; banco e Redis não publicam portas.
- Verificação somente leitura em 2026-09-30 03:25 UTC: `/healthz` e `/api/health` responderam HTTP 200.

## Plano de impacto zero

1. Integrar somente após CI aprovado; o job `deploy-homolog` exige aprovação do Environment `homolog`.
2. O deploy usa exclusivamente `-p markina-gallery -f docker/docker-compose.yml`; cria backup lógico dedicado da Markina antes da atualização e executa as migrations já versionadas, sem migration nova nesta change.
3. Reconstruir/recriar apenas os serviços Markina selecionados pelo script de deploy e conferir o inventário rotulado por projeto. Evolution API, banco e Redis permanecem no projeto existente; a operação não altera DNS, firewall, proxy global, certificados, nem recursos de outros projetos. Não executar `down` ou prune.
4. Confirmar o SHA publicado, estado saudável dos serviços e HTTP 200 em `http://127.0.0.1:8080/healthz`, `http://127.0.0.1:8080/api/health` e nas duas rotas públicas do domínio acima.
5. Se smoke test falhar, seguir o rollback do script para o SHA saudável anterior, mantendo o backup lógico e registrando os resultados antes de qualquer tentativa adicional.

## Verificação específica desta change

Os testes locais verificam erro sintético antes do commit (HTTP 500, `request_id`, resultado `not_committed` e corpo/log sem SQL ou PII) e falha auxiliar depois do commit (HTTP 200, recibo concluído e referência de reconciliação). A interface também cobre resposta HTTP 502 não JSON sem renderizar o HTML do proxy e sem repetir automaticamente a mutação.

Uma falha inesperada injetada diretamente no processo de homologação não faz parte do smoke test: não há chave ou mecanismo de falha sintética habilitado no produto. A publicação verificará saúde e SHA; a validação do contrato de falha permanece coberta pelos testes isolados e pelo CI.
