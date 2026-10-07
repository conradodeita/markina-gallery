## Context

A change `dark-mode-and-landscape-covers` já estabelece a preferência global Claro/Escuro/Sistema, o atributo no elemento raiz, tokens semânticos e a proteção de fotografias, logos e QR Codes. Esta change acrescenta uma dimensão visual independente, sem substituir nem reimplementar essa preferência.

## Goals / Non-Goals

**Goals:** adicionar três acabamentos pré-definidos que possam ser selecionados em conjunto com qualquer modo de aparência; aplicar o acabamento consistentemente nas áreas administrativa e do cliente.

**Non-Goals:** criar paleta livre, CSS customizado, sincronização entre dispositivos, preferências de conta/galeria ou mudança das cores das mídias.

## Decisions

1. Representar o acabamento por um valor enumerado e controlado no elemento raiz, separado do modo claro/escuro. Usar tokens CSS semânticos para fundo de página, superfícies, texto principal, texto secundário e realces, sem espalhar cores literais pelas telas.
2. Oferecer Neutro (padrão atual), Cinza metálico, Azul metálico e Vinho metálico. Cada acabamento define pares coordenados de cores para superfícies e textos em cada modo. Usar gradientes discretos somente nas superfícies aprovadas; campos de texto, diálogos densos e regiões que exigem alto contraste podem manter fundo sólido derivado da mesma paleta.
3. Persistir o modo e o acabamento como preferências locais independentes. Falha de armazenamento não pode impedir a interface de carregar nem o controle de funcionar durante a sessão. Usar Neutro quando não houver valor salvo ou quando o valor for inválido.
4. No modo Escuro, preservar a luminância escura das superfícies e usar a cor selecionada apenas em tokens compatíveis de borda/realce; não transformar fundos escuros em painéis claros.
5. Atualizar as cores do texto principal e secundário junto com o acabamento selecionado, considerando o modo claro/escuro e a superfície onde o texto aparece. Preservar hierarquia, legibilidade, contraste e foco visível em cada combinação.
6. Não aplicar filtros ou estilos de tema a fotografias, logos, favicons, QR Codes ou ativos protegidos. Preservar as regras de contraste e foco estabelecidas para o design system.

## Risks / Trade-offs

- Cada acabamento em dois temas amplia a matriz visual; cobrir os quatro acabamentos nos três modos e larguras de tela representativas.
- Uma aparência metálica muito marcada pode competir com fotos; manter os gradientes discretos e aplicados a áreas de interface, não às imagens.

## Migration Plan

Sem migration de banco ou alteração de API. Preferências antigas de Claro/Escuro/Sistema continuam válidas; acabamento ausente ou desconhecido resolve para Neutro. Rollback remove os novos tokens e controles, mantendo a preferência de modo já existente.
