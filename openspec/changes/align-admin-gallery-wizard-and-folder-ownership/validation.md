# Roteiro de validação do fotógrafo

Use somente uma galeria e clientes de teste. Não use fotos de pessoas reais nem dados de produção.

1. Entre em **Administração → Galerias** e escolha **Nova galeria**. Informe título, evento e descrição. Confirme que o novo endereço começa pela etapa **Ajustes**.
2. Navegue pelas cinco etapas. Em **Vendas** e **Detalhes**, confirme que há uma mensagem clara de indisponibilidade, sem preço, cobrança ou personalização fictícia.
3. Em **Imagens**, crie duas pastas. Envie JPEGs apenas para a primeira; renomeie a segunda e confirme que ela pode ser apagada somente enquanto vazia e em preparação.
4. Em **Clientes**, procure pelo nome ou WhatsApp de uma cliente de teste, vincule-a, e confirme que o link é não listado. Crie uma segunda cliente, se necessário, para testar os responsáveis de uma mesma família.
5. Volte a **Imagens**, abra a primeira pasta e libere-a para uma das galerias privadas vinculadas. A pasta passa a `Liberada`; a outra, se existir, permanece administrativa e invisível para a cliente.
6. Faça login como a cliente de teste. Confirme que ela vê somente a galeria privada dela e as fotos da pasta liberada. Ela não deve ver originais, outras clientes, outras galerias privadas ou fotos de uma pasta ainda em preparação.
7. Retorne ao admin e tente criar pasta ou registrar foto depois de bloquear a galeria. O sistema deve recusar a escrita. Confirme também que a rota antiga de criação direta de foto não cria dados.

## Critérios de aceite

- Nenhuma pasta ou foto pode ser criada sem a galeria-mãe.
- Uma pasta só pode ser liberada para galerias privadas da mesma origem.
- O cliente precisa concluir o login antes de visualizar fotos.
- O link de uma galeria não a torna pesquisável publicamente.
- Prévia administrativa e arquivos do cliente continuam protegidos; o original não é exposto.
- Venda e aparência só serão ativadas quando os contratos próprios existirem e forem aprovados.

## Evidências automatizadas desta aplicação

- `python -m pytest -q` em `backend`: 38 testes aprovados.
- `python -m ruff check app migrations tests` em `backend`: aprovado.
- `npm run lint`: aprovado, com sete avisos preexistentes sobre imagens/navegação em telas fora deste editor.
- `npm test -- --pool=threads --maxWorkers=1`: 14 testes aprovados.
- `npm run build`: aprovado.
