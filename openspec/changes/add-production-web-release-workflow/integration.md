# Integração revisável da linha de produção

## Decisão e escopo

Em 2026-10-14, após exposição da divergência (562 commits exclusivos de develop e 11 de main), o proprietário autorizou prosseguir com a preparação da integração para revisão. O alvo é um PR para main, sem merge nem deploy nesta preparação.

A base da aplicação será exclusivamente o SHA já observado em produção `aa7119c0b82bd5fa147fe6bbdac98dfa21091190`. A mudança posterior de pagamentos em develop (`92366f5`) e o checkout local com trabalho de outras tasks não são fontes de código desta integração. O tamanho do PR contra main representa o histórico da aplicação já implantada; a comparação de runtime deve ser feita contra `aa7119c`.

## Resolução da divergência

- Incorporar a ancestralidade de `origin/main` (`e0b29dd97f4319d43e49870cefff114f993cd7b8`) em branch isolada baseada na produção, preservando ambos os históricos.
- Preservar o código de aplicação/backend/Compose do SHA ativo nesta etapa.
- Conservar os workflows manuais de inventário/facial existentes em main e o job de política de inventário acrescentado por main.
- Resolver a manutenção preservando a execução operacional apenas quando a ref é develop; em main e outras refs permanece uma entrada que recusa operação antes de acessar o servidor. Isso conserva o contrato inerte de main e o contrato operacional de develop.
- Reunir os requisitos já consolidados das duas branches, sem sincronizar nem arquivar as novas changes de release e galeria.
- Ativar o carregamento tardio na rota canônica autenticada `/public-galleries/[galleryId]`, usando a opção já presente `deferGridImages`. Em produção, `/gallery/[galleryId]` é apenas um redirecionamento legado; a implementação antiga no checkout local não deve substituir essa rota.

## Gates

O PR é de revisão, não autoriza merge nem publicação. As validações devem usar a nova árvore; resultados do checkout antigo não certificam esta candidata. Antes de publicar, são necessários revisão/CI de main, inventário atualizado, SHA exato e aprovação explícita do release web conforme design/runbook. Não há alteração de segredos ou de recursos remotos nesta preparação.
