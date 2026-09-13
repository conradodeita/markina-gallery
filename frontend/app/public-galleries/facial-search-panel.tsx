"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { FacialApiError, facialSearchApi, type FacialSearchAvailability, type FacialSearchResult } from "../facial-search-client";
import { MarkinaButton, StatusBadge, SystemState } from "../ui-kit";

const terminalStates = new Set(["ready", "no_face", "multiple_faces", "low_quality", "index_incomplete", "no_candidates", "cancelled", "expired", "failed"]);
const defaultMaxReferenceBytes = 30 * 1024 * 1024;
const stateLabels: Record<string, string> = {
  queued: "Busca na fila",
  waiting_index: "Preparando as fotos",
  validating_reference: "Validando a foto enviada",
  searching: "Procurando possibilidades",
  ranking: "Organizando resultados",
  ready: "Resultados prontos",
  no_face: "Nenhum rosto foi detectado",
  multiple_faces: "A foto enviada contém mais de um rosto",
  low_quality: "A foto não tem qualidade suficiente",
  index_incomplete: "As fotos da galeria não ficaram prontas a tempo",
  no_candidates: "Nenhuma possibilidade foi encontrada",
  cancelled: "Busca cancelada",
  expired: "A busca expirou",
  failed: "Não foi possível concluir a busca",
};

export function FacialSearchPanel({
  galleryId,
  result,
  onResult,
}: {
  galleryId: string;
  result: FacialSearchResult | null;
  onResult: (result: FacialSearchResult | null) => void;
}) {
  const [availability, setAvailability] = useState<FacialSearchAvailability | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [consented, setConsented] = useState(false);
  const [subjectDeclaration, setSubjectDeclaration] = useState<"adult" | "minor" | "">("");
  const [guardianConfirmed, setGuardianConfirmed] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const libraryInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const consentDialog = useRef<HTMLElement>(null);
  const polling = useRef({ signature: "", delay: 0 });
  const storageKey = `markina:facial-search:${galleryId}`;

  function closeDialog() {
    setDialogOpen(false);
    setConsented(false);
    setSubjectDeclaration("");
    setGuardianConfirmed(false);
    setSelectedFile(null);
    if (libraryInput.current) libraryInput.current.value = "";
    if (cameraInput.current) cameraInput.current.value = "";
  }

  function chooseReference(file: File | undefined, source: "library" | "camera") {
    if (!file) return;
    const sourceInput = source === "library" ? libraryInput.current : cameraInput.current;
    if (file.type !== "image/jpeg") {
      setSelectedFile(null);
      setError("Escolha uma foto no formato JPEG.");
      if (sourceInput) sourceInput.value = "";
      return;
    }
    if (file.size > (availability?.max_reference_bytes ?? defaultMaxReferenceBytes)) {
      setSelectedFile(null);
      setError("Escolha uma foto JPEG de até 30 MB.");
      if (sourceInput) sourceInput.value = "";
      return;
    }
    setSelectedFile(file);
    setError("");
    const otherInput = source === "library" ? cameraInput.current : libraryInput.current;
    if (otherInput) otherInput.value = "";
  }

  useEffect(() => {
    let active = true;
    const restored = window.sessionStorage.getItem(storageKey);
    facialSearchApi.availability(galleryId)
      .then((value) => {
        if (!active) return;
        setAvailability(value);
      })
      .catch(() => { if (active) setAvailability({ state: "unavailable", manual_selection_available: true, minor_search_available: false }); });
    if (restored) {
      facialSearchApi.read(galleryId, restored)
        .then((value) => { if (active) onResult(value); })
        .catch(() => window.sessionStorage.removeItem(storageKey));
    } else {
      facialSearchApi.latest(galleryId)
        .then((latest) => {
          if (!active || !latest?.id || !latest?.status || !latest?.progress) return;
          window.sessionStorage.setItem(storageKey, latest.id);
          onResult(latest);
        })
        .catch(() => undefined);
    }
    return () => { active = false; };
  }, [galleryId, onResult, storageKey]);

  useEffect(() => {
    if (!result || terminalStates.has(result.status)) return;
    const signature = `${result.status}:${result.progress.index.ready}:${result.progress.comparison.done}`;
    const baseDelay = result.poll_after_ms ?? 2000;
    polling.current = polling.current.signature === signature
      ? { signature, delay: Math.min(10_000, Math.max(baseDelay, Math.round(polling.current.delay * 1.5))) }
      : { signature, delay: baseDelay };
    const timer = window.setTimeout(() => {
      facialSearchApi.read(galleryId, result.id)
        .then(onResult)
        .catch((cause) => {
          if (cause instanceof FacialApiError && cause.status === 404) {
            window.sessionStorage.removeItem(storageKey);
            onResult(null);
            return;
          }
          setError(cause instanceof Error ? cause.message : "Não foi possível atualizar a busca.");
        });
    }, polling.current.delay);
    return () => window.clearTimeout(timer);
  }, [galleryId, onResult, result, storageKey]);

  useEffect(() => {
    if (dialogOpen) consentDialog.current?.focus();
  }, [dialogOpen]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const file = selectedFile;
    if (!file || file.type !== "image/jpeg") {
      setError("Escolha uma foto JPEG nítida com apenas um rosto.");
      return;
    }
    if (!consented || !availability?.consent_version || !subjectDeclaration) return;
    if (subjectDeclaration === "minor" && !guardianConfirmed) return;
    setBusy(true);
    setError("");
    try {
      const created = await facialSearchApi.create(
        galleryId,
        file,
        availability.consent_version,
        subjectDeclaration,
        subjectDeclaration === "minor"
          ? availability.minor_representation_reference ?? undefined
          : undefined,
      );
      window.sessionStorage.setItem(storageKey, created.id);
      onResult(created);
      closeDialog();
    } catch (cause) {
      const retry = cause instanceof FacialApiError && cause.retryAfterSeconds
        ? ` Tente novamente em ${cause.retryAfterSeconds} segundos.`
        : "";
      setError(`${cause instanceof Error ? cause.message : "Não foi possível iniciar a busca."}${retry}`);
    } finally {
      setBusy(false);
    }
  }

  async function cancel(): Promise<boolean> {
    if (!result || busy) return false;
    setBusy(true);
    setError("");
    try {
      await facialSearchApi.cancel(galleryId, result.id);
      window.sessionStorage.removeItem(storageKey);
      onResult(null);
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível excluir a busca.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  if (!availability) return <SystemState tone="loading" title="Verificando busca por rosto" detail="A seleção manual continua disponível." />;
  if (availability.state === "unavailable") return null;
  const progressTotal = result?.status === "waiting_index" ? result.progress.index.total : result?.progress.comparison.total ?? 0;
  const progressDone = result?.status === "waiting_index" ? result.progress.index.ready : result?.progress.comparison.done ?? 0;
  const progressValue = progressTotal ? Math.round(progressDone / progressTotal * 100) : 0;
  const referenceRetentionMinutes = Math.ceil((availability.reference_retention_seconds ?? 900) / 60);
  const candidateRetentionHours = Math.ceil((availability.candidate_retention_seconds ?? 86400) / 3600);
  return (
    <section className="facial-search-panel" aria-labelledby="facial-search-title">
      <div><p className="eyebrow">Encontre mais rápido</p><h2 id="facial-search-title">Procurar por reconhecimento facial</h2><p>Use uma foto nítida como filtro desta galeria. O resultado mostra possibilidades; você decide o que selecionar.</p></div>
      {!result ? <MarkinaButton type="button" onClick={() => { setDialogOpen(true); setError(""); }}>Enviar foto para procurar</MarkinaButton> : (
        <div className="facial-search-status" aria-live="polite">
          <div><StatusBadge tone={result.status === "ready" ? "success" : result.status === "failed" ? "danger" : "neutral"}>{stateLabels[result.status] ?? result.status}</StatusBadge><span>{result.reference_deleted ? "Foto de referência eliminada" : "Foto protegida temporariamente"}</span></div>
          {!terminalStates.has(result.status) ? <><progress value={progressValue} max={100} aria-label="Progresso da busca facial" /><small>{progressValue}% concluído · {result.estimate?.remaining_items ?? 0} itens restantes. Tempo restante ainda não disponível. Você pode fechar esta tela; avisaremos quando terminar.</small></> : null}
          {result.status === "no_face" ? <p>Tente uma foto frontal, bem iluminada e com o rosto inteiro.</p> : null}
          {result.status === "multiple_faces" ? <p>Recorte a imagem para manter somente a pessoa procurada.</p> : null}
          {result.status === "low_quality" ? <p>Envie outra foto com mais nitidez e melhor iluminação.</p> : null}
          {result.status === "index_incomplete" || result.status === "failed" ? <p>A seleção manual permanece disponível. Você também pode tentar uma nova busca.</p> : null}
          <div className="gallery-access-actions"><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => { void cancel(); }}>{terminalStates.has(result.status) ? "Excluir busca" : "Cancelar busca"}</MarkinaButton>{terminalStates.has(result.status) ? <MarkinaButton type="button" disabled={busy} onClick={() => { void cancel().then((removed) => { if (removed) setDialogOpen(true); }); }}>Nova busca</MarkinaButton> : null}</div>
        </div>
      )}
      {error && !dialogOpen ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
      {dialogOpen ? (
        <div className="mk-dialog-backdrop facial-consent-backdrop" role="presentation" onMouseDown={closeDialog}>
          <section
            ref={consentDialog}
            className="mk-dialog facial-consent-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="facial-consent-title"
            aria-describedby="facial-consent-purpose facial-consent-limits"
            tabIndex={-1}
            onMouseDown={(event) => event.stopPropagation()}
            onKeyDown={(event) => { if (event.key === "Escape") closeDialog(); }}
          >
            <header className="facial-consent-header">
              <p className="eyebrow">Consentimento específico</p>
              <h2 id="facial-consent-title">Busca facial nesta galeria</h2>
              <p id="facial-consent-purpose">Antes de enviar, entenda como a foto será usada para procurar possíveis correspondências.</p>
            </header>
            <div className="facial-consent-privacy" id="facial-consent-limits">
              <strong>Uso temporário e restrito</strong>
              <p>A foto escolhida e a representação biométrica facial extraída dela serão usadas somente para procurar possíveis correspondências nesta galeria.</p>
              <p>Não há cadastro biométrico permanente. Esses dados serão eliminados após o processamento ou, no máximo, em {referenceRetentionMinutes} minutos.</p>
              <small>Os resultados expiram em até {candidateRetentionHours} horas. São apenas sugestões, não confirmam identidade e podem conter correspondências incorretas.</small>
            </div>
            <form onSubmit={submit}>
              <section className="facial-consent-step" aria-labelledby="facial-reference-source-title">
                <div className="facial-consent-step-heading">
                  <span aria-hidden="true">1</span>
                  <div>
                    <h3 id="facial-reference-source-title">Escolha a foto</h3>
                    <p>Prefira uma JPEG de até 30 MB semelhante a foto de documento: frontal, nítida, bem iluminada, com o rosto inteiro e somente uma pessoa.</p>
                    <small>Use apenas uma foto do rosto. Não fotografe nem envie documento de identidade.</small>
                  </div>
                </div>
                <input
                  ref={libraryInput}
                  type="file"
                  accept="image/jpeg"
                  aria-label="Escolher foto JPEG da galeria do celular"
                  hidden
                  onChange={(event) => chooseReference(event.currentTarget.files?.[0], "library")}
                />
                <input
                  ref={cameraInput}
                  type="file"
                  accept="image/jpeg"
                  capture="user"
                  aria-label="Tirar foto JPEG com a câmera"
                  hidden
                  onChange={(event) => chooseReference(event.currentTarget.files?.[0], "camera")}
                />
                <div className="facial-reference-actions">
                  <MarkinaButton type="button" disabled={busy} onClick={() => libraryInput.current?.click()}>Escolher foto do celular</MarkinaButton>
                  <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => cameraInput.current?.click()}>Usar câmera</MarkinaButton>
                </div>
                {selectedFile ? <p className="facial-reference-selected" role="status">Foto selecionada e pronta para envio.</p> : null}
                {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
              </section>
              <fieldset className="facial-consent-step facial-consent-subject">
                <legend><span aria-hidden="true">2</span> Quem aparece na foto?</legend>
                <label className="gallery-toggle"><input type="radio" name="facial-subject" value="adult" checked={subjectDeclaration === "adult"} onChange={() => { setSubjectDeclaration("adult"); setGuardianConfirmed(false); }} required /> Pessoa adulta</label>
                <label className="gallery-toggle"><input type="radio" name="facial-subject" value="minor" checked={subjectDeclaration === "minor"} disabled={!availability.minor_search_available} onChange={() => setSubjectDeclaration("minor")} required /> Criança ou adolescente</label>
              </fieldset>
              {subjectDeclaration === "minor" ? <label className="gallery-toggle facial-consent-check"><input type="checkbox" checked={guardianConfirmed} onChange={(event) => setGuardianConfirmed(event.target.checked)} required /> Declaro que sou pai, mãe ou responsável legal pela criança ou adolescente que aparece na foto e possuo autorização para enviá-la.</label> : null}
              <label className="gallery-toggle facial-consent-check"><input type="checkbox" checked={consented} onChange={(event) => setConsented(event.target.checked)} required /> Autorizo, de forma livre, informada e específica, o tratamento temporário desta foto e dos dados biométricos extraídos exclusivamente para procurar possíveis correspondências nesta galeria. Li e compreendi as informações acima.</label>
              <p className="field-hint">A busca é opcional. Você pode cancelar ou continuar procurando e selecionando as fotos manualmente.{availability.legal_notice_version ? ` Aviso ${availability.legal_notice_version}.` : ""}{!availability.minor_search_available ? " A busca de criança ainda não está disponível neste ambiente." : ""}</p>
              <div className="mk-dialog__actions facial-consent-actions"><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={closeDialog}>Cancelar</MarkinaButton><MarkinaButton disabled={!selectedFile || !consented || !subjectDeclaration || (subjectDeclaration === "minor" && !guardianConfirmed) || busy}>{busy ? "Enviando…" : "Autorizar e procurar fotos"}</MarkinaButton></div>
            </form>
          </section>
        </div>
      ) : null}
    </section>
  );
}
