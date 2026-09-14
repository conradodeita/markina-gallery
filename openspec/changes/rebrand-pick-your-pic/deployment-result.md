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

Publicação de código concluída: PR #83 mergeado em `23bdee9bb7b3c1f946693f08c48741dee28188f1`, às 12:09:47 UTC. CI do PR `34841304268` aprovado (backend 555 passed / 3 skipped; frontend 251 passed, lint/build; OpenSpec e gitleaks). Pipeline develop/deploy `34841907861` concluído com sucesso após aprovação explícita do ambiente homolog. Nenhuma suíte completa local adicional; checks obrigatórios de CI preservados.

Backup lógico restrito criado pelo pipeline em `/var/lib/markina-gallery/backups/predeploy-20260914T121540Z-23bdee9bb7b3.dump` (~4,9 MB, modo 600). Schema continua `20260913_0055 (head)`. `last-healthy.sha` e checkout remoto apontam o merge. Checkout remoto limpo.

Worker opcional antigo parado antes da publicação e reconstruído depois no mesmo checkout. Novo container `2daec34b5208`, saudável; hashes de `preview_adjustment/service.py` e `product_brand.py` coincidem com o checkout do merge. A fila começou a avançar: primeira aferição 7 prontos, 1 processando, 49 na fila, nenhuma falha. Configuração preservada em intensidade 75, exposição +1,8 EV, geração 4. Nenhum reenfileiramento manual ou mudança de configuração.

API, web, nginx, worker comum e três workers faciais saudáveis; `FACIAL_PROCESSING_ENABLED=true` confirmado pela configuração runtime. HTTPS `/healthz` e `/api/health` aprovados. Todos os IDs de terceiros, banco/Redis e Evolution listados no inventário permaneceram iguais. Nenhuma mudança de porta, rede ou volume. Container facial legado já parado permaneceu intacto; aviso de órfão do Compose não foi seguido por limpeza.

Smoke público em Chrome, 390 e 1440 px: nome/manifesto Pick-your-Pic, escolha claro/escuro persistida após reload, sem overflow nem erro JS. Capturas dos dois temas inspecionadas em `.codex-tmp/homolog-rebrand-*`, não versionadas. Superfícies autenticadas seguem cobertas pelos testes locais; revisão estética final do proprietário permanece pendente.

Paridade de código da aplicação e worker confirmada. **Identidade visual por arquivo bloqueada**, conforme diagnóstico abaixo; não declarar PWA/arte oficial plenamente validada.

## Revisão final

Três defaults de `MEDIA_WATERMARK_TEXT` nos dois arquivos Compose ainda usavam a marca antiga. Alinhados à constante de produto, preservando nome da variável, projeto e precedência do ambiente real. Teste de contrato adicionado: `product-brand.test.tsx`, 3 testes aprovados. Nenhum `.env` real editado.

Push concluído e PR #83 aberto. CI inicial `34841042762` identificou um contrato textual antigo do PWA que exigia InstallApp imediatamente adjacente a children, incompatível com a toolbar de aparência aprovada. Atualizado para verificar instalação única na toolbar compartilhada e ausência de duplicação nos shells, preservando asserções de manifesto, offline privado e contraste. Sem alteração de comportamento para contornar testes.

Validação da correção: 13 testes aprovados em pwa-contract, install-app, theme-control e product-brand, com um worker local. Demais gates permanecem obrigatórios no CI.

## Bloqueio encontrado no smoke: arquivos de branding não persistidos

- `/api/branding` anuncia logo, ícone e favicon configurados, mas as três rotas de arquivo retornam 404. O fallback textual Pick-your-Pic funciona, sem esconder a falha operacional.
- Diagnóstico read-only confirmou que os três registros existem no banco, mas os arquivos não existem em `branding_root() = /app/media/branding`.
- Esse caminho não está em nenhum mount persistente da API. O Compose monta somente fontes, derivados, histórico e referências faciais em `/var/lib/markina/...`; não transporta `BRANDING_ASSETS_ROOT`. A implementação antiga permite guardar uploads de marca na camada efêmera do container. Recriações podem perdê-los.
- Não foi aferida a existência dos arquivos antes desta publicação; portanto não é possível determinar em qual deploy desapareceram. Não atribuir com certeza a perda a esta execução nem afirmar que já estavam ausentes.
- Inspeção segura em diretórios próprios `/opt/markina-gallery`, `/var/lib/markina-gallery` e volumes montados de fontes/derivados/histórico não encontrou logo/app-icon/favicon recuperáveis. Não há container API anterior preservado; não houve inspeção/mutação de overlay Docker ou recursos de terceiros.
- Nenhum registro de branding apagado, nenhuma arte substituta inventada e nenhum upload da prancha composta fornecida como referência. Backup lógico de banco não contém os bytes dessas imagens.
- Próximo passo requer change cirúrgica e aprovação: persistência explícita de uploads de marca, procedimento de migração não destrutivo quando existirem arquivos e teste de recriação. Depois solicitar os arquivos individuais ao proprietário para reenvio. Não considerar mero reenvio suficiente antes de corrigir a persistência.

As implementações locais permanecem concluídas; revisão humana, sincronização/arquivamento e resolução da pendência operacional acima ainda não realizados.
