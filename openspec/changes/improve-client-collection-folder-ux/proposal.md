# Proposal

## Why

No Acervo da cliente, abrir uma pasta ainda exige abrir outro painel para ver o processamento, e o envio de fotos não mostra avanço suficiente. As miniaturas e o comparativo são pequenos para conferir no computador. A opção de incluir outra cliente na pasta contraria o uso exclusivo que o fotógrafo deseja para pastas criadas nesse Acervo.

## What Changes

- Mostrar o processamento diretamente ao abrir a pasta no Acervo, mantendo o carregamento sob demanda e sem alterar a etapa Imagens.
- Ampliar as prévias administrativas da pasta e o antes/depois em diálogo acessível, sem expor originais.
- Iniciar o upload ao escolher JPEGs, apresentar progresso real do lote e estado claro de espera, falha e conclusão, preservando retentativa e identidade estável do arquivo.
- **BREAKING:** novas pastas restritas do Acervo pertencem a uma só cliente; a API recusa atribuição adicional. Remover o controle “Adicionar cliente” do card. Pastas já compartilhadas continuam acessíveis sem conversão ou revogação automática.

## Capabilities

### New Capabilities

- `media-storage/client-collection-workflow`: interação administrativa para abrir, enviar e conferir fotos e processamento no Acervo.

### Modified Capabilities

- `client-access/folder-audiences`: novas pastas restritas do Acervo são exclusivas, preservando vínculos compartilhados existentes.

## Impact

Componentes do Acervo, painel de processamento, upload de JPEGs e seus testes; endpoint administrativo de atribuição de cliente à pasta e testes de autorização/compatibilidade. Sem migration destrutiva, mudanças em originais, dados comerciais, notificações ou acesso da cliente às pastas já autorizadas.
