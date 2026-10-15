# Configuração por fotógrafo

PIX, marca, tabelas progressivas, templates, preferências de avisos e processamento pertencem à conta revalidada da sessão administrativa. O mesmo código de tabela pode existir em A e B. Alterar a tabela ou proteção de A não altera B; pedidos anteriores conservam seus snapshots. Conta nova recebe os textos técnicos do produto e estados não configurados, sem copiar valores comerciais da conta existente.

Na entrada de cliente, a marca é resolvida pelo convite opaco válido; sem convite, somente uma sessão válida pode fornecer contexto. Convite explicitamente inválido não usa a marca da sessão como alternativa. Entrada anônima apresenta a identidade técnica do produto. Assets contextuais incluem o convite quando necessário e são privados, sem cache. Novos uploads usam `tenants/<UUID>/branding/`; keys legadas permanecem iguais, e caminhos de outra conta ou fora da raiz são recusados.

Alterar PIX exige senha atual e OTP vinculado ao administrador, sessão e conta. Confirmação estrangeira e vínculo revogado falham antes de consumir o código; o serviço de reenvio aplica a mesma restrição. Os testes usam outbox e destinatário sintéticos, sem envio ou transação financeira. O vínculo seguro de canais e revalidação de workers continuam obrigatórios nas tasks 5.1–5.2; esta etapa não libera segunda conta operacional.

Evidência: `backend/tests/test_tenant_configuration.py`, testes de entrada/configurações frontend e `validation.md`. Migration de preservação das configurações legadas está registrada na task 2.3.
