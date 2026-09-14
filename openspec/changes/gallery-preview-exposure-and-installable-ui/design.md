## Context

O módulo inicial está publicado com configuração global e worker separado. O proprietário avaliou o resultado e pediu exposição e controle por galeria, além de UI menos monocromática e instalação PWA. A avaliação estética da change anterior permanece aberta, não sendo critério de correção técnica desta evolução.

## Goals / Non-Goals

Isolar ajustes, preservar fonte limpa e fallback, melhorar hierarquia e oferecer instalação real. Não importar XMP, alterar biometria, fazer edição final ou criar armazenamento offline de acervos.

## Decisions

Refinamento posterior à primeira validação: a base das páginas usa cinza claro neutro, não bege. Bege fica em ações secundárias. Os ícones vêm do upload administrativo existente: favicon original e app-icon convertido sob demanda para PNG 180/192/512, sem corte/distorção nem alteração da fonte, com margem transparente para artes retangulares. URLs públicas de marca revalidam conteúdo, sem cache de cinco minutos; manifesto e metadata apontam para essas rotas. Remover o ícone gerado nesta change. Sem arte configurada, responder 404, sem inventar substituta. Instalações já existentes podem depender do ciclo de atualização do navegador/SO.

1. Tabela nova de configuração por ParentGallery: enabled, strength (10–75), exposure em décimos de EV (-20 a 20), generation e updated_at. Migration copia o singleton anterior para galerias existentes com exposição zero, preservando gerações e resultados. Novas galerias começam desligadas. A tabela antiga é mantida somente para reversibilidade da migration; API global deixa de alterar estado.
2. Cada foto usa a configuração de sua galeria de origem. Referências da seleção privada recebem a mesma prévia; uploads privados pertencentes ao mesmo parent seguem esse escopo. A configuração da galeria B não cancela nem invalida A. Locks e geração impedem publicação obsoleta. A limpeza exclusiva exige todas as configurações desligadas e worker parado.
3. Exposição é compensação após mistura automática: converter sRGB para luz linear, multiplicar por 2^EV e voltar a sRGB com limites. Zero preserva os pixels; ajustes extremos podem recortar altas luzes. A fonte de cada re-run é sempre a prévia limpa; proteção aplicada por último.
4. Painel na etapa 04 recebe galleryId fixo. Salvar aplica às novas fotos; botão explícito processa/reprocessa as existentes com paginação, progresso e antes/depois. Não salvar automaticamente ao arrastar sliders. Bloquear processamento de valores não salvos.
5. Identidade definida pelo proprietário: preto e amarelo, com cinza e bege nas superfícies. Substitui a proposta inicial verde-petróleo. Amarelo nas ações/destaques com texto preto; amarelo escuro para links sobre fundos claros; cartões em branco/cinza/bege, com preto para hierarquia. Cores semânticas de sucesso/erro apenas nos respectivos estados, não como tema. Tokens e estilos compartilhados antes de exceções locais; fotos continuam neutras, temas configurados das galerias preservados, foco/contraste e largura fluida mantidos. Ícone, manifesto e aviso offline seguem a mesma identidade.
6. Manifesto com identidade estável e start_url neutra `/`, ícones oficiais enviados em Configurações adaptados para 192/512 e Apple, standalone. Componente de instalação no topo, sem popup automático: prompt nativo quando disponível; instrução para instalação manual nos navegadores reconhecidos. Ocultar em standalone ou após instalação nesta sessão. Nunca prometer instalação nativa universal.
7. Service worker não persiste respostas, fotos, API, HTML autenticado ou tokens. Intercepta somente navegação documental para oferecer HTML offline neutro gerado no próprio script, sem dados do usuário. Nenhum cache de aplicação é criado. Fluxos online existentes seguem intactos.

## Risks / Trade-offs

- Após copiar os valores, a migration desliga o singleton legado: reinício acidental de worker antigo não deve admitir trabalho global. Essa defesa não substitui parar/atualizar o worker na publicação.

- Exposição não recupera informação perdida; avaliação fotográfica continua humana.
- O worker antigo não entende a nova configuração: publicação deve parar somente esse worker, migrar API e reconstruí-lo antes de retomar. Sem exclusão de filas/fotos.
- Instalação depende do navegador/HTTPS; iOS usa menu de compartilhamento. Offline não permite trabalhar no acervo.
- Migration preserva valores globais apenas para galerias já existentes; não reprocessa automaticamente.

## Validation

Testes focados de isolamento, geração, exposição, fallback/limpeza, endpoints, painel, instalação e privacidade do worker; migration temporária, lint/typecheck/build e inspeção visual mobile/desktop. Sem suíte geral local nem benchmark. Registrar limitações e evidências em tasks.
