## Why

A biblioteca da cliente demora a apresentar conteúdo porque bloqueia toda a página enquanto carrega jornadas e histórico comercial, e hoje a conferência de pedidos usa um visualizador sequencial que oculta o conjunto comprado. A galeria privada também mistura estados de navegação com estados comerciais, mantém uma capa vazia sem função e não diferencia visualmente pedidos aguardando pagamento, informados e confirmados.

## What Changes

- Fazer `/library` apresentar a jornada autorizada assim que seus dados essenciais chegarem, carregando o histórico comercial de forma progressiva e oferecendo feedback imediato durante a navegação.
- Medir e limitar regressões nas consultas autenticadas da biblioteca, preservando projeções em lote e evitando que o frontend espere dados que não são necessários para a primeira renderização útil.
- Corrigir ações cujo texto fica invisível por conflito de estilos, garantindo rótulo visível, contraste e nome acessível.
- Manter cada pedido comercialmente separado e, ao abrir `Ver fotos`, exibir todas as fotos daquele pedido em uma grade de quatro colunas no desktop e duas no mobile, preservando ampliação individual.
- Remover somente da galeria privada da cliente a composição de capa vazia, sem alterar capas da Galeria pública ou superfícies administrativas.
- Substituir os filtros principais incompatíveis por estados comerciais coerentes: carrinho, aguardando pagamento, pagamento informado e compradas, com contagens derivadas do backend.
- Aumentar o espaçamento entre pedidos e aplicar diferenciação visual por estado no acompanhamento de pagamento.
- Validar a mudança com testes cirúrgicos das rotas, componentes e projeções afetadas, sem executar suítes completas quando não houver evidência de risco compartilhado.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `client-access/derived-galleries`: tornar a biblioteca progressiva, acessível e capaz de retomar pedidos separados com todas as fotos visíveis em grade responsiva.
- `gallery-sales/original-gallery-experience`: alinhar a galeria privada aos estados comerciais reais, retirar a capa sem função nessa superfície e diferenciar visualmente o acompanhamento dos pedidos.

## Impact

- Página Next.js da biblioteca, estado de carregamento da rota, shell/links da cliente e estilos compartilhados de ações e grades.
- Página privada da galeria, componente compartilhado de apresentação fotográfica e estilos dos filtros e pedidos.
- Contratos FastAPI de `/library`, `/library/purchases` e projeções comerciais apenas se a medição focada demonstrar consulta redundante ou N+1; nenhuma mudança de autorização ou estado financeiro.
- Testes frontend direcionados da biblioteca, galeria privada, apresentação e pedidos; testes backend direcionados de tempo/quantidade de consultas; lint, typecheck e validação OpenSpec dos arquivos tocados.
- Sem migration prevista, sem alteração em reconhecimento facial, preços, PIX, WhatsApp, mídia, dados existentes ou infraestrutura.
