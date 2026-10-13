## Context

A etapa Imagens atualmente combina painéis de galeria com um painel específico da pasta selecionada. O upload mantém contagem em estado temporário no editor, enquanto consultas de processamento podem atualizar a lista inteira de pastas. A base integrada `4fe9b68` já contém configuração independente em `FolderProcessingSettings` para pastas comuns e restritas, com `tenant_id` imposto pelo backend. A duplicação é da interface, e o salvamento/reprocessamento automático ainda é oferecido apenas às pastas restritas. A atualização periódica limpa a grade e pode interromper visualmente o estado local do upload.

## Decisions

1. **Um painel contextual compartilhado.** A etapa terá uma única área de processamento. Ela consulta a pasta selecionada e mostra, para qualquer pasta de conteúdo pública ou privada, o estado/progresso facial e de prévias e os parâmetros de intensidade/exposição daquela pasta. A listagem administrativa aceita `include_restricted=true` para incluir as pastas restritas da mesma galeria, mantendo o comportamento padrão dos outros consumidores; o editor percorre a paginação existente para não esconder pastas após o primeiro limite; os cards de clientes apontam para Imagens com `folder=<id>`, sem repetir controles. A lista de pastas permanece compacta e pode mostrar contagem/resumo de upload sem repetir os controles.
2. **Isolamento por identidade de pasta.** `PhotoFolder.id` identifica configuração e progresso. A seleção de outra pasta troca os dados apresentados, sem compartilhar estado de configuração ou fila. Reconhecimento continua automático conforme o gate global e não ganha controles locais de permissão/pausa.
3. **Reutilizar o contrato integrado.** Usar `GET/PATCH /admin/photo-folders/{id}/processing` e `FolderProcessingSettings` existentes. Não criar uma segunda tabela ou migration: a base atual já possui defaults independentes de 50%/0 EV para pastas comuns e 75%/0 EV para restritas, autorização por fotógrafo e geração por pasta. A galeria privada derivada é legado comercial; o painel desta change opera pastas comuns/restritas do editor unificado, sem redefinir esse legado.
4. **Salvamento e reprocessamento automáticos.** O controle aplica debounce curto, persiste a nova configuração e enfileira novamente somente fotos elegíveis da pasta selecionada a partir da fonte limpa. Gerações antigas são invalidadas conforme o mecanismo já existente. Não há ação para processar a galeria inteira.
5. **Progresso de upload independente da seleção.** O estado real do lote ativo é indexado pela pasta de destino e renderizado fora do conteúdo condicional da pasta aberta. Trocar pasta não oculta o lote anterior. O polling atualiza os resumos afetados sem ativar estado de carregamento de página nem substituir o editor inteiro; a tela mantém estrutura e foco durante o upload.
6. **Limpeza restrita.** Remover somente os painéis globais que passam a duplicar o painel contextual e o código de interface que ficar comprovadamente sem uso nesta etapa. Não reorganizar outros componentes nem renomear módulos fora do necessário.

## Alternatives

- **Manter controles públicos por galeria e privados por pasta:** rejeitada porque não oferece o mesmo modelo para todos os tipos e mantém os cartões duplicados.
- **Mostrar controles repetidos dentro de cada card de pasta:** rejeitada por alongar a página no celular, especialmente com muitas pastas.
- **Fazer polling recarregando o editor completo:** rejeitada porque pode piscar a tela e interromper a apresentação do contador do lote.

## Risks / Trade-offs

- A base de execução deve ser o worktree integrado em `4fe9b68`. O checkout principal está defasado e não pode receber a release desta change; os testes feitos nele são somente evidência exploratória do sintoma, não validação da versão final.
- Mudanças de parâmetros durante jobs em andamento devem continuar protegidas por geração/fingerprint para impedir publicação obsoleta.
- O estado do upload no navegador não equivale a um job retomável após fechar/atualizar a página; esta change garante continuidade enquanto o editor permanece aberto e não cria um protocolo de retomada novo.
- A identidade do painel deve deixar claro o nome da pasta selecionada e usar estados acessíveis de carregamento, erro, sucesso e progresso.

## Photographer isolation and shared workers

O painel é reutilizado pela seleção, mas a identidade de configuração é fotógrafo + pasta. O servidor deriva `tenant_id` da sessão e revalida a propriedade em leitura, gravação e reprocessamento. Os workers existentes podem consumir a fila compartilhada de vários fotógrafos, com jobs, fontes, parâmetros, proteção e publicação associados ao proprietário persistido; não instanciar um motor persistente por pasta nem mudar quotas, fairness ou concorrência operacional nesta change. Testar IDs de outro fotógrafo recusados e alterações sem efeito sobre a fila/configuração dele.

## System Monitor

Preservar o escopo de autorização e de agregação já definido pelo Monitor do sistema. Mudar a pasta selecionada consulta estados, sem criar jobs ou registrar trabalho executado. Uma alteração real de parâmetros invalida/reagenda a geração da pasta, refletida na fila monitorada. Contadores de fila representam jobs; telemetria de trabalho representa tentativas realmente executadas, incluindo reprocessamento, sem criar métricas por cada renderização da interface.
