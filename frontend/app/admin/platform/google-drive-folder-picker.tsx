"use client";

import { type FormEvent, useState } from "react";
import { MarkinaButton } from "../../ui-kit";

const DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file";
const GLOBAL_FOLDER_NAME = "Pick-your-Pic Global";
const FOLDER_MIME_TYPE = "application/vnd.google-apps.folder";

type PickerView = {
  setMimeTypes(value: string): PickerView;
  setIncludeFolders(value: boolean): PickerView;
  setSelectFolderEnabled(value: boolean): PickerView;
  setParent(value: string): PickerView;
  setMode(value: string): PickerView;
};

type PickerDialog = { setVisible(value: boolean): void };
type PickerBuilder = {
  addView(value: PickerView): PickerBuilder;
  setOAuthToken(value: string): PickerBuilder;
  setDeveloperKey(value: string): PickerBuilder;
  setAppId(value: string): PickerBuilder;
  setCallback(value: (data: Record<string, unknown>) => void): PickerBuilder;
  setTitle(value: string): PickerBuilder;
  setLocale(value: string): PickerBuilder;
  setMaxItems(value: number): PickerBuilder;
  setOrigin(value: string): PickerBuilder;
  build(): PickerDialog;
};

type GooglePicker = {
  Action: { PICKED: string };
  Response: { ACTION: string; DOCUMENTS: string };
  Document: { ID: string; NAME: string; MIME_TYPE: string };
  ViewId: { DOCS: string };
  DocsViewMode: { LIST: string };
  DocsView: new (viewId: string) => PickerView;
  PickerBuilder: new () => PickerBuilder;
};

type GoogleBrowser = Window & {
  gapi?: { load(name: string, callback: () => void): void };
  google?: { picker?: GooglePicker };
};

type PickerSession = {
  access_token: string;
  scope: string;
  expires_in: number;
  developer_key: string;
  project_number: string;
  expected_parent_folder_id: string;
};

let pickerLibrary: Promise<GooglePicker> | undefined;

function loadPickerLibrary(): Promise<GooglePicker> {
  if (pickerLibrary) return pickerLibrary;
  const loading: Promise<GooglePicker> = new Promise<GooglePicker>((resolve, reject) => {
    const target = window as GoogleBrowser;
    const initialize = () => {
      const api = target.gapi;
      if (!api) {
        reject(new Error("Google Picker indisponível."));
        return;
      }
      api.load("picker", () => {
        const picker = target.google?.picker;
        if (picker) resolve(picker);
        else reject(new Error("Google Picker indisponível."));
      });
    };
    const existing = document.getElementById("google-drive-picker-api") as HTMLScriptElement | null;
    if (existing) {
      if (target.gapi) initialize();
      else {
        existing.addEventListener("load", initialize, { once: true });
        existing.addEventListener("error", () => reject(new Error("Google Picker indisponível.")), { once: true });
      }
      return;
    }
    const script = document.createElement("script");
    script.id = "google-drive-picker-api";
    script.src = "https://apis.google.com/js/api.js";
    script.async = true;
    script.defer = true;
    script.onload = initialize;
    script.onerror = () => reject(new Error("Google Picker indisponível."));
    document.head.appendChild(script);
  }).catch((error: unknown) => {
    pickerLibrary = undefined;
    throw error;
  });
  pickerLibrary = loading;
  return loading;
}

function validSession(value: unknown): value is PickerSession {
  if (!value || typeof value !== "object") return false;
  const data = value as Partial<PickerSession>;
  return typeof data.access_token === "string" && /^[!-~]{1,8192}$/.test(data.access_token) &&
    data.scope === DRIVE_FILE_SCOPE && Number.isSafeInteger(data.expires_in) &&
    typeof data.expires_in === "number" && data.expires_in > 0 && data.expires_in <= 3600 &&
    typeof data.developer_key === "string" && /^[A-Za-z0-9_-]{20,256}$/.test(data.developer_key) &&
    typeof data.project_number === "string" && /^[1-9][0-9]{0,23}$/.test(data.project_number) &&
    typeof data.expected_parent_folder_id === "string" &&
    /^[A-Za-z0-9_-]{1,128}$/.test(data.expected_parent_folder_id);
}

export function GoogleDriveBackupFolderPicker() {
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [candidate, setCandidate] = useState<{ id: string; name: string } | null>(null);
  const [authorized, setAuthorized] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function startSelection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !password || !/^[0-9]{6}$/.test(totp)) return;
    const body = JSON.stringify({ current_password: password, totp_code: totp });
    setPassword("");
    setTotp("");
    setBusy(true);
    setError("");
    setCandidate(null);
    setAuthorized("");
    try {
      const response = await fetch("/api/admin/platform/drive/picker/session", {
        method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error",
        headers: { "Content-Type": "application/json" }, body,
      });
      if (!response.ok) throw new Error();
      const session: unknown = await response.json();
      if (!validSession(session)) throw new Error();
      const pickerApi = await loadPickerLibrary();
      const view = new pickerApi.DocsView(pickerApi.ViewId.DOCS)
        .setMimeTypes(FOLDER_MIME_TYPE)
        .setIncludeFolders(true)
        .setSelectFolderEnabled(true)
        .setParent(session.expected_parent_folder_id)
        .setMode(pickerApi.DocsViewMode.LIST);
      const pickerDialog: { current?: PickerDialog } = {};
      const builtPicker = new pickerApi.PickerBuilder()
        .addView(view)
        .setOAuthToken(session.access_token)
        .setDeveloperKey(session.developer_key)
        .setAppId(session.project_number)
        .setTitle("Selecione a pasta global de backup")
        .setLocale("pt-BR")
        .setMaxItems(1)
        .setOrigin(window.location.origin)
        .setCallback((data) => {
          pickerDialog.current?.setVisible(false);
          if (data[pickerApi.Response.ACTION] !== pickerApi.Action.PICKED) return;
          const items = data[pickerApi.Response.DOCUMENTS];
          const selected = Array.isArray(items) ? items[0] : null;
          if (!selected || typeof selected !== "object") {
            setError("Não foi possível identificar a pasta selecionada.");
            return;
          }
          const document = selected as Record<string, unknown>;
          const id = document[pickerApi.Document.ID];
          const name = document[pickerApi.Document.NAME];
          const mimeType = document[pickerApi.Document.MIME_TYPE];
          if (typeof id !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(id) ||
              name !== GLOBAL_FOLDER_NAME || mimeType !== FOLDER_MIME_TYPE) {
            setError("Selecione Pick-your-Pic Global dentro da raiz de backups.");
            return;
          }
          setCandidate({ id, name });
        })
        .build();
      pickerDialog.current = builtPicker;
      builtPicker.setVisible(true);
    } catch {
      setError("Não foi possível abrir o seletor. Confira a conexão e tente novamente.");
    } finally {
      setBusy(false);
    }
  }

  async function authorizeSelection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !candidate || !password || !/^[0-9]{6}$/.test(totp)) return;
    const body = JSON.stringify({
      folder_id: candidate.id, current_password: password, totp_code: totp,
    });
    setPassword("");
    setTotp("");
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/admin/platform/drive/picker/authorize", {
        method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error",
        headers: { "Content-Type": "application/json" }, body,
      });
      if (!response.ok) throw new Error();
      const result = await response.json() as { state?: unknown; folder_name?: unknown };
      if (result.state !== "selected" || result.folder_name !== GLOBAL_FOLDER_NAME) throw new Error();
      setAuthorized(GLOBAL_FOLDER_NAME);
      setCandidate(null);
    } catch {
      setError("Não foi possível autorizar essa pasta. Confira o caminho e tente novamente.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="mk-stack" aria-label="Destino global de backup">
    <h4>Destino global do backup</h4>
    <p>Selecione somente a pasta Pick-your-Pic Global em Oracle-Production-Backups. O acesso usa drive.file e não ativa a rotina de backup.</p>
    {authorized ? <p role="status">Pasta autorizada: {authorized}. O vínculo protegido e o ensaio sintético ainda precisam ser concluídos com a rotina desativada.</p> : null}
    {!candidate ? <form onSubmit={(event) => void startSelection(event)} autoComplete="off">
      <label>Senha atual do proprietário<input type="password" autoComplete="off" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      <label>Código atual do autenticador<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={totp} onChange={(event) => setTotp(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
      <MarkinaButton disabled={busy || !password || !/^[0-9]{6}$/.test(totp)}>{busy ? "Abrindo seletor…" : "Selecionar pasta global"}</MarkinaButton>
    </form> : <form onSubmit={(event) => void authorizeSelection(event)} autoComplete="off">
      <p>Pasta selecionada: <strong>{candidate.name}</strong>. Confirme com a senha e um novo código do autenticador para autorizar somente essa pasta.</p>
      <label>Senha atual do proprietário<input type="password" autoComplete="off" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      <label>Novo código do autenticador<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={totp} onChange={(event) => setTotp(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
      <MarkinaButton disabled={busy || !password || !/^[0-9]{6}$/.test(totp)}>{busy ? "Validando pasta…" : "Autorizar esta pasta"}</MarkinaButton>
    </form>}
    {error ? <p role="alert">{error}</p> : null}
  </section>;
}
