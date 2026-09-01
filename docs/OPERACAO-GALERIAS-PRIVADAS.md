# Operação de galerias privadas

## Fluxo do fotógrafo

Na área administrativa, configure primeiro a **Galeria pública** e publique as
fotos prontas na etapa **Imagens e pastas**. Depois, na etapa **Clientes e
acesso**:

1. cadastre ou vincule a cliente por nome e WhatsApp; o servidor normaliza o
   número para o formato internacional e evita duplicação por telefone;
2. escolha **Disponibilizar fotos** e marque somente o conteúdo destinado a
   essa cliente;
3. confirme a operação para criar ou reutilizar a privada derivada, sem copiar
   a mídia e sem transformar disponibilidade em seleção ou compra;
4. acompanhe no card os contadores e os estados de acesso e pagamento;
5. use **Desvincular cliente** quando necessário e acompanhe a operação
   assíncrona; cadastro e histórico comercial permanecem preservados.

A própria cliente também pode iniciar a privada ao selecionar uma foto
autorizada da Galeria pública. Uma privada administrativa pode permanecer com
zero seleções enquanto conservar fotos disponibilizadas pelo fotógrafo.

## Proteção de mídia

O JPEG original é armazenado em área privada e não é exposto pela interface ou
por uma URL pública. O processamento produz apenas derivados: miniatura, prévia
com marca d'água para a cliente e prévia administrativa sem marca para
conferência do fotógrafo. A privada referencia a mesma foto da origem; não há
duplicação do original. Excluir a Galeria pública preserva a única cópia ainda
referenciada por uma privada ou por histórico comercial.

## Experiência da cliente

A cliente autenticada encontra a biblioteca com as galerias ativas e o
histórico de compras. Na galeria, o prazo de seleção, as permissões de favoritos
e comentários e a mensagem do fotógrafo são entregues pelo backend; não há
estados comerciais simulados no frontend. Ela pode voltar à Galeria pública
para escolher novas fotos, que entram na privada correspondente àquela origem.

Consulte também
[`OPERACAO-EDITOR-GALERIA-E-PAGAMENTOS.md`](OPERACAO-EDITOR-GALERIA-E-PAGAMENTOS.md)
e [`CICLO-DE-VIDA-E-ACESSO-DE-GALERIAS.md`](CICLO-DE-VIDA-E-ACESSO-DE-GALERIAS.md).
