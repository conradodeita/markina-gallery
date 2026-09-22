## Context

`ensure_public_app_origin` no deploy persiste a origem HTTPS autorizada em `PUBLIC_APP_ORIGIN`. API e worker geral recebem essa variável, mas `face-search-worker`, responsável por `process_next_search_notification`, recebe a âncora facial com URL local padrão. A outbox guarda caminho relativo cifrado; origem é acrescentada no envio.

## Decisions

1. Acrescentar `PUBLIC_APP_ORIGIN` à âncora facial e remover duplicação dos serviços que já a herdam. Não modificar flags, `.env` ou secrets: o deploy existente já fornece a configuração correta.
2. Resolver origem principal não vazia primeiro, depois variável legada. Origem principal inválida causa erro de configuração, sem fallback para outra origem. Normalizar barra final, validar porta, esquema, hostname, ausência de credenciais/query/fragmento/caminho e whitespace. Fora de development/test/local, exigir HTTPS e hostname público; rejeitar localhost, sufixos locais e IP não global, inclusive loopback IPv4/IPv6.
3. Falhar antes de chamar o provedor. O tratamento existente registra falha de configuração e retentativa limitada; não reenviar mensagens já marcadas como enviadas nem modificar outbox histórica. Testes usam provedor falso e dados sintéticos.

## Risks / Trade-offs

- Configuração inválida deixa de produzir notificação com URL incorreta, podendo esgotar as retentativas existentes; não alterar essa política.
- O endereço legado permanece compatível para instalações que o configuram explicitamente; homologação usa origem canônica do deploy.
- Não há consulta DNS na validação: configuração é controlada pelo operador e a validação recusa hosts locais e IPs literais não públicos.

## Migration Plan

Sem migration. Após CI e autorização de merge/publicação, usar workflow existente para atualizar código/Compose e recriar o worker facial com `PUBLIC_APP_ORIGIN`. Destino histórico `markina-homolog.duckdns.org`, entrada `127.0.0.1:8080`, projeto `markina-gallery`; conferir inventário atual antes da operação. Sem novas portas, volumes, redes ou recursos de terceiros. Mensagens já enviadas não são alteradas nem reenviadas.
