"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { FacialApiError, FacialUploadUnconfirmedError, facialProgressPercent, facialSearchApi, type FacialSearchAvailability, type FacialSearchResult } from "../facial-search-client";
import { clearFacialSearchStorage, facialSearchStorageKey, readFacialSearchStorage, rememberFacialSearch } from "../facial-search-storage";
import { PUSH_LOGOUT_EVENT } from "../push-device";
import { MarkinaButton, StatusBadge, SystemState } from "../ui-kit";

const terminalStates = new Set(["ready", "no_face", "multiple_faces", "low_quality", "index_incomplete", "no_candidates", "cancelled", "expired", "failed"]);
const defaultMaxReferenceBytes = 30 * 1024 * 1024;
const stateLabels: Record<string, string> = {
  queued: "Busca na fila",
  waiting_index: "Preparando as fotos",
  validating_reference: "Preparando a referência",
  searching: "Procurando possibilidades",
  ranking: "Organizando resultados",
  ready: "Resultados prontos",
  no_face: "Nenhum rosto foi detectado",
  multiple_faces: "Não foi possível isolar um único rosto",
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
  const showDialog = dialogOpen;
  const [consented, setConsented] = useState(true);
  const [unconfirmedRequest, setUnconfirmedRequest] = useState<string | null>(null);
  const subjectDeclaration = "conditional" as const;
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraStarting, setCameraStarting] = useState(false);
  const [cameraFacing, setCameraFacing] = useState<"environment" | "user">("environment");
  const cameraMode = cameraActive || cameraStarting;
  const [cameraAspect, setCameraAspect] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pollFailedRequestId, setPollFailedRequestId] = useState<string | null>(null);
  const [manualPollAttempt, setManualPollAttempt] = useState(0);
  const libraryInput = useRef<HTMLInputElement>(null);
  const cameraVideo = useRef<HTMLVideoElement>(null);
  const cameraStream = useRef<MediaStream | null>(null);
  const cameraAttempt = useRef(0);
  const consentDialog = useRef<HTMLElement>(null);
  const polling = useRef({ signature: "", delay: 0 });
  const manualPollRequest = useRef<string | null>(null);
  const restoreAllowed = useRef(true);
  const initialResult = useRef(result);
  const storageKey = useRef<string | null>(null);
  const contextVersion = useRef(0);

  useEffect(() => {
    if (result && result !== initialResult.current) restoreAllowed.current = false;
  }, [result]);

  function stopCamera() {
    cameraAttempt.current += 1;
    cameraStream.current?.getTracks().forEach((track) => track.stop());
    cameraStream.current = null;
    setCameraActive(false);
    setCameraStarting(false);
  }

  function closeDialog() {
    stopCamera();
    setDialogOpen(false);
    setConsented(true);
    setUnconfirmedRequest(null);
    setSelectedFile(null);
    if (libraryInput.current) libraryInput.current.value = "";
  }

  function chooseReference(file: File | undefined, source: "library" | "camera") {
    if (!file) return;
    const sourceInput = source === "library" ? libraryInput.current : null;
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
    setUnconfirmedRequest(null);
    setSelectedFile(file);
    setError("");
    const otherInput = source === "library" ? null : libraryInput.current;
    if (otherInput) otherInput.value = "";
  }

  async function startGuidedCamera(facing: "environment" | "user" = "environment") {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Este navegador não permite abrir a câmera aqui. Escolha uma foto do dispositivo.");
      return;
    }
    setCameraStarting(true);
    const attempt = ++cameraAttempt.current;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: facing }, width: { ideal: 1280 }, height: { ideal: 1280 } },
      });
      if (attempt !== cameraAttempt.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      cameraStream.current = stream;
      setCameraFacing(facing);
      setCameraActive(true);
    } catch {
      if (attempt === cameraAttempt.current) {
        stopCamera();
        setError("Não foi possível abrir a câmera. Permita o acesso ou escolha uma foto do dispositivo.");
      }
    } finally {
      if (attempt === cameraAttempt.current) setCameraStarting(false);
    }
  }

  async function captureGuidedPhoto() {
    const video = cameraVideo.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      setError("A câmera ainda está iniciando. Aguarde a imagem aparecer e tente novamente.");
      return;
    }
    const attempt = cameraAttempt.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setError("Não foi possível preparar a captura. Tente novamente ou escolha uma foto.");
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (attempt !== cameraAttempt.current) return;
    if (!blob) {
      setError("Não foi possível preparar a captura. Tente novamente ou escolha uma foto.");
      return;
    }
    chooseReference(
      new File([blob], "captura-facial.jpg", { type: "image/jpeg", lastModified: Date.now() }),
      "camera",
    );
    stopCamera();
  }

  useEffect(() => {
    if (cameraActive && cameraVideo.current && cameraStream.current) {
      cameraVideo.current.srcObject = cameraStream.current;
    }
  }, [cameraActive]);

  useEffect(() => () => {
    cameraAttempt.current += 1;
    cameraStream.current?.getTracks().forEach((track) => track.stop());
  }, []);

  useEffect(() => {
    let active = true;
    let loaded = false;
    let refreshAttempt = 0;
    const invalidate = () => {
      contextVersion.current += 1;
      storageKey.current = null;
      clearFacialSearchStorage();
      closeDialog();
      onResult(null);
      setAvailability({ state: "unavailable", manual_selection_available: true, minor_search_available: false });
    };
    const refresh = async () => {
      const attempt = ++refreshAttempt;
      let version = contextVersion.current;
      try {
        const value = await facialSearchApi.availability(galleryId);
        if (!active || attempt !== refreshAttempt || version !== contextVersion.current) return;
        const key = facialSearchStorageKey(value.storage_context, galleryId);
        const changed = loaded && (!key || storageKey.current !== key);
        clearFacialSearchStorage(key ? value.storage_context : undefined);
        storageKey.current = key;
        setAvailability(value);
        if (changed) {
          version = ++contextVersion.current;
          closeDialog();
          onResult(null);
          restoreAllowed.current = true;
        }
        if (loaded && !changed) return;
        loaded = true;
        const restored = readFacialSearchStorage(key);
        try {
          const latest = restored ? await facialSearchApi.read(galleryId, restored) : await facialSearchApi.latest(galleryId);
          if (!active || version !== contextVersion.current || !restoreAllowed.current || !latest?.id || !latest?.status || !latest?.progress) return;
          rememberFacialSearch(key, latest.id);
          onResult(latest);
        } catch (cause) {
          if (!active || version !== contextVersion.current) return;
          rememberFacialSearch(key, null);
          if (cause instanceof FacialApiError && [401, 403].includes(cause.status)) invalidate();
        }
      } catch {
        if (active && attempt === refreshAttempt && version === contextVersion.current) invalidate();
      }
    };
    void refresh();
    window.addEventListener("focus", refresh);
    window.addEventListener(PUSH_LOGOUT_EVENT, invalidate);
    return () => {
      active = false;
      contextVersion.current += 1;
      window.removeEventListener("focus", refresh);
      window.removeEventListener(PUSH_LOGOUT_EVENT, invalidate);
    };
  }, [galleryId, onResult]);

  useEffect(() => {
    if (!result || terminalStates.has(result.status)) return;
    let active = true;
    let timer: number | undefined;
    const signature = `${result.status}:${result.progress.index.ready}:${result.progress.comparison.done}`;
    const baseDelay = result.poll_after_ms ?? 2000;
    polling.current = polling.current.signature === signature
      ? { signature, delay: Math.min(10_000, Math.max(baseDelay, Math.round(polling.current.delay * 1.5))) }
      : { signature, delay: baseDelay };
    const requestedManually = manualPollRequest.current === result.id;
    if (requestedManually) manualPollRequest.current = null;
    const poll = async (retry: number) => {
      const version = contextVersion.current;
      try {
        const value = await facialSearchApi.read(galleryId, result.id);
        if (!active || version !== contextVersion.current) return;
        setPollFailedRequestId(null);
        setError("");
        onResult(value);
      } catch (cause) {
        if (!active || version !== contextVersion.current) return;
        if (cause instanceof FacialApiError && [401, 403, 404].includes(cause.status)) {
          contextVersion.current += 1;
          clearFacialSearchStorage();
          onResult(null);
          closeDialog();
          if (cause.status !== 404) setAvailability({ state: "unavailable", manual_selection_available: true, minor_search_available: false });
          return;
        }
        const transient = !(cause instanceof FacialApiError)
          || cause.status === 429 || cause.status >= 500;
        if (transient && retry < 3) {
          setError("A busca foi iniciada, mas não conseguimos atualizar o resultado. Verifique sua conexão; tentaremos consultar novamente.");
          timer = window.setTimeout(() => { void poll(retry + 1); }, Math.min(8000, 1000 * (2 ** retry)));
          return;
        }
        setPollFailedRequestId(result.id);
        setError(transient
          ? "A busca foi iniciada, mas não conseguimos atualizar o resultado. Toque em Atualizar busca quando a conexão voltar."
          : cause instanceof Error ? cause.message : "Não foi possível atualizar a busca.");
      }
    };
    timer = window.setTimeout(() => { void poll(0); }, requestedManually ? 0 : polling.current.delay);
    return () => { active = false; if (timer !== undefined) window.clearTimeout(timer); };
  }, [galleryId, manualPollAttempt, onResult, result]);

  useEffect(() => {
    if (!showDialog) return;
    consentDialog.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previousOverflow; };
  }, [showDialog, cameraMode]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const file = selectedFile;
    if (!file || file.type !== "image/jpeg") {
      setError("Escolha uma foto JPEG nítida com apenas um rosto.");
      return;
    }
    if (!consented || !availability?.consent_version || busy || unconfirmedRequest) return;
    setBusy(true);
    setError("");
    const version = contextVersion.current;
    try {
      const created = await facialSearchApi.create(
        galleryId, file, availability.consent_version, subjectDeclaration,
      );
      if (version !== contextVersion.current) return;
      rememberFacialSearch(storageKey.current, created.id);
      onResult(created);
      closeDialog();
    } catch (cause) {
      if (version !== contextVersion.current) return;
      if (cause instanceof FacialUploadUnconfirmedError) {
        setUnconfirmedRequest(cause.requestId);
        rememberFacialSearch(storageKey.current, cause.requestId);
      }
      if (cause instanceof FacialApiError && [401, 403].includes(cause.status)) {
        contextVersion.current += 1;
        clearFacialSearchStorage();
        onResult(null);
        closeDialog();
        setAvailability({ state: "unavailable", manual_selection_available: true, minor_search_available: false });
      }
      const retry = cause instanceof FacialApiError && cause.retryAfterSeconds
        ? ` Tente novamente em ${cause.retryAfterSeconds} segundos.`
        : "";
      const message = cause instanceof FacialApiError
        ? cause.message
        : "Não foi possível confirmar o envio da foto. Verifique sua conexão e confira se a busca apareceu antes de tentar novamente.";
      setError(`${message}${retry}`);
    } finally {
      setBusy(false);
    }
  }

  async function confirmUpload() {
    if (!unconfirmedRequest || busy) return;
    setBusy(true);
    const version = contextVersion.current;
    try {
      const recovered = await facialSearchApi.read(galleryId, unconfirmedRequest);
      if (version !== contextVersion.current) return;
      if (recovered?.id !== unconfirmedRequest || !recovered.status || !recovered.progress) throw new Error("Invalid confirmation");
      rememberFacialSearch(storageKey.current, recovered.id);
      onResult(recovered);
      setError("");
      closeDialog();
    } catch (cause) {
      if (version !== contextVersion.current) return;
      if (cause instanceof FacialApiError && [401, 403].includes(cause.status)) {
        contextVersion.current += 1;
        clearFacialSearchStorage();
        onResult(null);
        closeDialog();
        setAvailability({ state: "unavailable", manual_selection_available: true, minor_search_available: false });
      }
      setError("O envio ainda não foi confirmado. Confira novamente quando a conexão voltar ou escolha a foto para iniciar uma nova tentativa.");
    } finally {
      setBusy(false);
    }
  }

  async function cancel(): Promise<boolean> {
    if (!result || busy) return false;
    setBusy(true);
    setError("");
    const version = contextVersion.current;
    try {
      await facialSearchApi.cancel(galleryId, result.id);
      if (version !== contextVersion.current) return false;
      rememberFacialSearch(storageKey.current, null);
      onResult(null);
      return true;
    } catch (cause) {
      if (version !== contextVersion.current) return false;
      if (cause instanceof FacialApiError && [401, 403, 404].includes(cause.status)) {
        contextVersion.current += 1;
        clearFacialSearchStorage();
        onResult(null);
        closeDialog();
        if (cause.status !== 404) setAvailability({ state: "unavailable", manual_selection_available: true, minor_search_available: false });
      }
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
  const progressValue = facialProgressPercent(progressDone, progressTotal) ?? 0;
  const referenceRetentionMinutes = Math.ceil((availability.reference_retention_seconds ?? 900) / 60);
  const candidateRetentionHours = Math.ceil((availability.candidate_retention_seconds ?? 86400) / 3600);
  return (
    <section className="facial-search-panel" aria-labelledby="facial-search-title">
      <div><p className="eyebrow">Encontre mais rápido</p><h2 id="facial-search-title">Procurar por reconhecimento facial</h2><p>Use uma foto nítida como filtro desta galeria. O resultado mostra possibilidades; você decide o que selecionar.</p></div>
      {!result ? <MarkinaButton type="button" onClick={() => { setDialogOpen(true); setError(""); }}>Enviar foto para procurar</MarkinaButton> : (
        <div className="facial-search-status" aria-live="polite">
          <div><StatusBadge tone={result.status === "ready" ? "success" : result.status === "failed" ? "danger" : "neutral"}>{stateLabels[result.status] ?? result.status}</StatusBadge><span>{result.reference_deleted ? "Sem imagem temporária nesta busca" : "Foto protegida temporariamente"}</span></div>
          {!terminalStates.has(result.status) ? <><progress value={progressValue} max={100} aria-label="Progresso da busca facial" /><small>{progressValue}% concluído · {progressDone} de {progressTotal} fotos nesta etapa. Tempo restante ainda não disponível. Você pode fechar esta tela; avisaremos quando terminar.</small></> : null}
          {result.status === "no_face" ? <p>Tente uma foto frontal, bem iluminada e com o rosto inteiro.</p> : null}
          {result.status === "multiple_faces" ? <p>Detectamos mais de uma região possível. Recorte a imagem para manter somente o rosto da pessoa procurada.</p> : null}
          {result.status === "low_quality" ? <p>Envie outra foto com mais nitidez e melhor iluminação.</p> : null}
          {result.status === "no_candidates" ? <p>Não encontramos sugestões confiáveis com esta foto. Isso não confirma que a pessoa não esteja nesta galeria. Tente outra foto mais nítida ou continue pela seleção manual.</p> : null}
          {result.status === "index_incomplete" || result.status === "failed" ? <p>A seleção manual permanece disponível. Você também pode tentar uma nova busca.</p> : null}
          <div className="gallery-access-actions">{pollFailedRequestId === result.id ? <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => { manualPollRequest.current = result.id; setPollFailedRequestId(null); setError(""); setManualPollAttempt((attempt) => attempt + 1); }}>Atualizar busca</MarkinaButton> : null}<MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => { void cancel(); }}>{terminalStates.has(result.status) ? "Excluir busca" : "Cancelar busca"}</MarkinaButton>{terminalStates.has(result.status) ? <MarkinaButton type="button" disabled={busy} onClick={() => { void cancel().then((removed) => { if (removed) setDialogOpen(true); }); }}>Nova busca</MarkinaButton> : null}</div>
        </div>
      )}
      {error && !showDialog ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
      {showDialog ? (
        <div className="mk-dialog-backdrop facial-consent-backdrop" role="presentation" onMouseDown={closeDialog}>
          <section
            ref={consentDialog}
            className={`mk-dialog facial-consent-dialog${cameraMode ? " facial-consent-dialog--camera" : ""}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby={cameraMode ? "facial-camera-title" : "facial-consent-title"}
            aria-describedby={cameraMode ? "facial-camera-guidance" : "facial-consent-purpose"}
            tabIndex={-1}
            onMouseDown={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key === "Escape") { event.preventDefault(); if (cameraMode) stopCamera(); else closeDialog(); }
              if (event.key !== "Tab") return;
              const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("button:not([disabled]), input:not([disabled]), summary, [tabindex='0']"))
                .filter((element) => !element.closest("[hidden]") && (!element.closest("details:not([open])") || element.tagName === "SUMMARY"));
              const first = controls[0], last = controls[controls.length - 1];
              if (!first) { event.preventDefault(); return; }
              if (event.shiftKey && (document.activeElement === first || document.activeElement === event.currentTarget)) { event.preventDefault(); last.focus(); }
              if (!event.shiftKey && (document.activeElement === last || document.activeElement === event.currentTarget)) { event.preventDefault(); first.focus(); }
            }}
          >
            {cameraMode ? <div className="facial-guided-camera" aria-label="Captura guiada obrigatória">
              <header><h2 id="facial-camera-title">Enquadre o rosto</h2></header>
              <div className="facial-guided-camera-stage">
                <div className="facial-guided-camera-frame" style={{ width: `min(100%, calc(60dvh * ${cameraAspect}))`, aspectRatio: cameraAspect }}>
                  <video ref={cameraVideo} autoPlay playsInline muted aria-label="Enquadramento ao vivo da câmera" onLoadedMetadata={(event) => {
                    const video = event.currentTarget;
                    if (video.videoWidth && video.videoHeight) setCameraAspect(video.videoWidth / video.videoHeight);
                  }} />
                </div>
              </div>
              <p id="facial-camera-guidance">Posicione o rosto dentro do contorno. Olhe para a câmera, procure uma luz de frente e mantenha o celular firme.</p>
              {cameraStarting ? <p role="status">Abrindo câmera…</p> : null}
              {error ? <p role="alert">{error}</p> : null}
              <div className="facial-reference-actions">
                <MarkinaButton type="button" disabled={busy || cameraStarting || !cameraActive} onClick={() => { void captureGuidedPhoto(); }}>Capturar rosto</MarkinaButton>
                <MarkinaButton type="button" variant="secondary" disabled={busy || cameraStarting} onClick={() => { const next = cameraFacing === "environment" ? "user" : "environment"; stopCamera(); void startGuidedCamera(next); }}>{cameraFacing === "environment" ? "Usar câmera frontal" : "Usar câmera traseira"}</MarkinaButton>
                <MarkinaButton type="button" variant="secondary" onClick={stopCamera}>Cancelar câmera</MarkinaButton>
              </div>
            </div> : null}
            <div hidden={cameraMode}>
              <header className="facial-consent-header">
                <p className="eyebrow">Consentimento específico</p>
                <h2 id="facial-consent-title">Busca facial nesta galeria</h2>
                <p id="facial-consent-purpose">Antes de enviar, entenda como a foto será usada para procurar possíveis correspondências.</p>
              </header>
              <details className="facial-consent-privacy" id="facial-consent-limits">
                <summary>Uso temporário e restrito</summary>
                <p>A foto escolhida e a representação biométrica facial extraída dela serão usadas somente para procurar possíveis correspondências nesta galeria.</p>
                <p>Não há cadastro biométrico permanente. Esses dados serão eliminados após o processamento ou, no máximo, em {referenceRetentionMinutes} minutos.</p>
                <small>Os resultados expiram em até {candidateRetentionHours} horas. São apenas sugestões, não confirmam identidade e podem conter correspondências incorretas.</small>
              </details>
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
                  <div className="facial-reference-actions">
                    <MarkinaButton type="button" disabled={busy || cameraStarting} onClick={() => { stopCamera(); libraryInput.current?.click(); }}>Escolher foto do celular</MarkinaButton>
                    <MarkinaButton type="button" variant="secondary" disabled={busy || cameraStarting} onClick={() => { setSelectedFile(null); void startGuidedCamera(); }}>{cameraStarting ? "Abrindo câmera…" : "Usar câmera"}</MarkinaButton>
                  </div>
                  {selectedFile ? <p className="facial-reference-selected" role="status">Foto selecionada e pronta para envio.</p> : null}
                  {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
                </section>
                <details className="facial-consent-details">
                  <summary>Leia a declaração de consentimento</summary>
                  <p id="facial-consent-declaration">Se a pessoa retratada for criança ou adolescente menor de 18 anos, declaro ser seu pai, sua mãe ou seu responsável legal. Autorizo, de forma livre, informada e específica, a busca de fotos dessa pessoa nesta galeria e o tratamento temporário da foto enviada e dos dados biométricos extraídos exclusivamente para procurar possíveis correspondências nesta galeria. Li e compreendi as informações acima.</p>
                </details>
                <label className="gallery-toggle facial-consent-check"><input type="checkbox" checked={consented} onChange={(event) => setConsented(event.target.checked)} required /> Autorizo a busca facial e o tratamento temporário nesta galeria. Se a pessoa for menor de 18 anos, declaro ser seu pai, sua mãe ou responsável legal.</label>
                <p className="field-hint">A busca é opcional. Você pode cancelar ou continuar procurando e selecionando as fotos manualmente.{availability.legal_notice_version ? ` Aviso ${availability.legal_notice_version}.` : ""}</p>
                {unconfirmedRequest ? <MarkinaButton type="button" disabled={busy} onClick={() => { void confirmUpload(); }}>{busy ? "Conferindo envio…" : "Conferir envio"}</MarkinaButton> : null}
                <div className="mk-dialog__actions facial-consent-actions"><MarkinaButton type="button" variant="secondary" disabled={busy} onClick={closeDialog}>Cancelar</MarkinaButton><MarkinaButton disabled={!selectedFile || !consented || busy || !!unconfirmedRequest}>{busy ? "Iniciando busca…" : "Autorizar e procurar fotos"}</MarkinaButton></div>
              </form>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
