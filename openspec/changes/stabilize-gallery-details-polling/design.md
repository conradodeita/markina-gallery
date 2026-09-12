## Context

Veja `proposal.md` e a delta spec. O editor usa um único contador de atualização para todos os passos. Quando a Etapa 03 encontra uma capa `processing`, agenda nova consulta; o efeito de dados reage ao contador marcando `loading=true`, e o retorno antecipado substitui toda a página pelo estado `Abrindo a galeria`. A resposta também reinicializa a prévia visual, ainda que o fotógrafo esteja editando os controles.

## Goals / Non-Goals

**Goals:**

- distinguir a primeira abertura de uma sincronização em segundo plano;
- limitar a atualização automática ao estado remoto da capa;
- preservar estado local e interação durante o processamento;
- encerrar timers e ignorar respostas obsoletas com segurança.

**Non-Goals:**

- alterar o endpoint de detalhes ou o worker de derivados;
- mudar frequência, formato ou regras de processamento da capa além do necessário para estabilidade;
- modificar polling das etapas 04 e 05 sem evidência de que compartilham o mesmo defeito.

## Decisions

### Polling da capa usa carregamento silencioso e escopo próprio

O carregamento inicial continuará controlando a tela global. Depois que o editor e os detalhes existirem, o timer consultará somente os detalhes da Etapa 03 e atualizará apenas capa/configuração remota necessária, sem alternar o estado global de carregamento.

Alternativa descartada: esconder visualmente o estado `Abrindo a galeria` por CSS. O formulário continuaria desmontado no DOM, perdendo foco e edição.

### Estado editável não é reinicializado por resposta de acompanhamento

A prévia local e os campos do formulário serão inicializados na primeira carga ou após salvamento explícito. Respostas de polling não sobrescreverão valores não salvos; apenas o estado do ativo de capa e sua URL poderão mudar.

Alternativa descartada: reaplicar todos os dados do editor em cada resposta. Isso conserva o risco de apagar alterações locais e muda o foco mesmo sem tela de loading.

### Timer observa estado terminal e ciclo de vida da rota

Haverá no máximo um timer ativo. A consulta será cancelada ou sua resposta ignorada quando o componente desmontar, o passo mudar ou uma requisição mais recente prevalecer. Estados `ready` e `failed` encerram o ciclo; erro transitório usa estado local recuperável.

Alternativa descartada: intervalo permanente. Ele gera tráfego desnecessário e pode aplicar respostas fora de ordem.

## Risks / Trade-offs

- [Resposta antiga substituir a capa nova] → associar cada ciclo à intenção/carga vigente e ignorar resultado obsoleto.
- [Campos controlados e não controlados divergirem] → testar edição antes e durante duas respostas de polling.
- [Falha transitória encerrar acompanhamento cedo demais] → disponibilizar retentativa local sem derrubar o editor.
- [Timer continuar após navegação] → limpar timeout e invalidar requisições no cleanup do efeito.

## Migration Plan

1. Criar testes com temporizadores controlados que reproduzam o piscar atual.
2. Separar carga inicial e sincronização silenciosa da Etapa 03.
3. Validar processamento, conclusão, falha transitória, edição, foco e desmontagem.
4. Publicar somente frontend, sem migration nem reprocessamento; rollback retorna ao bundle anterior.
