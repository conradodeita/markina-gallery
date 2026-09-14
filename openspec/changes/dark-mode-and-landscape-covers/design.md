## Context

Ver proposal.md. A base é develop após PR #82, com tokens claros compartilhados, mas ainda há cores literais em CSS global, módulos e componentes. O upload de capa registra um PhotoAsset em pasta `cover_assets` e envia bytes por `/admin/photo-assets/{id}/source`. A geração atual produz `admin_preview` limpo (máximo 2000 px) e `client_preview` protegido (1600 px). As rotas de capa do cliente ainda selecionam o derivado protegido.

## Goals / Non-Goals

**Goals:** tema global consistente; exceção estritamente contextual para capa; validação real de orientação, inclusive EXIF; reaproveitamento seguro dos derivados existentes.

**Non-Goals:** edição de fotos, recorte inteligente, upload de formatos novos, retirada da proteção do acervo, alteração de permissões, redesign de logo, mudança de regras financeiras/faciais ou ativação de qualquer job real nesta etapa.

## Decisions

1. Tema controlado por atributo no elemento raiz e tokens semânticos. Preferência local de três estados (claro/escuro/sistema), sem vínculo de conta; bootstrap mínimo antes da pintura para evitar flash, respeitando CSP e sem acesso a dados pessoais. Tratar falha de localStorage e ouvir mudança do sistema somente no modo Sistema. Alternativa de tema exclusivamente do sistema rejeitada porque não permite escolha explícita; filtro CSS global rejeitado por alterar fotografias e QR Code.
2. Revisar primeiro tokens e estilos compartilhados, depois cores literais nos módulos/telas. Preferência é global, não por galeria. Preservar cores de marca, mídias e personalização do título; usar superfícies escuras neutras e amarelo com contraste medido. Não basta trocar apenas o fundo do body. Controle compartilhado no topo sem competir com a instalação PWA.
3. Resolver capa por seu ID vigente no backend dentro de cada galeria já autorizada, e só então buscar `admin_preview` limpo. A rota de capa aceita somente ID da galeria, nunca parâmetro arbitrário para tornar uma foto limpa. Manter limite atual de 2000 px desse derivado, remoção de metadados, safe path, auditabilidade e headers privados; não reutilizar nem abrir o endpoint administrativo ao cliente. Alternativa de nova variante/recálculo em massa rejeitada porque a prévia limpa já existe. Se faltar, retornar indisponibilidade, nunca original. URLs administrativas que apontam a watermarked-preview precisam passar a resolver capa limpa, sem alterar o contrato da rota protegida do acervo.
4. Validar `width > height` após `ImageOps.exif_transpose` e decodificação do JPEG no backend, antes da escrita de fonte/seleção/enqueue; somente para pasta técnica de capa. Revalidar no caminho legado de seleção de capa quando admitir mudança do cover_photo_id. Não basta validar extensão ou valores do frontend. O registro técnico da tentativa pode existir, mas a capa atual permanece até upload válido; não introduzir exclusão silenciosa de registros.
5. Novos uploads exigem horizontal; capas antigas verticais/quadradas permanecem visíveis até substituição e também ficam limpas. A migração de apresentação é somente resolução de URL/derivado, sem migration de banco, backfill, exclusão ou marca-d'água removida destrutivamente.
6. Componente de capa com largura fluida e proporção intrínseca/contain, altura adaptativa, título sobreposto responsivo. Horizontal não garante enquadramento universal; manter a foto inteira é a decisão explícita. Preservar configurações do título e aplicar limites responsivos de tamanho/wrapping, sem esticar ou cortar fotos. Miniaturas de fotos/pastas continuam protegidas; somente representações efetivas da capa vigente recebem a exceção.

## Risks / Trade-offs

- Capa sem marca pode ser copiada por cliente autorizado → intenção explícita do proprietário; não afirmar que o título impede cópia. Registrar a exceção no mandato/roadmap/documentação ao implementar; não remover proteção das outras fotos.
- A foto horizontal fica mais baixa no celular → ajustar título e espaçamento, validar larguras 360/390/768/1440 e fotografias panorâmicas; não impor 16:9 como regra de upload.
- Cores legadas podem gerar trechos claros/ilegíveis → inventário de cores e teste visual de entrada, dashboard, editor, biblioteca, galeria, carrinho, PIX e diálogos em ambos os temas.
- Fonte EXIF enganosa ou arquivo corrompido → validar dimensões visuais e decodificação reais no servidor, mantendo limite de bytes existente.

## Migration Plan

Sem migration própria. Após implementação/testes/revisão, publicar somente com autorização operacional e inventário atualizado. A base ainda contém a migration 0055 e exige atualização coordenada do worker opcional descrita na change anterior; não confundir ausência de nova migration com ausência dessa dependência pendente. Nenhum deploy será executado no planejamento. Rollback de apresentação restaura o resolvedor protegido sem apagar fontes/derivados ou a preferência local. Revisão humana precede sincronização e arquivamento.
