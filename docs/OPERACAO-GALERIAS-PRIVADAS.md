# Operação de galerias privadas

## Fluxo do fotógrafo

Uma galeria privada reúne duas origens legítimas, sem confundi-las:

- as fotos que a própria cliente seleciona na Galeria pública entram
  automaticamente em sua privada correspondente;
- o fotógrafo pode criar pastas privadas e enviar JPEGs novos do próprio
  dispositivo diretamente para aquela privada.

Na etapa **Clientes e acesso** da Galeria pública:

1. cadastre ou vincule a cliente por nome e WhatsApp; o servidor normaliza o
   número para o formato internacional e evita duplicação por telefone;
2. escolha **Criar galeria privada** para abrir uma privada vazia quando ela
   ainda não existir;
3. acompanhe no card os contadores e os estados de acesso e pagamento;
4. abra a ficha privada para criar pastas e enviar JPEGs novos do dispositivo,
   quando desejar montar um acervo administrativo próprio;
5. use **Desvincular cliente** quando necessário e acompanhe a operação
   assíncrona; cadastro e histórico comercial permanecem preservados.

A própria cliente também pode iniciar a privada ao selecionar uma foto
autorizada da Galeria pública. Essa entrada é automática e continua sendo a
origem normal das escolhas feitas pela cliente. O administrador não recebe um
catálogo para escolher manualmente fotos já existentes na Galeria pública ou
em outra privada.

## Proteção de mídia

O JPEG original é armazenado em área privada e não é exposto pela interface ou
por uma URL pública. O processamento produz apenas derivados: miniatura, prévia
com marca d'água para a cliente e prévia administrativa sem marca para
conferência do fotógrafo. Uma seleção da cliente referencia a foto pública sem
duplicar o original; um upload administrativo novo pertence exclusivamente à
privada e não aparece na pública nem pode ser reutilizado em outra privada.

## Experiência da cliente

A cliente autenticada encontra a biblioteca com as galerias ativas e o
histórico de compras. Na galeria, o prazo de seleção, as permissões de favoritos
e comentários e a mensagem do fotógrafo são entregues pelo backend; não há
estados comerciais simulados no frontend. Ela pode voltar à Galeria pública
para escolher novas fotos, que entram automaticamente na privada correspondente
àquela origem.

Consulte também
[`OPERACAO-EDITOR-GALERIA-E-PAGAMENTOS.md`](OPERACAO-EDITOR-GALERIA-E-PAGAMENTOS.md)
e [`CICLO-DE-VIDA-E-ACESSO-DE-GALERIAS.md`](CICLO-DE-VIDA-E-ACESSO-DE-GALERIAS.md).
