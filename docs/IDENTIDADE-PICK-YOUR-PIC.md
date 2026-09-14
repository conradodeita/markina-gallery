# Identidade Pick-your-Pic

O nome de apresentação é **Pick-your-Pic**, mantendo a paleta preto/amarelo com cinza e bege de apoio. A mudança não altera o domínio atual, links de galerias, conta do administrador, sessões, pagamentos ou permissões.

Em **Configurações**, continue usando os uploads de logotipo, ícone do aplicativo e favicon. Envie cada arte individualmente: a prancha de referência com várias aplicações não é usada automaticamente. A logo já contém nome e tipografia; os cabeçalhos a mostram sem repetir o nome ao lado, com proporção preservada e fundo neutro claro para legibilidade nos dois temas. Sem arquivo ou em falha, aparece Pick-your-Pic em texto. Nenhuma arte é recriada ou invertida.

Novos textos padrão, e-mails de segurança, OTP e defaults de marca-d’água passam a usar Pick-your-Pic. Configurações e mensagens personalizadas já salvas permanecem intactas. Caso ainda contenham a marca anterior, edite-as no painel: não fazemos substituição silenciosa no banco nem reprocessamos fotos antigas.

O manifesto do PWA usa Pick-your-Pic como nome e nome curto. Aplicativos já instalados dependem do ciclo de atualização do navegador/sistema operacional para mostrar o novo nome e ícone; não é garantida atualização imediata da tela inicial. Não é necessário apagar dados da conta ou sessões.

## Identificadores preservados

`markina-gallery` continua sendo o identificador de infraestrutura; são mantidos o projeto Docker Compose, nomes de volumes/redes, pacote npm, cabeçalhos `X-Markina-*`, cookie `markina_session`, filas, chaves de ambiente e caminho `/markina-sw.js`. Esses identificadores não são a marca apresentada ao usuário. Caminhos de documentação, migrations e evidências históricas também são preservados para auditabilidade.

## Publicação

Rebrand e modo escuro foram implementados localmente. Homologação só exibirá a nova identidade após publicação autorizada com inventário operacional e conferência do SHA. A mudança não autoriza alterações de DNS, segredos ou serviços de terceiros.
