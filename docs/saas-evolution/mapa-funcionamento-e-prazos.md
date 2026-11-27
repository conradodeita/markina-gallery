# Mapa de funcionamento e prazos — Pick-your-Pic

Referência central para preparar o futuro manual. Atualização: 11/11/2026. **Implementado localmente não significa publicado.** As specs consolidadas e deltas ativos continuam sendo a fonte técnica; links abaixo identificam o comportamento e as pendências. Não usar versões históricas de decisões como regra atual.

## Vocabulário único

| Expressão | Significado |
| --- | --- |
| Suspender | Bloquear a disponibilidade da conta preservando dados e conciliação iniciada; não encerra nem exclui. |
| Encerrar | Finalizar a prestação operacional após proteger prazos e obrigações; não apaga automaticamente todos os dados. |
| Expirar pasta | Terminar seu prazo de acesso; não significa que os arquivos já foram transferidos. |
| Arquivar / congelar | Transferir mídia para armazenamento frio com verificação; preservar referências de seleção, sem acesso às fotos arquivadas. |
| Recuperar / descongelar | Restaurar e verificar mídia; não autentica nem reabre uma conta encerrada. |
| Reabrir conta | Ação administrativa separada para permitir novo login, depois dos gates aplicáveis. |
| Eliminar dados pessoais | Tratar solicitação por categoria/finalidade, separada do encerramento do serviço. Não significa apagar compras de clientes automaticamente. |
| Excluir definitivamente mídia | Ação explícita e auditada de remoção verificada; não é arquivo frio e não é recuperável. |

## Prazos por evento

| Evento inicial | Prazo/regra | Estado e fonte |
| --- | --- | --- |
| Cadastro de fotógrafo não verificado | 30 dias para limpeza de nome/e-mail do cadastro não verificado; não abrange conta ativa | Local; [cadastro](../../openspec/changes/add-photographer-signup-portal/retention-privacy-matrix.md). |
| Liberação de pasta nova | Número finito de dias escolhido pelo fotógrafo, sem herdar da galeria | Local; [arquivo](../../openspec/changes/add-gallery-media-archive/proposal.md). Pastas antigas iniciam indeterminadas; prazo começa quando configurado. |
| Expiração de pasta | 30 dias completos antes de elegibilidade ao arquivo, sujeitos a obrigações e reaberturas | Local; mesma change. Carrinho não bloqueia indefinidamente; pedido aberto bloqueia. |
| Reabertura normal | Solicitação dentro da janela de 30 dias; fotógrafo define dias desde aprovação | Local; pública vale aos autorizados; privada somente solicitante. Arquivo espera 30 dias após o último prazo aplicável. |
| Recuperação fria concluída | 30 dias de acesso para novos pedidos, contados da liberação. Depois, nova expiração e janela de arquivo. | Local. Taxa global por pasta e ciclo, reserva antes e débito só após a liberação íntegra. Conta do proprietário isenta. |
| Solicitação de encerramento | Sem duração fixa: aguarda prazos, pedidos, obrigações e arquivamento verificado | Local; [encerramento](../../openspec/changes/add-photographer-account-closure/proposal.md). Saldo remanescente confirmado não bloqueia. Pastas comprovadamente nunca liberadas podem arquivar diretamente. |
| Conta efetivamente encerrada | Dez anos até revisão manual; contador no console | Local; não é exclusão automática, prazo máximo de recuperação ou obrigação legal genérica. |
| Revisão após dez anos | Proprietário pode reduzir CPF/endereço cifrados nas condições aprovadas ou excluir mídia fria por fluxo auditado | Local; [exclusão auditada](../../openspec/changes/add-audited-tenant-media-deletion/proposal.md). São ações diferentes. Nome/e-mail mínimos restritos; verificador CPF permanece enquanto houver mídia recuperável. |
| Aceite dos Termos | Durante conta ativa e até dez anos após encerramento, ressalvadas exceções documentadas | Decisão registrada; não copiar esse prazo para todos os dados financeiros ou de clientes. |
| Contatos de clientes sem vínculos/obrigações | Nenhum prazo geral aprovado | Os 90 dias foram sugestão, não decisão nem código. Vínculo recuperável e direitos de terceiros precisam de tratamento próprio. |

## Quem faz o quê

- Fotógrafo: pede encerramento do próprio tenant, confirma consequências e saldo; não reabre sozinho conta encerrada.
- Proprietário: suspende/ativa disponibilidade, acompanha encerramento, solicita recuperação e decide reabertura separadamente; exclusão fria após revisão exige fluxo sensível próprio. Não existe aprovação para inventar um encerramento compulsório de outro tenant.
- Cliente: mantém direitos e histórico próprio; encerramento do fotógrafo não apaga automaticamente suas compras. Não prometer acesso perpétuo a galerias expiradas/arquivadas.

## Recuperação de acesso — validada localmente

[secure-photographer-account-recovery](../../openspec/changes/secure-photographer-account-recovery/proposal.md) foi implementada e validada localmente; não está publicada. Usar primeiro e-mail e fatores anteriores verificados. Telefone só é meio de recuperação se houver vínculo comprovado e mecanismo existente; telefone cadastrado e WhatsApp conectado não bastam. Nome/CPF identificam e não autenticam.

Decisão substitutiva: se esses meios estiverem indisponíveis, o fotógrafo contata o proprietário externamente. O proprietário julga a identidade fora do SaaS e confirma no console a recuperação, com motivo, reautenticação e auditoria. Novo e-mail é verificado e o fotógrafo define a própria senha. O SaaS não coleta documentos/selfies e não exige fator antigo nessa exceção. Recuperar credenciais não reabre conta encerrada, não retira suspensão e não restaura mídia excluída.

### Na prática: qual ação usar

| Situação | Caminho | Efeito |
| --- | --- | --- |
| Conta ativa, esqueceu a senha e mantém e-mail | Link de recuperação; com TOTP ativo, também código do autenticador ou de recuperação | Nova senha, sessões antigas encerradas; sem sua aprovação. |
| Mantém senha/TOTP e perdeu a caixa de e-mail | Entrar e usar troca autenticada de e-mail; confirmar novo endereço | Troca comum, sem atendimento excepcional. |
| Perdeu só o autenticador e não tem código de recuperação | Atendimento de revogação de autenticador pelo proprietário, com motivo e reautenticação | Volta à senha; pode configurar outro autenticador; estado da conta preservado. |
| Não consegue usar os meios disponíveis | Proprietário confere identidade externamente, abre atendimento; fotógrafo confirma novo e-mail e escolhe senha; proprietário conclui com senha/TOTP próprios | Só na conclusão final entram juntos o e-mail e a senha novos. Link vale quinze minutos; sem login automático. |
| Conta suspensa | Retirar suspensão no console, como ação própria | Recuperar credenciais não a libera. |
| Conta encerrada | Restaurar/verificar mídia necessária e autorizar reabertura no console | Recuperar credenciais não reabre; suspensão, se houver, permanece. Mídia definitivamente excluída não volta. |

O proprietário não recebe a senha escolhida pelo fotógrafo. CPF e nome não são senha nem prova única. Não há upload de documentos neste atendimento. Depois de dez anos, CPF mais um novo e-mail não autorizam sozinhos a reabertura. A recuperação da própria identidade do proprietário continua em fluxo próprio.

## Eliminação e conservação de dados

Separar dados pessoais do fotógrafo, registros comerciais necessários e dados próprios dos clientes. O encerramento não resolve, por si só, todos os pedidos de eliminação. Não prometer conservação irrestrita para possível reabertura nem exclusão de registros obrigatórios. A futura política detalhada precisa identificar finalidade, base aplicável, exceções e responsáveis; não está concluída por este mapa. A discussão não substitui automaticamente as regras locais aprovadas.

## Regras para o futuro manual

Organizar jornadas por proprietário, fotógrafo e cliente, com ação, efeito, prazo, bloqueio e forma de resolução. Incluir exemplos de expiração/arquivo e encerramento/reabertura. Diferenciar disponível de proposto e registrar revisão/data do manual. Não expor fornecedor de arquivo, caminhos, chaves ou detalhes internos como instruções ao usuário.

## Limites de publicação

Nenhuma ação desta documentação altera produção. Ensaio Workspace real, custódia, transporte real de mensagens/e-mail, infraestrutura e release conservam autorizações próprias. Ver [checkpoint do candidato](candidate-validation-2026-11-03.md).
