# Design

## Context

Ver `proposal.md` e os deltas de `client-access/cloned-private-galleries` e `media-storage/protected-previews`. Em homologação, o Proxy Manager termina TLS e alcança o nginx da Markina por HTTP. Esse nginx sobrescreve `X-Forwarded-Proto` com `$scheme`; `_gallery_capability_link` em `backend/app/main.py` usa esse cabeçalho e gera `http://`. A API já recebe `PUBLIC_APP_ORIGIN=https://markina-homolog.duckdns.org`, validado hoje para links de notificações faciais. O backend do carrinho fornece `/public-galleries/<galeria>/photos/<foto>/preview`, mas `purchasePreviewUrl` no frontend rejeita essa família de rotas antes da requisição.

## Goals / Non-Goals

**Goals:**

- Usar uma única validação da origem pública para links sensíveis gerados pelo servidor e fazer a emissão falhar antes de persistir uma capacidade nova se a origem implantada for inválida.
- Carregar a mídia canônica no carrinho pelo endpoint protegido existente, conservando a lista restrita de caminhos permitidos e o tratamento de falha.
- Preservar compatibilidade de teste/desenvolvimento HTTP e os caminhos de galeria legada/histórico de compras.

**Non-Goals:**

- Mudar o Proxy Manager compartilhado, certificado, DNS, arquivo `.env`, política de OTP, token/capacidade, precificação, pagamento ou autorização de mídia.
- Fazer pagamento real, confirmar pedido ou habilitar segundo fotógrafo.

## Decisions

### Origem pública no backend

Extrair a validação já usada por `notification_public_origin` para um módulo comum pequeno. `PUBLIC_APP_ORIGIN` tem precedência; a compatibilidade existente com `MARKINA_PUBLIC_URL` pode permanecer quando for uma origem válida. Em ambiente implantado, exigir origem absoluta HTTPS, host público e ausência de usuário, senha, caminho significativo, query, fragmento ou caracteres inválidos. A rotina de convite usa somente a origem validada para compor `/?access_token=...`; não consulta `Host`, `X-Forwarded-Host` nem `X-Forwarded-Proto` em ambiente implantado. Uma mudança futura de domínio atualiza a configuração existente, sem código hardcoded. Em teste/desenvolvimento, preservar a origem local HTTP para fixtures e execução local.

Antes de criar/rotacionar capacidade em rotas de escrita, validar a origem. Assim, um erro de configuração não deixa uma capacidade nova persistida sem link utilizável. Respostas de leitura sem token continuam possíveis; onde a resposta inclui token, a falha deve ser neutra e não imprimir a capacidade. Manter a exceção de configuração compatível no subsistema de notificação ao reutilizar o validador.

Alternativas rejeitadas: repassar `X-Forwarded-Proto` pelo nginx próprio ainda deixaria a geração dependente de cabeçalhos de requisição; fixar o domínio de homologação no código exigiria release a cada troca de domínio; aceitar o esquema de `request.url` reproduziria o defeito por causa do trecho HTTP interno.

### Prévia canônica no frontend

Ampliar apenas a expressão de rotas locais aceitas em `purchasePreviewUrl` para `/public-galleries/<id>/photos/<id>/preview`. A função conserva um único prefixo `/api`, rejeita esquema externo, query, fragmento, travessia, original e área administrativa; o componente existente continua exibindo “Prévia indisponível” se a mídia retornar erro. O endpoint FastAPI atual revalida sessão, vínculo, galeria e pasta; não haverá nova rota pública nem relaxamento no servidor.

Alternativa rejeitada: usar URL de original ou inserir fallback direto ao storage para contornar a falha, pois isso violaria as regras de prévias protegidas. Não duplicar componente apenas para a galeria canônica.

## Risks / Trade-offs

- [Origem pública ausente/inválida em outro ambiente implantado] → falhar fechado, documentar a verificação de `PUBLIC_APP_ORIGIN` sem expor secrets e validar localmente antes do deploy.
- [Regressão em notificações faciais ao compartilhar o validador] → conservar assinatura/erro públicos e executar testes focados dos links de notificação.
- [A rota admitida pelo frontend não autoriza a cliente] → manter teste de negação direta no backend e rejeição de rotas arbitrárias no frontend; URL nunca substitui autorização.
- [Deploy da correção volta a gerar backup com dados novos] → inventariar antes da janela e pedir autorização operacional específica; a homologação foi deixada sem dados operacionais sintéticos.

## Migration Plan

Não há migration nem alteração de configuração persistida. Implementar e validar em branch/PR separado; parar após push enquanto o proprietário confere a CI. Antes de integrar em `develop` (gatilho de deploy automático), apresentar SHA, inventário de serviços/porta/subdomínio, backup e plano de impacto zero, e obter autorização específica. Após publicação, criar somente dados sintéticos autorizados, verificar o esquema HTTPS do convite sem registrar o token, prévia protegida no carrinho e negação de outra cliente; excluir os dados de teste pelo procedimento homologado e confirmar admin/Evolution/serviços vizinhos. Em caso de regressão, usar correção de código compatível sem migration; reverter ao binário anterior reabriria o defeito do convite e não é aceito como solução de segurança.
