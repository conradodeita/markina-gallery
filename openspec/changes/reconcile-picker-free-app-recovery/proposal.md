# Proposal

## Why

A retirada do Picker foi integrada ao código e a chave exclusiva já foi revogada, mas o cleanup permanece bloqueado porque o handoff preserva containers antigos com o bind do Picker e o caminho de recovery pode reiniciar diretamente esses containers. O proprietário aprovou manter recuperação da aplicação sem restaurar o recurso Picker; o fluxo precisa preservar a recuperação de API/web sem depender da chave aposentada.

## What Changes

- Acrescentar ao handoff protegido uma receita de recuperação de API/web vinculada às imagens e aos modelos do par API/web atual e saudável, SHA, configuração e fingerprint aprovados, removendo somente o bind exato de `picker-config.json` e mantendo OAuth e demais mounts inalterados.
- Recuperar API/web pela receita verificada, sem iniciar o container histórico que mantém o bind do Picker; continuar exigindo inventário somente-leitura, aprovação protegida própria, lock, healthchecks e validação dos endpoints.
- Reconhecer um container antigo como testemunha imutável somente quando sua identidade/configuração estiver registrada, seu estado for parado e a receita atual de recovery não depender dele. Seus metadados continuam na fingerprint; qualquer divergência, container ativo ou mount desconhecido bloqueia.
- Permitir a retirada posterior do arquivo exato do Picker apenas após runtime API/web saudável e inventário atual que prove ausência de mount ativo/candidato de recovery. OAuth, banco, dados de clientes, volumes e outros projetos permanecem preservados.
- Validar em ambiente local/CI sintético que a receita do par ativo inicia API/web sem o segredo do Picker e preserva OAuth e demais recursos. Não inclui execução no servidor.

## Capabilities

### New Capabilities

- `deployment-operations/picker-free-app-recovery`: recuperação protegida de API/web sem restaurar o mount ou a credencial aposentados do Google Picker.

### Modified Capabilities

Nenhuma. A regra geral de rollback continua limitada a API/web e com inventário/aprovação próprios; esta capability acrescenta a receita específica necessária à aposentadoria do Picker.

## Impact

Afeta a ponte Compose root-only, o preflight de aposentadoria, o workflow protegido de liberação/recuperação e seus testes de contrato. Não muda API pública, schema do banco, OAuth, armazenamento frio ou dados de clientes. A mudança prepara código e artefatos revisáveis; qualquer execução em produção exigirá gates, inventário, fingerprint e aprovação operacional próprios.

A obtenção das imagens para o ensaio reutiliza o exportador da imagem ativa, incluindo web além de API. O workflow protegido de diagnóstico oferece exportação somente leitura para artifacts privados de curta retenção, vinculados ao SHA e aos IDs recém-observados.
