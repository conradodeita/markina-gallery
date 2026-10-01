# Cadastro independente por fotógrafo

Cada fotógrafo mantém seu cadastro próprio de cliente, nome e telefone. A mesma pessoa pode usar o mesmo número com dois fotógrafos sem compartilhar UUID, histórico ou alterações cadastrais. Números canônicos e reservas ativas são únicos dentro da conta, inclusive antes da verificação; histórico de telefone aposentado conserva o proprietário.

O servidor deriva a conta do vínculo administrativo autenticado. UUID no caminho, campo extra no corpo e cursor de paginação não autorizam outra conta. Busca e agregados do diretório usam somente a conta autorizada; UUID alheio recebe a mesma resposta de recurso ausente. Cursor de outra conta ou formato antigo é recusado.

Troca de telefone exige prova OTP da mesma conta antes de consumir o desafio. Conflito local não aposenta o número atual; sucesso revoga as sessões do cliente correspondente e minimiza somente desafios/entregas daquele contexto. Cadastro, prova e sessão independente do mesmo telefone em outro fotógrafo permanecem preservados.

O painel solicita a prova em `/admin/clients/{id}/phone/challenge`, autenticado pelo vínculo administrativo e conferindo cliente/conta antes de emitir. Não exige galeria nem utiliza entrada genérica de cliente. A confirmação continua em `/admin/clients/{id}/phone`, com desafio e número próprio. O controle compartilhado do diretório/editor usa esse contrato.

Clientes entram pelo link enviado pelo fotógrafo; cada link conserva seu contexto na criação, reenvio e verificação OTP. Sem link, a entrada orienta solicitá-lo; sessão cliente já válida pode seguir para sua biblioteca. Link de B com cookie de A exige autenticação contextual de B. O piloto futuro usa perfis/contextos de navegador separados; não há promessa de sessões simultâneas A/B no mesmo perfil. Token fica somente no fluxo em memória/URL, sem localStorage/cache de dados privados.

Evidência local: `backend/tests/test_tenant_identity_directory.py`, 11 casos PostgreSQL. O teste de rotas substitui apenas a entrada de sessão administrativa já autenticada, mantendo consultas e vínculos reais; não equivale à validação completa de login/middleware. Tasks 3.2–3.3 completam OTP e sessão. A branch parcial não habilita uma segunda conta operacional nem dispensa prontidão e autorização remota.
