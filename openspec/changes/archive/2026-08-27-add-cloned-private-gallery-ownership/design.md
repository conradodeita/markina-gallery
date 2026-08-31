## Context

O modelo existente já separa `ParentGallery`, `PhotoAsset` e `DerivedGallery`, mas a tentativa local de tornar `GalleryAccess` um acesso múltiplo para uma mesma galeria derivada conflita com a decisão de negócio. Veja `proposal.md` e as delta specs para o comportamento requerido.

## Goals / Non-Goals

**Goals:**

- Preservar `DerivedGallery.client_id` como a única proprietária da galeria privada.
- Reutilizar `PhotoAsset` e `DerivedGalleryPhoto` quando outra galeria privada for clonada.
- Separar o registro de entrada pelo link não listado da autorização de uma galeria privada.
- Expor contratos backend-driven para o painel operacional e a biblioteca da cliente.
- Manter pedidos confirmados imutáveis e auditáveis na alteração de telefone.

**Non-Goals:**

- Não criar grade pública de acervo coletivo nem ativar busca facial.
- Não implementar upload por pastas, preço progressivo, checkout/PIX, WhatsApp ou entrega nesta mudança.
- Não migrar dados reais de clientes em homologação.

## Decisions

### Acervo-fonte, registro e galeria privada são recursos diferentes

`ParentGallery` continua sendo o acervo-fonte administrativo. Uma nova relação `ParentGalleryRegistration` registra que uma cliente passou pelo link não listado e concluiu o OTP, com estado `pending | active | blocked | expired`, origem e auditoria. Essa relação não autoriza leitura de fotos por si só.

`DerivedGallery` continua com uma única `client_id` proprietária. A autorização da cliente em rotas de galeria será conferida por igualdade com essa proprietária e pelas regras da galeria (`access_enabled`, prazo e estado), nunca por `GalleryAccess`. Uma migration manterá os dados legados de `GalleryAccess` para auditoria e deixará de usá-los como autorização de galeria privada.

Alternativa descartada: uma tabela N:N de acesso a `DerivedGallery`. Ela simplificaria a tela inicial, mas mistura carrinhos e históricos e não representa a compra independente de mãe e pai.

### Clonagem referencia fotos, não arquivos

Uma operação administrativa cria nova `DerivedGallery` para a cliente de destino, associa a mesma `parent_gallery_id` e copia apenas os registros `DerivedGalleryPhoto` escolhidos. Configurações de prazo, comentários, favoritos, mensagem e regras comerciais são copiadas por snapshot configurável; seleção, favoritos, comentários, visualizações e pedidos nunca são copiados.

A operação será idempotente por uma chave de solicitação administrativa, para que repetição de rede não crie galerias duplicadas. A API retornará a nova galeria e registrará os identificadores de origem/destino na auditoria.

### Estados de foto são derivados por cliente

Será criado `PhotoView` com unicidade `(derived_gallery_id, client_id, photo_asset_id)` e timestamp de primeira/última abertura ampliada. A resposta da galeria calcula `purchased` por itens de pedidos confirmados da mesma cliente, `viewed_not_purchased` por `PhotoView` sem compra e `new` na ausência de ambos. O carregamento de miniaturas não grava `PhotoView`.

O painel administrativo poderá agregar o número de vendas por `PhotoAsset`, mas o contrato enviado à cliente não conterá número, nome ou qualquer indício de compras por terceiros.

### Telefone é um contato verificável, não a identidade comercial

Uma tabela `ClientPhone` manterá telefones normalizados por cliente, com estado de verificação, vigência e rótulo de principal. O telefone ativo continuará único; um telefone histórico não poderá autenticar após ser substituído. Pedidos terão snapshot de nome e telefone da cliente no momento de sua confirmação para auditoria. A troca exige OTP no novo número e ação autenticada do fotógrafo; ela não funde clientes nem transfere galerias.

Alternativa descartada: alterar `Client.phone_e164` diretamente. Ela apagaria a evidência de contato usada em uma venda e impediria uma recuperação segura de histórico.

### Contratos administrativos e exportação

O backend fornecerá: lista paginada de galerias-fonte com busca/estado; detalhe de fonte com registros e galerias privadas; criação de cliente/registro e clonagem; ficha individual de seleção; e exportação TXT/CSV de identificadores. Prévia sem marca d'água será servida apenas pela rota administrativa já autenticada e ainda usará derivado local, nunca original ou Google Drive.

O frontend consome esses contratos sem mocks persistentes. A lista e a ficha distinguem `galeria-fonte` de `galeria privada da cliente`; ações de bloqueio, reativação, clonagem e troca de contato terão confirmação explícita.

## Risks / Trade-offs

- [Migração de autorizações provisórias] → preservar linhas legadas para auditoria, migrar somente relacionamentos comprovadamente proprietários e testar upgrade/downgrade em banco sintético.
- [Clonagem repetida por erro de rede] → chave de idempotência, índice de consulta e registro de auditoria.
- [Histórico de telefone interpretado como acesso de terceiro] → somente telefone ativo e verificado autentica; alteração exige vínculo administrativo e OTP.
- [Vazamento do acervo coletivo por link] → link registra intenção, mas nenhuma rota de foto do acervo-fonte é oferecida a cliente; somente galeria privada autorizada é renderizada.
- [Exportação contendo dados excessivos] → exportar apenas identificador/nome de arquivo e metadados da própria seleção, sob autorização administrativa e com auditoria.

## Migration Plan

1. Criar as tabelas e índices de registro de fonte, visualização e histórico de telefone, além dos snapshots comerciais necessários, sem apagar dados existentes.
2. Migrar clientes existentes para um telefone principal verificado conforme os dados atuais e preservar telefone/nome nos pedidos já confirmados.
3. Converter o uso de `GalleryAccess` para somente compatibilidade/auditoria e validar que cada galeria derivada existente mantém a proprietária original.
4. Publicar APIs e telas sem remover a rota anterior; migrar consumidores para a autorização por proprietária.
5. Após testes e homologação sintética, remover as rotas de acesso compartilhado não publicadas. Rollback: reverter código para a versão anterior; a migration é aditiva e não elimina registros.
