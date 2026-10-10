# Tasks

## 1. Localização do diagnóstico

- [x] 1.1 Retirar o card da Visão Geral, manter no Monitor, atualizar documentação e validar regressões da localização/gate com Vitest sem servidor.

- [x] 1.2 Identificar fotógrafos somente por e-mail existente na árvore privilegiada; validar vínculo único/ausente/ambíguo, pesquisa, isolamento e exclusão da exportação com testes ORM e Vitest, documentando o contrato.

## 2. Integração

- [x] 2.1 Validar lint/build e OpenSpec, revisar diff e registrar comandos/resultados antes do PR, sem iniciar aplicação local.
- [ ] 2.2 Após CI/deploy verde, confirmar no servidor a ausência na Visão Geral, presença autorizada no Monitor e identificação por e-mail na árvore; registrar SHA e evidência verificável.

## Workflow follow-up

- Pausar após push enquanto o CI roda, conforme instrução humana vigente.
- Sincronizar e arquivar somente após revisão humana específica desta change e validação remota concluída.
