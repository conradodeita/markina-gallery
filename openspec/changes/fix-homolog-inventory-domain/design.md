# Design

## Context

O workflow atual já usa o secret `HOMOLOG_PUBLIC_BASE_URL` no pipeline de deploy, mas o workflow manual de inventário não o recebe. O script remoto compara `PUBLIC_APP_ORIGIN` com um hostname literal e o workflow também monta os health checks usando esse literal.

## Goals / Non-Goals

**Goals:**
- Compartilhar a origem homologada já configurada no Environment `homolog` entre o workflow, o script remoto e os probes públicos.
- Recusar URL ausente, malformada ou divergente antes de coletar dados ou fazer probes.
- Manter a saída sanitizada e o inventário restrito ao projeto `markina-gallery`.

**Non-Goals:**
- Alterar DNS, proxy, arquivos de ambiente do servidor, Compose, containers ou serviços.
- Criar ou rotacionar secrets, mudar o domínio configurado ou publicar aplicações.
- Remover a validação HTTPS, a comparação do domínio do Compose ou os guards de SHA/topologia.

## Decisions

1. O workflow receberá `HOMOLOG_PUBLIC_BASE_URL` do Environment `homolog`, o mesmo secret usado pelo deploy. Isso evita outra configuração de domínio e preserva a fonte de verdade operacional.
2. O workflow validará a URL como origem HTTPS sem credenciais, caminho, query, fragmento ou porta explícita antes de conectar por SSH ou chamar endpoints públicos. A falha apresentará somente uma mensagem de categoria.
3. O script remoto receberá essa origem como argumento, validará sua forma e comparará o hostname com `PUBLIC_APP_ORIGIN` renderizado pelo Compose. A comparação rejeitará divergências antes de `compose ps` ou da consulta transitória ao banco.
4. Os probes externos usarão a origem aprovada e os logs exibirão apenas seu hostname. A alternativa de atualizar o literal para `markina.pickyourpic.com.br` foi descartada porque repetiria o problema quando a origem configurada mudar.
5. Os testes de política verificarão configuração do secret, ausência de hostnames fixos, falhas antes das consultas e preservação dos guards read-only já existentes.

## Risks / Trade-offs

- [O secret do Environment pode divergir do Compose] → O inventário falha fechado antes de consultas/probes e identifica a divergência sem registrar a URL.
- [O secret pode estar ausente] → O workflow informa o nome da configuração ausente, sem abrir SSH nem tentar uma URL padrão.
- [Um hostname novo pode estar no Compose sem atualização do secret] → A falha explícita exige reconciliar a configuração homologada pelo fluxo autorizado, sem alterar o servidor durante o inventário.

## Migration Plan

1. Validar a change, executar testes de política e confirmar que `HOMOLOG_PUBLIC_BASE_URL` está definido no Environment `homolog` por meios que não revelem seu valor.
2. Integrar a correção por PR em `main`; o workflow manual passa a usar a origem configurada quando for iniciado novamente.
3. Nenhuma migration, alteração persistente, reinício, deploy ou mudança no servidor é necessária para esta correção.

## Open Questions

Nenhuma.
