# Design

## Contexto

Esta change adiciona um controle Redis próprio para manutenção, uma middleware ASGI e wrappers cooperativos nos consumidores Python. A implementação experimental de release Python não faz parte desta change. O controle usa chaves próprias e operações Lua atômicas; PostgreSQL continua sendo a fonte durável de estado dos jobs. Nenhum job ou fila será limpo.

## Decisões

1. Manter controle e chaves Redis exclusivos de manutenção, sem importar o executor experimental de release Python. Sem serviço novo, tabela nova ou migration. `CONTROLLED_MAINTENANCE_ENABLED` ausente/falso é no-op sem consulta Redis; modo ativo exige PostgreSQL e Redis.
2. A middleware mantém todo o ciclo ASGI dentro do marcador ativo, inclusive leitura do corpo e envio da resposta. Healthchecks são isentos. Ingressos comuns recebem 503 antes do handler quando o gate está fechado; sessões continuam armazenadas e podem ser usadas após a retomada.
3. Os únicos caminhos críticos inicialmente isentos são `POST /internal/whatsapp/webhook` e `GET /infinitepay/return`. A exceção é por método e caminho exatos, mantém marcador ativo e preserva autenticação, deduplicação, idempotência e persistência do handler atual. Não altera a implementação do PR #260.
4. O ACK da middleware significa apenas que o handler terminou normalmente; se o handler lançar erro, o token permanece sem ACK. O modo não converte isso em sucesso. Um operador não pode parar a API com a justificativa de que a barreira está drenada enquanto os callbacks continuam admitidos.
5. Workers já compatíveis envolvem cada ciclo completo (admissão, claim, processamento e ACK persistente) no marcador compartilhado. O gate bloqueia a entrada do ciclo seguinte. Registros Redis sem TTL impedem que uma queda pareça drenagem; o CLI também confere estados persistidos `processing`/`receiving` antes de autorizar continuação.
6. As janelas 00h–03h, 03h–06h e 06h–09h (America/Sao_Paulo) são orientação de agenda, não autorização automática. Não há scheduler nem reabertura automática; fechamento e retomada exigem comando explícito e autorização da operação futura.
7. A primeira ativação em processos legados permanece NO-GO. Gate no Redis não para código que ainda não o consulta; Nginx fechado, estado momentaneamente vazio ou SIGTERM não provam drain. O proprietário deverá escolher entre (a) projetar e validar um bootstrap compatível com pausa/ACK dos legados, ou (b) autorizar separadamente um procedimento de manutenção supervisionada que aceite o risco residual documentado de interrupção/retry/reconciliação. Nenhuma alternativa será executada nesta change.
8. A API pode receber callback crítico durante o gate, mas os dados disponíveis não provam que os emissores repetirão callbacks nem que InfinitePay tenha receiver durável durante a substituição do processo API. Portanto, publicação que pare a API fica bloqueada até validar retry/reconciliação por provedor ou implementar recepção durável em change própria, coordenada sem modificar o PR #260.

## Compatibilidade

A mudança é desativada por padrão. O marcador usa somente chaves Redis próprias do projeto. SQLite continua sendo no-op apenas em testes locais; controles operacionais exigem PostgreSQL e Redis reais descartáveis. Falha de infraestrutura é fail-closed para novas operações e nunca apaga recibos.

## Questões em aberto

- Qual protocolo/garantia suportada pelos emissores cobre a lacuna de callback durante uma substituição da API? Requer confirmação por provedor antes de qualquer publicação que reinicie API.
- Qual procedimento o proprietário escolherá para o primeiro bootstrap em containers que não reconhecem o gate? Até a decisão e prova, a publicação é bloqueada.
