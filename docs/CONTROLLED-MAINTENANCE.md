# Manutenção cooperativa

O controle é opt-in por `CONTROLLED_MAINTENANCE_ENABLED=true` em todos os serviços backend que participam da manutenção: API, worker geral, workers faciais, preview adjustment e RAW. O valor padrão em Compose e `.env.example` é `false`; com ele desativado, o runtime não consulta Redis e mantém o comportamento normal.

A janela aprovada para manutenções futuras é 00h–03h preparação, 03h–06h manutenção e 06h–09h validação, no fuso `America/Sao_Paulo`. A agenda não fecha nem reabre o sistema automaticamente e não substitui autorização operacional específica.

Depois que todos os processos forem compatibilizados e a ativação estiver autorizada separadamente, a sequência no ambiente isolado é:

```text
python -m app.maintenance_cli maintenance-begin --operation <id>
python -m app.maintenance_cli status
python -m app.maintenance_cli wait --operation <id> --timeout 900
python -m app.maintenance_cli verify-state --operation <id>
python -m app.maintenance_cli maintenance-finish --operation <id>
```

`wait` precisa observar ACK de todos os pedidos/ciclos já admitidos. HTTP 5xx, exceção, desconexão ou falha no ACK deixa recibo pendente; `verify-state` e `maintenance-finish` também recusam estados persistentes `processing`/`receiving`. Timeout, recibo sem ACK, Redis/PostgreSQL indisponível ou identidade divergente mantém o gate fechado. Não apague recibos manualmente para contornar um bloqueio. O gate não limpa nem recria filas. A retomada é somente explícita; não há scheduler, fechamento automático por horário ou reabertura automática.

Mantenha a flag `true` em todos os processos enquanto o gate estiver ativo. Um processo iniciado com a flag desativada não consulta Redis; a flag só pode ser desativada depois que `maintenance-finish` confirmar o fechamento do gate.

Healthchecks seguem acessíveis. Sessões não são revogadas: ingressos comuns recebem HTTP 503 com `Retry-After: 5` e `Cache-Control: no-store` durante o gate, e voltam a funcionar depois da retomada. Uploads e requisições longas são contados pelo ciclo ASGI completo. Workers compatíveis deixam de iniciar novos ciclos e só confirmam o ciclo atual depois do retorno normal do processamento.

Somente `POST /internal/whatsapp/webhook` e `GET /infinitepay/return` são admitidos como callbacks críticos durante a manutenção, sujeitos aos handlers e à persistência/idempotência existentes. A continuidade desses eventos durante uma parada ou substituição da API não foi comprovada por estes testes. Portanto, a drenagem comum não autoriza parar a API; cada emissor precisa de receiver durável ou garantia comprovada de retry/reconciliação antes de um release que interrompa a API.

## Bloqueio do primeiro bootstrap

Os containers já publicados não consultam esta flag nem o gate. Um gate Redis não os pausa retroativamente. Não há protocolo legado comprovado para impedir novos claims e confirmar uploads/jobs ativos antes da primeira substituição. Assim, este procedimento não autoriza o primeiro deploy. O proprietário precisa escolher entre manter o release bloqueado até haver um bootstrap com quiescência verificável, ou autorizar em missão separada uma janela supervisionada que aceite explicitamente o risco residual de interromper trabalho em andamento e exigir reconciliação/retry. Nenhuma dessas operações ocorreu nesta implementação.
