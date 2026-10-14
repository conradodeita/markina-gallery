# Decisão do spike de descoberta facial

## Decisão

**AJUSTAR antes de integrar.** YuNet + SFace está tecnicamente aprovado como baseline único para uma próxima validação controlada, mas a funcionalidade de produto permanece reprovada para ativação até todos os gates residuais serem cumpridos.

| Candidato | Decisão | Justificativa |
|---|---|---|
| OpenCV YuNet + SFace | **Aprovar como baseline; ajustar antes do produto** | Código/pesos permissivos, execução e desempenho ARM64 comprovados no Oracle, isolamento aprovado e ponto sintético conservador com zero FP; faltam RIPD e calibração representativa permitida |
| AdaFace R18 | **Rejeitar por ora** | Cadeia comercial do peso/dataset não ficou inequívoca; não baixar ou integrar até haver comprovação escrita |
| InsightFace/Buffalo | **Rejeitar** | Pesos públicos restringem uso a pesquisa não comercial |
| DeepFace | **Rejeitar como solução** | Wrapper não resolve licença dos modelos nem reduz o caminho operacional |
| CompreFace | **Rejeitar para o alvo atual** | Distribuição padrão x86/AVX e arquitetura de múltiplos serviços inadequadas ao Oracle ARM atual |

## O que o spike comprovou

- O pipeline local consegue detectar múltiplos rostos por foto, versionar o modelo e consultar somente o evento solicitado.
- A consulta é um filtro temporário e não cria galeria, vínculo, seleção, pedido ou autorização.
- O limiar oficial de exemplo `0,363` é inadequado para este corpus; a calibração é obrigatória.
- `0,750` favoreceu falsos negativos: precisão 100%, recall 98,62%, top-1 100%, zero FP e 15 FN agregados.
- Baixa resolução é o cenário mais frágil e deve orientar mensagens de qualidade e testes futuros.
- O caminho OpenCV funciona no Oracle ARM64 físico: 14,36 fotos/s em container limitado a 2 CPUs/1 GiB e consulta mediana inferior a 1 ms.
- O custo mínimo dos vetores é pequeno frente às imagens, mas operação real exige medição de fila, criptografia, índice e concorrência.

## Arquitetura aprovada para uma change futura

1. Indexação facial assíncrona e versionada após a prévia fotográfica ficar pronta; falha facial nunca bloqueia a foto.
2. Habilitação explícita por Galeria pública somente após base legal, transparência e controles infantis válidos.
3. Referência temporária com exatamente um rosto, consentimento destacado e exclusão automática em sucesso, falha, cancelamento ou timeout.
4. Busca limitada à Galeria pública que a cliente já está autorizada a visualizar.
5. Candidatas destacadas no topo da mesma galeria, com linguagem de possibilidade e seleção manual consciente.
6. Criação/reuso da única privada de `Galeria pública + cliente` somente na primeira seleção, pelo resolvedor comercial existente.
7. Fotos de pesquisas distintas compõem o mesmo filtro/carrinho; duplicatas são eliminadas.
8. Revisão prévia do fotógrafo dispensável somente se o resultado não ampliar acesso; obrigatória em qualquer outro desenho.

## Gates ainda obrigatórios

- reconciliar formalmente o roadmap, que ainda contém o fluxo anterior de revisão antes da exposição;
- elaborar e revisar RIPD, hipótese legal da indexação, transparência, consentimento e tratamento de menores/ECA Digital;
- definir mecanismo não biométrico de representação legal para referência de criança;
- calibrar com corpus representativo permitido e avaliação de equidade, sem dados reais em homologação;
- testar exclusão ponta a ponta, concorrência, retentativa, timeout, criptografia, rate limit e revogação;
- criar outra change OpenSpec para worker, storage, banco, API e frontend, com migrations somente aditivas;
- obter revisão humana da change e autorização operacional antes de qualquer deploy.

## Rollout recomendado

1. protótipo local atrás de feature flag desligada por padrão;
2. testes automatizados de isolamento e ciclo de vida;
3. piloto interno apenas com adultos sintéticos/consentidos;
4. revisão técnica, jurídica, de segurança e humana;
5. somente então considerar opt-in restrito, monitorado e reversível.

Até o fim desses gates, a seleção manual existente continua sendo a única jornada de cliente autorizada.
