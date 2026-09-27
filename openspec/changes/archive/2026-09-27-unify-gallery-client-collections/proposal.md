# Proposal

## Why

A distinção operacional entre Galeria pública e galeria privada derivada duplica telas, vínculos e caminhos de acesso, embora a seleção e o histórico comercial já sejam individuais por cliente. Uma única galeria com pastas comuns ou atribuídas a clientes permite organizar o acervo sem criar outra galeria para cada jornada.

## What Changes

- **BREAKING**: encerrar a criação e a navegação de galerias privadas derivadas como conceito do produto. A Galeria pública autenticada torna-se a única galeria operacional; nenhuma primeira seleção cria uma derivada. O nome de produto “Galeria pública” continua significando acervo não listado, acessível só após OTP e vínculo autorizado.
- Adicionar a cada pasta de conteúdo o público `todos os clientes vinculados` ou `clientes escolhidos`. Uma cliente vê as pastas comuns e somente as exclusivas atribuídas a ela; uma pasta exclusiva pode servir uma ou várias clientes. Toda pasta nova começa em preparação, sem exposição, até escolha explícita do público e liberação.
- Preservar a apresentação da área **“Coleção”** no acesso da cliente: nela aparecem, na mesma navegação de pastas existente, as pastas comuns da galeria e as pastas restritas atribuídas à cliente autenticada.
- Eliminar da navegação a página separada “Minha galeria”: ações sobre fotos ainda disponíveis (seleção, favoritos, comentários e pedido de novo prazo) permanecem na Coleção; revisão e PIX ficam no Carrinho; pedidos, estados de pagamento e entregas ficam em Compras. Links legados devem levar a cliente autenticada ao destino correspondente sem expor dados de outra pessoa.
- Manter seleção, favoritos, visualizações, comentários, carrinho, pedidos, entrega, prazo e histórico separados por `galeria + cliente`, sem transformar seleção pública em cópia de foto ou galeria. Preservar o isolamento e os snapshots comerciais confirmados fora da limpeza pontual de homologação.
- Na etapa Clientes da Galeria pública, substituir o caminho “Galeria privada · acervo da cliente” por uma seção recolhível **“Acervo da cliente”** no card correspondente. Criar pastas restritas e enviar seus JPEGs nesse card; a pasta nasce atribuída àquela cliente e pode receber outras clientes sem duplicação. Mostrar ali fotos, estados e ações individuais. Pastas comuns continuam na etapa Imagens; retirar links, botões e textos de criação/abertura de galeria privada.
- Aplicar a autorização de pasta no backend a listagens, URL de prévia, busca facial, seleção, carrinho, exportação e notificações. Corrigir a rota de prévia pública que hoje não confirma explicitamente o escopo comum da foto.
- Fazer uma limpeza destrutiva e inventariada **somente em homologação** dos dados de teste: galerias, pastas, fotos, clientes, seleções, compras, pedidos, entregas, interações e históricos operacionais relacionados, arquivos fotográficos e filas correspondentes. Entregar homologação vazia de galerias, clientes e fotos. Preservar conta e sessões administrativas, 2FA, login/instância Evolution, segredos, todas as configurações globais e recursos de outros projetos. Por decisão explícita do proprietário, não criar novo backup para esta limpeza; não excluir backups preexistentes nem dados de produção. Em 27/09, após ver o inventário zerado e conferir o estado vazio pela interface, o proprietário dispensou a validação adicional com dados sintéticos temporários e sua segunda limpeza.
- Substituir nos documentos arquiteturais as regras que exigem a derivação. Descontinuar referências técnicas legadas por etapas, sem migration destrutiva de produção ou exclusão implícita de histórico fora da homologação autorizada.

## Capabilities

### New Capabilities

- `client-access/folder-audiences`: público comum ou lista de clientes por pasta, com autorização individual em todos os caminhos de leitura e interação.

### Modified Capabilities

- `client-access/cloned-private-galleries`: substituir propriedade, clonagem e entrada por derivada por vínculo individual na galeria única; manter isolamento e troca segura de telefone.
- `client-access/derived-galleries`: substituir biblioteca e permissões de derivadas pela jornada individual na galeria única e histórico autorizado.
- `gallery-sales/operational-gallery-interface`: concentrar a operação no editor da Galeria pública e no “Acervo da cliente” recolhível.
- `gallery-sales/client-selection-operations`: associar a ficha e as ações comerciais a `galeria + cliente`, sem galeria derivada.
- `gallery-sales/original-gallery-experience`: apresentar uma única jornada por galeria à cliente.
- `media-storage/protected-previews`: exigir o público da pasta também na entrega direta da prévia.
- `media-storage/staged-folder-release`: liberar uma pasta somente após definir e validar seu público.
- `deployment-operations`: especificar a limpeza controlada dos dados de teste em homologação, com inventário e preservação comprovada dos recursos administrativos e configurações.

## Impact

- Backend: modelos e migration aditiva de público de pasta, autorização central, API de galeria/cliente, comércio, busca facial, notificações, lifecycle e limpeza homologada.
- Frontend: editor de pastas comuns e cards de clientes com criação/upload de pastas restritas em Galerias públicas, galeria e biblioteca da cliente, navegação e textos sem galeria privada.
- Operação: OpenSpec, mandato/roadmap, testes de isolamento com duas ou mais clientes, CI e validação em homologação após inventário e aprovação do plano de impacto zero.
