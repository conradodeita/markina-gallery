## Context

A regra global de tema escuro seleciona todos os inputs/selects/textareas, inclusive os DOM fields do SDK. O Brick padrão mantém texto próprio escuro, causando mistura de cores. A presença de controller.current não comprova onReady. O timer só começa após carregamento do script e o effect depende do callback onSubmit.

## Decisions

Usar tema oficial default via customization.visual.style e uma superfície clara isolada no wrapper próprio, com regras de elementos HTML e sem seletores gerados pelo SDK. Nenhum acesso ao conteúdo de cartão nos iframes. onReady é a única evidência de campos prontos. Timeout de 20 segundos cobre desde a montagem do componente, oferece recarga completa explícita e não cria nova tentativa ou cobrança por si. Manter serialização create/unmount atual para evitar instâncias concorrentes; callback via ref preserva atualização sem remontagem por identidade de função.

Não atribuir causa única à automação: o comportamento intermitente foi observado, mas não há prova de causalidade. Corrigir os defeitos reproduzíveis e registrar qualquer limite do ensaio real.

## Validation

Testes focados devem reproduzir controlador resolvido sem onReady, script indisponível, onReady tardio, mudança de callback sem recriar Brick e limpeza da instância. Build/lint e inspeção visual dos campos. Reutilizar testes financeiros já validados. Revisar diff por regressões e não ampliar refatoração além do wrapper afetado.

## Deployment

Somente web, sem migration nesta change; depende de inventário remoto atualizado e coordenação com o executor da 0090. Preservar PIX, restrição de teste ao proprietário e bloqueio de cobranças reais. Verificação autenticada de layouts PR295 e campos após publicação permanece pendente até efetiva observação.
