## Decisões

### HTML autônomo em vez de PDF

O backend SHALL consultar itens congelados de pedidos confirmados da cliente e galeria autorizadas, gerar HTML em memória e retornar `Content-Disposition: attachment`. Cada prévia histórica disponível terá prioridade; na ausência dela, o derivado administrativo `admin_preview` disponível será embutido como `data:image/jpeg;base64,...`, tornando o arquivo utilizável depois do download sem depender de sessão, URL ou armazenamento remoto. O HTML conterá CSS de impressão: quatro colunas em telas largas, três colunas em papel/viewport menor e duas colunas em telas muito estreitas. A data/hora usará `America/Sao_Paulo`.

O HTML será escapado com `html.escape` para nomes e metadados. A resposta não criará registro, caminho temporário ou job de limpeza. Fotos sem prévia disponível continuarão identificadas com um aviso no lugar da imagem, sem incluir original. Sem compra confirmada, a rota responderá conflito em vez de gerar arquivo vazio. TXT/CSV permanecerão como APIs legadas, mas desaparecerão da interface.

### Herança da apresentação privada

`DerivedGallery` não receberá uma nova configuração. A rota administrativa resolverá o `folder_display_mode` atual do `ParentGallery` e o retornará como `inherited_folder_display_mode`; a tela exibirá a regra como somente leitura. A rota de revisão da cliente continuará usando a mesma fonte de verdade.

### Liberação de pastas privadas

O endpoint existente de publicação será usado pela tela privada. A ação ficará disponível somente para pastas próprias em preparação; após resposta bem-sucedida, a tela recarrega a pasta. O backend continuará exigindo a conclusão do processamento e manterá a mesma autorização administrativa. Não haverá publicação automática silenciosa.

### “Minha galeria” e “Compras”

Não remover nem redirecionar `/gallery/[galleryId]`. A galeria privada é a superfície de seleção, filtros, prazo e reabertura; `/library/purchases` é o histórico de pedidos e entregas. A sobreposição de miniaturas de pedidos não elimina os casos de uso da galeria.
