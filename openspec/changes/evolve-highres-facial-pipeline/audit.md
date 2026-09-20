# Auditoria e baseline

## Fonte e autorização

Pedido integral recebido em 19/09/2026, iniciativa high-res. Proprietário autorizou medição privada nesta conversa; localização, origem e manifesto do corpus ainda não fornecidos. Não executar sobre fotografias arbitrárias encontradas no disco. Proposta e implementação local autorizadas; deploy remoto não autorizado.

## Fluxo observado

1. `main.py: upload /admin/photo-assets/{id}/source` valida JPEG, grava `safe_source_path(photo)` e cria MediaJob; no estado inicial lê todo body e escreve diretamente o destino.
2. `worker.process_next_media_job` reserva MediaJob; `media.generate_derivatives` aplica EXIF transpose e gera thumbnail 480, admin_preview 2000 e client_preview 1600. O limite usa `(width, width*2)`, portanto retratos podem ultrapassar o maior lado nominal.
3. Depois dos derivados, `enqueue_photo_index_if_eligible` exige foto disponível, admin_preview pronta, client_preview pronta, configuração, rollout e política. Chave idempotente contém fingerprint da prévia/modelo/qualidade/geração.
4. `facial.worker.process_claimed_index_job → engine.replace_photo_index` lê admin_preview, exige client_preview e substitui atomicamente os envelopes de PhotoFaceEmbedding. FK composta já impõe foto/galeria.
5. `provider.OpenCvSFaceProvider` limita detecção a 1600/2 MP, alinha e extrai SFace na mesma imagem reduzida. Caixas permanecem nesse espaço; engine fornece dimensões do derivado ao avaliador: inconsistência quando ocorre redução adicional.
6. `preview_adjustment.enqueue_after_derivatives` ocorre depois do commit de mídia, mas não espera conclusão facial. Worker independente usa admin_preview. Perfil RawTherapee muda exposição/tons, sem crop; engine rejeita alteração de dimensões. Não há reindexação direta pelo ajuste.
7. Selfie usa armazenamento AEAD temporário, snapshot de jobs e comparação NumPy dos embeddings existentes, sem detector sobre o acervo. Isolamento por galeria/modelo/qualidade/fingerprint. Referência eliminada no terminal, retenção teto 15 minutos; candidatas 24 horas.
8. Purge/lifecycle existentes removem embeddings, consultas e armazenamento por escopo. Original de acervo não tem lifecycle temporário explícito. Regeneração convencional ainda depende dele.
9. Galeria cliente usa GalleryPresentation, grupos best/other e cartões existentes. Não há API de regiões ou clique facial. A ampliação e marcadores comerciais precisam integração sem duplicação de fotos.

## Changes relacionadas e precedência

- `integrate-private-facial-filter`: índice cifrado, consulta, consentimento, qualidade, purge; suas regras de fonte após prévias são substituídas somente para fotos opt-in high-res.
- `productionize-facial-search`: limite do detector, workers separados, rollout e capacidade; gates de produção continuam pendentes.
- `auto-enable-facial-processing-for-new-galleries`: default general condicionado ao ambiente, exceções suspensas preservadas.
- `add-optional-preview-auto-adjustment` e `gallery-preview-exposure-and-installable-ui`: preservar fila/configuração/engine/limpeza, adicionar barreira anterior e invariável geométrica.
- Mudanças locais preexistentes em continuidade de notificações/branding/compras e `.codex-tmp/` são externas a esta iniciativa.

## Baseline e limites da evidência

O benchmark histórico documenta throughput ARM (419 fotos/430,467 s), mas não contém ground truth que permita inferir recall do lote atual. Contagem de fotos sem embedding não é falso negativo comprovado. Baseline local de regressão: 39 testes aprovados, 164,68 s; números reais antes/depois, calibração e tuning ARM permanecem dependentes do corpus anotado e execução autorizada no host. Testes sintéticos comprovam geometria/lifecycle/isolamento, não precisão de reconhecimento no domínio real. Resultados posteriores estão em validation.md e report.md.

## Riscos de integração

Não apagar fontes legadas retroativamente. Para fontes novas temporárias, regravar proteção a partir da prévia limpa durável, nunca redetectar. Retirada de original implica reupload para trocar modelo. Espelhamento Drive de originais, previsto no roadmap anterior, não deve criar cópia escondida para fotos opt-in. Não liberar ou excluir fonte enquanto job que a lê estiver ativo; falhas têm TTL explícito e estado reupload_required quando expirado.
