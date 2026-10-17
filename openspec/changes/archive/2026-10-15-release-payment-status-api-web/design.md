## Context

O servidor identificado como `clearbudget-vnic` hospeda a Markina em `132.145.193.169`. Em 2026-10-15, o checkout estava limpo e detached em `71be3b2`; API e web foram criados às 16:49 UTC. O registro `web-last-healthy.sha` ainda aponta para `faafe14`, portanto esse arquivo não prova a versão dos containers atuais. A main remota está em `200859a`, que não contém vários commits já instalados na produção. A API ativa contém código de hostname canônico e a migration 0081.

## Goals / Non-Goals

Preservar integralmente a versão instalada e publicar a classificação financeira aprovada, mediante inventário verificável e rollback pelas imagens reais. Não executar migrations, modificar templates/configurações persistidos, instalar dependências em serviços ativos, recriar workers, alterar infraestrutura de terceiros nem transformar o fluxo web-only em autorização genérica.

## Decisions

1. Integrar o commit de produção à main em branch isolada, por PR com CI, mantendo a árvore do runtime igual à produção mais o delta de pagamentos. Validar conflitos conforme specs de pagamentos e os contratos já implementados de autenticação/entrega.
   O download de fotos compradas já presente na produção permanece disponível para ambos os estados de pagamento confirmado, com ou sem link de álbum; classificação visual não revoga a autorização comercial existente. O teste de confirmação/correção cobre ambos os estados.
2. Usar os mesmos seis arquivos Compose e perfis ativos. Conferir hashes de configuração da API/web, metadados e imagens antes de executar; nunca imprimir configuração resolvida ou valores de ambiente.
3. Publicar código sem migration: o candidato deve conservar integralmente `backend/migrations`, dependências, Dockerfiles e Compose em relação a `71be3b2`. Ler a revisão Alembic ativa sem escrever dados e compará-la à cadeia candidata.
4. Preservar imagens antigas por ID e tags específicas antes de construir as novas. Construir somente API/web antes de trocar qualquer container; usar `up -d --no-deps --no-build` com serviços explicitamente selecionados. Não usar o job deploy-homolog.
5. Recarregar apenas o nginx da Markina depois de conferir sua sintaxe, pois o upstream da API usa nome estático. Não recriar nginx ou alterar seu arquivo. Verificar saúde interna e HTTPS público, autenticação negada sem sessão e presença do novo código sem consultar dados de clientes.
6. Se as verificações falharem, coletar diagnóstico sem segredos e usar plano de rollback aprovado para restaurar as duas imagens antigas e o checkout anterior. A recuperação não envolve banco, migrations ou prunes.
7. Entregar plano e inventário final com SHA candidato, imagens anteriores, domínio/portas, escopo e interrupção possível. Executar somente após aprovação daquele plano; qualquer drift exige reavaliação.

## Risks / Trade-offs

- Main atrasada em relação ao runtime: comparar candidato diretamente com `71be3b2`, não apenas com main.
- Registro de versão web desatualizado: identificar imagens reais e hashes dos arquivos da API; não reutilizar o SHA antigo como prova de rollback.
- Troca de IP da API: nginx da Markina precisa de recarga, sem alteração do proxy compartilhado.
- Containers únicos: breve indisponibilidade possível; impacto zero se refere aos demais projetos, não a uma promessa de zero downtime da Markina.

## Migration Plan

Nenhuma migration será executada. O runbook deve abortar se houver diferença na cadeia ou revisão desconhecida. Sequência: integração local, validação, PR/main, inventário final, aprovação explícita, preservação de imagens, build, troca restrita, verificações e evidência.
