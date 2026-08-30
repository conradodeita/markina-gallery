# Operação de galerias privadas

## Fluxo do fotógrafo

Na área administrativa, abra **Nova galeria privada**. O fluxo é guiado e sempre usa os dados autorizados pelo backend:

1. Cadastre o cliente com nome e WhatsApp. O número pode ser digitado com espaços ou hífen; o sistema o normaliza para o formato internacional antes de gravar.
2. Crie o acervo-mãe do evento.
3. Selecione o acervo e importe os JPEGs. Cada arquivo é limitado a 25 MB, deve ser uma imagem JPEG válida e entra em processamento assíncrono.
4. Aguarde o estado `completed` antes de usar as prévias. Em caso de `failed`, importe novamente o arquivo correto.
5. Escolha o cliente, as fotos processadas e as permissões de favoritos e comentários para criar a galeria privada derivada.

## Proteção de mídia

O JPEG original é armazenado em área privada e não é exposto pela interface ou por uma URL pública. O processamento produz apenas derivados: miniatura, prévia com marca d'água para a cliente e prévia administrativa sem marca para conferência do fotógrafo.

## Experiência da cliente

A cliente autenticada encontra a biblioteca com as galerias ativas e o histórico de compras. Na galeria, o prazo de seleção, as permissões de favoritos e comentários e a mensagem do fotógrafo são entregues pelo backend; não há estados comerciais simulados no frontend.
