## Why

A ação “Abrir seleção individual” leva o fotógrafo a uma tela com exportações TXT/CSV que não ajudam na conferência visual e podem gerar arquivos vazios quando a seleção retornada não contém linhas exportáveis. O fotógrafo precisa de um registro visual portátil do pedido, com as prévias protegidas e os nomes das fotos, sem deixar arquivos temporários no servidor.

Na operação de galerias privadas, a configuração de organização das pastas já é herdada da Galeria pública na resposta autorizada da cliente, mas essa regra não é visível na administração. Além disso, o fluxo administrativo não oferece a publicação explícita de uma pasta privada criada e carregada pelo fotógrafo; a pasta permanece em preparação e não aparece para a cliente.

## What Changes

- Substituir a ação “Abrir seleção individual” por “Baixar seleção individual”, disponível quando houver compra confirmada.
- Gerar um HTML autônomo em memória a partir dos itens de pedidos confirmados, com data/hora de geração, nome da galeria e cliente, prévias embutidas, nome congelado de cada foto e grade responsiva de três colunas na impressão e quatro colunas em telas largas.
- Manter a auditoria da exportação e evitar qualquer gravação do arquivo gerado no armazenamento do servidor.
- Exibir na área administrativa da galeria privada a organização herdada da Galeria pública.
- Permitir ao administrador liberar explicitamente uma pasta privada após o processamento, para que ela passe a aparecer na apresentação da cliente com a configuração herdada.
- Manter “Minha galeria” enquanto superfície operacional de seleção; não redirecioná-la para “Compras”, pois as duas páginas têm finalidades distintas.

## Capabilities

### Modified Capabilities

- `gallery-sales/client-selection-operations`: baixar ficha visual portátil da seleção.
- `client-access/derived-galleries`: apresentar novas pastas privadas liberadas na mesma organização herdada da origem.
- `gallery-visualization-and-watermark-controls`: tornar explícita a herança do modo de pastas na administração privada.

## Impact

- Rota FastAPI de seleção individual e página administrativa correspondente.
- Rota de detalhe da galeria privada e componentes administrativos de pastas.
- Testes backend e frontend direcionados.
- Sem migration, sem arquivos temporários persistentes e sem alteração financeira ou de autorização.
