# Design

## Decisão

Cada downgrade protegido tenta adquirir, antes de consultar os guards, um único conjunto de locks PostgreSQL ACCESS EXCLUSIVE NOWAIT contendo todas as tabelas que serão consultadas, removidas ou terão colunas/constraints alteradas. O lock e o restante do downgrade permanecem na mesma transação Alembic.

NOWAIT faz a operação falhar imediatamente quando existe transação concorrente, em vez de esperar enquanto segura somente parte do conjunto. Se o lock do conjunto falhar, a transação Alembic é abortada e revertida antes de qualquer guard ou DDL. O conjunto inclui as tabelas alvo de operações de remoção/estreitamento, mesmo quando a tabela não aparece no SELECT EXISTS.

## Compatibilidade operacional

O requisito consolidado de deployment continua exigindo interrupção verificada dos escritores ativos antes de uma migration autorizada. Os locks do downgrade são uma defesa adicional para chamadas manuais ou escritores esquecidos; não substituem a janela de manutenção. O rollback normal de aplicação segue limitado a API/web e não executa downgrade automático.

Não será criado lock consultivo global: os caminhos de escrita atuais não compartilham um protocolo único de advisory lock. A proteção usa locks PostgreSQL sobre as relações realmente tocadas.

## Escopo

Revisar as migrations locais de 0094 a 0126 que consultam dados no downgrade antes de remover tabelas/colunas, reduzir tipos ou remover contexto protegido. Preservar a cobertura de tabelas já bloqueadas em 0094/0095 e fazê-la falhar imediatamente com NOWAIT. Padronizar 0114 para NOWAIT e incluir todas as tabelas tocadas. Incluir 0119, 0123 e 0126 na atomicidade do guard mesmo que seus estreitamentos incompatíveis tendam a falhar fechados.

Não alterar funções de upgrade, histórico aplicado, schemas de produção, containers, serviços, filas nem documentos/allowlists de deploy fora do escopo de deployment-operations.

## Validação

- Revisão estática confirma que o lock é tentado antes do primeiro guard em cada downgrade protegido e inclui as tabelas fonte e alvo.
- Testes PostgreSQL descartáveis devem comprovar lock conflitante aborta antes do guard/DDL, guard com dados recusa e preserva estado, e downgrade vazio conclui.
- Sem PostgreSQL exclusivo disponível, registrar essa prova como pendente; não iniciar serviço nem usar banco existente.
