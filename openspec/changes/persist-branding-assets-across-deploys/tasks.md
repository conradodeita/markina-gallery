## 1. Armazenamento persistente

- [x] 1.1 Configurar volume exclusivo e raiz de branding na API, mantendo caminhos locais de desenvolvimento e contratos de upload; validar Compose sem exibir segredos e teste de contrato que confirme mount/variável coerentes e ausência de novas portas.
- [x] 1.2 Cobrir upload autenticado, validação de arquivos, leitura dos três ativos, tamanhos de ícone e ausência segura em raiz persistente; executar testes backend focados com banco e diretório temporários, incluindo hashes e preferências preservados.

## 2. Transição e operação

- [x] 2.1 Implementar preservação pré-recriação e transferência idempotente de ativos legados, integradas ao deploy; testar arquivo ausente, válido, caminho inválido/symlink, destino igual/divergente, falha de cópia e bloqueio de recriação antes de preservação bem-sucedida, sem sobrescrita nem exclusão de fontes.
- [x] 2.2 Incluir backup restrito dos bytes de branding e documentar restauração, rollback mantendo volume, controle da janela sem uploads e reenvio de arquivos já ausentes; verificar integridade e restauração em diretório/volume isolado com dados sintéticos, sem restaurar banco.

## 3. Validação e entrega

- [x] 3.1 Executar teste isolado de recriação real de container usando o mesmo volume com três ativos sintéticos, verificando hashes e leitura após recriação; registrar evidência ou bloqueio explícito se Docker indisponível, sem marcar concluído apenas com teste de contrato.
- [x] 3.2 Executar testes direcionados de deploy/branding, lint aplicável, OpenSpec estrito e revisão do diff; registrar resultados e instruções de continuidade sem suíte completa local, sem imagens de teste no Git e sem sync/archive antes de revisão humana.

## 4. Homologação

- [ ] 4.1 Após implementação e aprovação operacional do inventário atualizado, publicar via PR/CI e deploy autorizado; verificar mount, versão, saúde e recursos de terceiros preservados. Registrar paridade ou bloqueio real, sem alterar configurações ou reiniciar workers opcionais sem necessidade.
- [ ] 4.2 Após persistência comprovada, orientar o proprietário a reenviar logo, favicon e ícone individuais ainda ausentes; verificar rotas/imagens e ícones do manifesto com a arte recebida, preservando proporção. Esta task depende do reenvio humano e não pode ser concluída com arte substituta.
