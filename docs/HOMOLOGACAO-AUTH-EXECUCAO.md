# Procedimento de homologação de autenticação — aposentado

> **Não executar nem usar como roteiro.** A decisão do proprietário em 18/11/2026 encerrou o ambiente de homologação. O bootstrap, as credenciais e o fluxo descritos neste documento foram supersedidos; não crie um Environment/secrets `homolog`, arquivo de configuração de homologação ou destino intermediário equivalente.

As instruções anteriores também associavam o domínio real `markina.pickyourpic.com.br` ao alias de proxy `markina-homolog-nginx`, o que não deve ser usado para configurar nem alterar o tráfego de produção. O arquivo `docker/.env.homolog` continua sendo apenas um nome legado da configuração de produção em operações documentadas; seu nome não representa um ambiente separado.

Para desenvolvimento, siga o setup local e use dados sintéticos. Para publicação ou recuperação da produção, consulte `DEPLOY.md`, o runbook da operação específica e a change OpenSpec aprovada. Este registro não autoriza mudanças no servidor, proxy, DNS, banco, secrets ou serviços.
