# Publicação em homologação — 14/09/2026

## Inventário e autorização

Proprietário autorizou push, merge e deploy e confirmou explicitamente o plano após o inventário nesta execução. Escopo: rebrand, modo escuro/capas e paridade do worker opcional de ajuste de prévias; sem limpeza de dados, mudança de domínio/portas ou recursos externos ao projeto.

- Checkout remoto limpo em `eb8c0837e3144f8d27429dffc05bb3683169d59a`; CI/deploy anterior `34792305700` concluído com sucesso. Migration `20260913_0055 (head)` já aplicada. Isso substitui a indicação histórica de deploy pendente nos registros locais anteriores.
- Aplicação e serviços faciais saudáveis. Worker opcional ainda no container anterior `3b2d57d791ac`, anterior ao deploy do PR #82. Configuração atual por galeria: uma, habilitada, intensidade 75, exposição +1,8 EV, geração 4; 57 ajustes na fila. Singleton legado desabilitado. Não alterar essa configuração nem reenfileirar fotos.
- Entrada preservada `https://markina-homolog.duckdns.org`, bind exclusivo `127.0.0.1:8080`. Disco 33% usado / 131 GiB livres; aproximadamente 20 GiB de memória disponíveis.
- Preservar Firefly `9335f5e9077e`, `f06f36a5ed33`, `6ea8a742b093`, `768223c11835`; Nginx Proxy Manager `66c25ca56d8c`; Portainer `e49166611a66`.
- Preservar persistência e integrações: DB `56caed105a12`, Redis `ebfa19d492e5`; Evolution `c0db1647bc23`, `de2ca0cf5a16`, `3112575298ff`. Nenhuma nova rede, volume ou porta.

## Plano aprovado

1. Revisar diff e testes focados; push da branch e PR para develop, CI obrigatório sem bypass.
2. Merge após CI verde. Parar somente o worker opcional antes da publicação, usando Compose explicitamente limitado ao projeto.
3. Pipeline padrão com backup lógico exclusivo, verificação de schema (0055 já aplicada), recriação dos serviços de aplicação no SHA aprovado, preservando flags e segredos existentes.
4. Reconstruir e iniciar `preview-adjustment-worker` no mesmo checkout com `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml -f docker/docker-compose.preview-adjustment.yml --profile preview-adjustment up -d --build --no-deps preview-adjustment-worker`. A fila existente poderá então prosseguir com a configuração já escolhida pelo administrador.
5. Conferir SHA, saúde, schema, manifesto/nome/temas, configuração preservada, progresso da fila e IDs dos recursos não envolvidos. Possível breve interrupção apenas da aplicação durante recriação; sem restore/downgrade destrutivo.

## Estado

Inventário e plano confirmados; publicação ainda não concluída. Não declarar paridade até verificar aplicação e worker opcional.

## Revisão final

Três defaults de `MEDIA_WATERMARK_TEXT` nos dois arquivos Compose ainda usavam a marca antiga. Alinhados à constante de produto, preservando nome da variável, projeto e precedência do ambiente real. Teste de contrato adicionado: `product-brand.test.tsx`, 3 testes aprovados. Nenhum `.env` real editado.
