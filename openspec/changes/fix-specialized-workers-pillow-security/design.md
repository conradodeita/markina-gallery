## Context

Decisão direta de 25/10/2026: corrigir os processos de fotos primeiro. Worktree separado do Mercado Pago, que permanece no PR #283/SHA53959492 com CI verde, sem publicação. Novo worktree acompanha o PR #258 do Dependabot (pin preexistente de Pillow13); main cef5bdf8 foi integrada localmente para não reintroduzir código de pagamentos aposentado. Nenhum reset/force push.

Produção: `/opt/markina-gallery`, host clearbudget-vnic, schema0087, API/worker geral Python3.13.17/Pillow13.0.0; seis especializados Python3.13.16/Pillow12.3.0: index/search/maintenance SFace, index Gemma, preview adjustment e raw development. Preserve as imagens/fontes existentes, inclusive diferenças entre elas. Não adotar os bloqueios/exceções da preparação Python anterior como autorização automática; esta missão registra a autorização adicional e precisa de seus próprios gates.

## Decisions

### Atualização mínima e origem

Usar Pillow13.0.0, correção indicada pelos alertas e já carregada na API. Revisar notas oficiais, licença MIT-CMU e requisitos de Python antes do build. Download de um wheel compatível pelo índice oficial, com SHA256 conferido pelo JSON PyPI13.0.0. `pip install --no-index --no-deps` sobre a imagem anterior imutável. Nenhum apt/pull de base, resolução ampla de dependências ou download de modelos. Todos os demais pacotes, Python e árvore de aplicação/model manifests devem permanecer idênticos. A cópia de NumPy/OpenCV e os binários externos fotográficos permanecem os mesmos.

### Compatibilidade e privacidade

Ensaiar JPEG RGB/L/CMYK, orientação EXIF, conversão, resize, normalização de referência e derivados/proteção com padrões gerados sem pessoas. Comparar pixels/formatos/dimensões entre antes/depois e executar os contratos locais pertinentes aos consumidores. Diferença inesperada é bloqueio, não motivo para afrouxar assertivas. Verificar os caminhos efetivamente instalados, sem inferir runtime por tag. Pesos/modelos existentes não são baixados nem trocados; qualquer eventual inferência necessita apenas de entrada sintética e permanece offline. Sem ingestão biométrica real, reindexação, canais ou mensagens.

Ensaio inicial bloqueou corretamente resize automático de retratos: a fonte oficial `src/libImaging/Resample.c`13.0.0 passou a executar o passe vertical primeiro quando a redução vertical excede duas vezes a horizontal;12.3.0 fazia horizontal primeiro. Ambos são filtros separáveis com arredondamento/clipping intermediário, portanto seus pixels podem diferir. Não introduzir tolerância geral nem alterar código do produto para imitar a biblioteca antiga. Comparar bit a bit os dois oráculos explícitos (horizontal→vertical e vertical→horizontal) entre versões e exigir que cada resize automático corresponda exatamente à regra da respectiva versão. Demais contratos continuam exigindo igualdade exata. A diferença conhecida fica registrada, sem alegar igualdade absoluta de todas as imagens futuras. Fonte: https://raw.githubusercontent.com/python-pillow/Pillow/13.0.0/src/libImaging/Resample.c .

### Publicação pontual

Preparação e ensaio não substituem containers ativos. Inventário inclui seis IDs/imagens, comandos, restart policy, mounts/configuração, fonte/model manifests, pacotes, filas/outboxes e serviços que devem permanecer. Mesmo domínio/porta loopback8080. O proprietário já aceitou uma janela temporária; antes de executá-la apresentar o inventário/impacto concreto e cumprir gates de autorização, CI, recuperação e origem. Não alterar proxy/DNS/firewall/certificados nem recursos de outros projetos.

Durante a janela aprovada, barreira exclusiva de ingresso, drenagem da API/worker geral e prova de quiescência, seguida de parada dos seis legados identificados por SIGINT sem SIGKILL. Suspender temporariamente `unless-stopped` para que não reiniciem antes da troca. Nenhum Alembic/DDL. Substituir somente os seis serviços, com mesmas configurações/modelos/mounts, por IDs candidatos. Restaurar restart policies e retomada de API/worker geral originais. Conferir saúde, versões, preservação financeira/minimizada e identidades dos serviços preservados. Falha exige recuperação por imagens anteriores compatíveis, sem apagar dados; rollback não conta como segurança corrigida.

### Retomada do checkout

Após correção validada/publicada, renovar o inventário/recibo Orders e reconciliar apenas os pins fonte do Pillow com o runtime já preparado, sem ampliar cegamente o gate47af72bd. Não declarar Mercado Pago publicado nesta change.

## Risks / Trade-offs

Pillow é biblioteca usada pelos motores especializados: não confundir um upgrade de pacote com licença/compatibilidade automaticamente aprovadas. O proprietário autorizou essa correção pontual; manter avaliação documentada de formatos/qualidade/recursos e qualquer bloqueio. Presença em faixa vulnerável confirma necessidade de correção, mas não prova exploração no ambiente. PR/CI e fechamento de alertas do manifest não provam imagem atualizada; confirmar versão efetiva dos seis serviços.

## Migration Plan

Sem migration. Preparar imagens/rollback antes da janela; registrar SHA/imagens e configuração antes/depois. Preservar histórico financeiro, filas e arquivos originais/derivados. Não arquivar/sincronizar specs até revisão humana e evidência da publicação.

## Refatoração proporcional

Não há limpeza de runtime elegível. O teste técnico do workflow anterior reconhecia recusa válida somente na categoria `protected`, embora o classificador já possua `dependencies`. Ajustar exclusivamente essa asserção para reconhecer ambas **apenas quando a publicação API/web foi recusada**, com regressão de dependência isolada. Nenhum allowlist, executor, manifesto de aprovação ou classificador de produção antigo é ampliado; código de aplicação não revisado continua falhando.
