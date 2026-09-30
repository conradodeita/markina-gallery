# Roteiro do piloto pequeno

## Estado e pré-condições

Planejado; não executado. Requer isolamento completo, matriz sem lacunas e suíte local aprovada. Homologação exige inventário e autorização de versão, contas, dados, permissão do dono e canais. Configuração externa ausente bloqueia o aceite remoto correspondente; não usar canal de outro fotógrafo nem bypass de OTP.

## Grupo e corpus propostos

| Item | Conta A | Conta B |
| --- | --- | --- |
| Fotógrafo | 1 administrador próprio | 1 administrador próprio |
| Clientes | A1, A2, A3 | B1, B2, B3 |
| Caso de contato repetido | A1 | B1 com mesmo telefone de A1 |
| Galeria | 1 | 1 |
| Pastas | 1 comum e 1 restrita | 1 comum e 1 restrita |
| JPEGs | Até 6, sintéticos e sem rostos | Até 6, sintéticos e sem rostos |
| PIX | Configuração sintética A | Configuração sintética B |

Os rótulos são referências de ensaio, sem nomes, telefones ou credenciais reais versionados. Separar contextos de navegador e autenticar cada cadastro por seu link. O operador da instalação possui permissão técnica própria, separada da autorização comercial.

## Sequência

1. Inventariar preservados e registrar baseline do dono pelo painel: consultar e copiar `capacity-report/v1`, UTC/cache e lacunas.
2. Ambos os fotógrafos entram com senha/TOTP, criam e preparam sua galeria/pastas e enviam o lote delimitado. Fazer leitura durante processamento; caso jobs sejam rápidos demais, registrar que o pico não foi capturado e usar evidência de conclusão separada.
3. As seis clientes entram pelos respectivos links e OTP. Até seis jornadas podem estar ativas. Verificar pasta comum e restrita, ampliação, favoritos e seleção. Coletar diagnóstico respeitando cache de até 30 segundos.
4. A1/B1 selecionam conjuntos distintos. Exercitar checkout com instruções PIX diferentes e confirmação sintética local; em homologação não alegar pagamento financeiro real. Exercitar também finalização sem cobrança de outra cliente, preservando o contrato vigente.
5. Verificar Compras e entrega, depois tentativas diretas de acesso cruzado a cliente, galeria, prévia, pedido, configuração e monitor por fotógrafo comum. Qualquer vazamento interrompe o ensaio.
6. Confirmar independência de alteração de nome/telefone, suspensão e exclusão operacional elegível com fixtures locais separadas; efeitos destrutivos remotos só se explicitamente inventariados/autorizados.
7. Após o término, obter novo diagnóstico e comparar pool, PostgreSQL e cinco filas, confirmando finalização dos jobs por evidência própria. Registrar cache, campos indisponíveis e fontes; não inferir throughput, worker saudável, SLO ou número seguro de usuários.

## Evidência a preencher na execução

Criar `pilot-results.md` somente com resultados reais: versão/schema, ambiente, autorizações, UTC de cada etapa, tamanho efetivo do corpus, concorrência efetiva, referências de testes, comparação sanitizada dos relatórios e lacunas. Declarar explicitamente se envio real, busca facial ou pico de fila não foram exercitados. Não persistir OTP, cookies, telefones, fotos, nomes ou payloads de mensagens. Eventual remoção do corpus precisa de plano e autorização específicos; não executar limpeza integral como encerramento automático.
