import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  Reflect.deleteProperty(window, "gapi");
  Reflect.deleteProperty(window, "google");
  document.getElementById("google-drive-picker-api")?.remove();
});

const syntheticPickerKey = `AIza${"x".repeat(35)}`;

const pickerSession = {
  access_token: "synthetic-short-token",
  scope: "https://www.googleapis.com/auth/drive.file",
  expires_in: 900,
  developer_key: syntheticPickerKey,
  project_number: "123456789012",
  expected_parent_folder_id: "synthetic-parent",
};

async function loadPickerComponent() {
  vi.resetModules();
  return (await import("./google-drive-folder-picker")).GoogleDriveBackupFolderPicker;
}

function installPickerMock() {
  let callback: ((data: Record<string, unknown>) => void) | undefined;
  const dialog = { setVisible: vi.fn() };
  const calls = { developerKeys: [] as string[], projectNumbers: [] as string[], accessTokens: [] as string[] };
  class DocsView {
    setMimeTypes = vi.fn(() => this);
    setIncludeFolders = vi.fn(() => this);
    setSelectFolderEnabled = vi.fn(() => this);
    setParent = vi.fn(() => this);
    setMode = vi.fn(() => this);
  }
  class PickerBuilder {
    addView = vi.fn(() => this);
    setOAuthToken = vi.fn((value: string) => { calls.accessTokens.push(value); return this; });
    setDeveloperKey = vi.fn((value: string) => { calls.developerKeys.push(value); return this; });
    setAppId = vi.fn((value: string) => { calls.projectNumbers.push(value); return this; });
    setCallback = vi.fn((value: (data: Record<string, unknown>) => void) => {
      callback = value;
      return this;
    });
    setTitle = vi.fn(() => this);
    setLocale = vi.fn(() => this);
    setMaxItems = vi.fn(() => this);
    setOrigin = vi.fn(() => this);
    build = vi.fn(() => dialog);
  }
  const api = {
    Action: { PICKED: "picked", CANCEL: "cancel", ERROR: "error" },
    Response: { ACTION: "action", DOCUMENTS: "docs" },
    Document: { ID: "id", NAME: "name", MIME_TYPE: "mimeType" },
    ViewId: { DOCS: "docs" },
    DocsViewMode: { LIST: "list" },
    DocsView,
    PickerBuilder,
  };
  Object.defineProperty(window, "gapi", {
    configurable: true, value: { load: vi.fn((_name: string, ready: () => void) => ready()) },
  });
  Object.defineProperty(window, "google", { configurable: true, value: { picker: api } });
  return {
    api, dialog, select: (data: Record<string, unknown>) => callback?.(data),
    calls,
  };
}

it("uses only drive.file, lets the owner select the global folder, and requires a second step-up", async () => {
  const GoogleDriveBackupFolderPicker = await loadPickerComponent();
  const picker = installPickerMock();
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(pickerSession), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({
      state: "selected", folder_name: "Pick-your-Pic Global", folder_id: "synthetic-folder-id",
    }), { status: 200 }));
  vi.stubGlobal("fetch", fetcher);
  render(<GoogleDriveBackupFolderPicker />);

  fireEvent.change(screen.getByLabelText("Senha atual do proprietário"), {
    target: { value: "synthetic-password" },
  });
  fireEvent.change(screen.getByLabelText("Código atual do autenticador"), {
    target: { value: "123456" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Selecionar pasta global" }));

  await waitFor(() => {
    expect(document.getElementById("google-drive-picker-api") ||
      picker.dialog.setVisible.mock.calls.length).toBeTruthy();
  });
  const script = document.getElementById("google-drive-picker-api");
  if (script && picker.dialog.setVisible.mock.calls.length === 0) fireEvent.load(script);
  await waitFor(() => expect(picker.dialog.setVisible).toHaveBeenCalledWith(true));
  expect(fetcher).toHaveBeenNthCalledWith(1, "/api/admin/platform/drive/picker/session",
    expect.objectContaining({
      method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error",
      body: JSON.stringify({ current_password: "synthetic-password", totp_code: "123456" }),
    }));
  expect(picker.calls.developerKeys).toEqual([pickerSession.developer_key]);
  expect(picker.calls.projectNumbers).toEqual([pickerSession.project_number]);
  expect(picker.calls.accessTokens).toEqual([pickerSession.access_token]);
  expect(document.body.textContent).not.toContain("synthetic-short-token");

  act(() => picker.select({ action: "loaded" }));
  expect(picker.dialog.setVisible.mock.calls).toEqual([[true]]);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(/Confirme com a senha e um novo código/)).toBeNull();

  act(() => picker.select?.({
    action: "picked",
    docs: [{ id: "synthetic-folder-id", name: "Pick-your-Pic Global",
      mimeType: "application/vnd.google-apps.folder" }],
  }));
  expect(await screen.findByText(/Confirme com a senha e um novo código/)).toBeTruthy();
  expect(picker.dialog.setVisible.mock.calls).toEqual([[true], [false]]);
  fireEvent.change(screen.getByLabelText("Senha atual do proprietário"), {
    target: { value: "synthetic-password" },
  });
  fireEvent.change(screen.getByLabelText("Novo código do autenticador"), {
    target: { value: "654321" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Autorizar esta pasta" }));

  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(fetcher).toHaveBeenNthCalledWith(2, "/api/admin/platform/drive/picker/authorize",
    expect.objectContaining({
      method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error",
      body: JSON.stringify({
        folder_id: "synthetic-folder-id", current_password: "synthetic-password", totp_code: "654321",
      }),
    }));
  expect((await screen.findByRole("status")).textContent).toContain(
    "Pasta autorizada: Pick-your-Pic Global. O vínculo protegido e o ensaio sintético ainda precisam ser concluídos com a rotina desativada.",
  );
});

it("shows a sanitized error when Google Picker fails after selection", async () => {
  const GoogleDriveBackupFolderPicker = await loadPickerComponent();
  const picker = installPickerMock();
  const fetcher = vi.fn().mockResolvedValueOnce(
    new Response(JSON.stringify(pickerSession), { status: 200 }),
  );
  vi.stubGlobal("fetch", fetcher);
  render(<GoogleDriveBackupFolderPicker />);

  fireEvent.change(screen.getByLabelText("Senha atual do proprietário"), {
    target: { value: "synthetic-password" },
  });
  fireEvent.change(screen.getByLabelText("Código atual do autenticador"), {
    target: { value: "123456" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Selecionar pasta global" }));

  await waitFor(() => {
    expect(document.getElementById("google-drive-picker-api") ||
      picker.dialog.setVisible.mock.calls.length).toBeTruthy();
  });
  const script = document.getElementById("google-drive-picker-api");
  if (script && picker.dialog.setVisible.mock.calls.length === 0) fireEvent.load(script);
  await waitFor(() => expect(picker.dialog.setVisible).toHaveBeenCalledWith(true));

  act(() => picker.select({
    action: "error", error: "synthetic-private-provider-detail",
    docs: [{ id: "synthetic-folder-id", name: "Pick-your-Pic Global" }],
  }));

  expect((await screen.findByRole("alert")).textContent).toContain(
    "O Google Drive não conseguiu concluir a seleção.",
  );
  expect(picker.dialog.setVisible.mock.calls).toEqual([[true], [false]]);
  expect(screen.queryByText(/Pasta selecionada:/)).toBeNull();
  expect(screen.queryByRole("button", { name: "Autorizar esta pasta" })).toBeNull();
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(document.body.textContent).not.toContain("synthetic-private-provider-detail");
  expect(document.body.textContent).not.toContain("synthetic-folder-id");
});

it("refuses a picker session that expands the OAuth scope", async () => {
  const GoogleDriveBackupFolderPicker = await loadPickerComponent();
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({
    ...pickerSession, scope: "https://www.googleapis.com/auth/drive",
  }), { status: 200 }));
  vi.stubGlobal("fetch", fetcher);
  render(<GoogleDriveBackupFolderPicker />);
  fireEvent.change(screen.getByLabelText("Senha atual do proprietário"), {
    target: { value: "synthetic-password" },
  });
  fireEvent.change(screen.getByLabelText("Código atual do autenticador"), {
    target: { value: "123456" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Selecionar pasta global" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/Não foi possível abrir o seletor/);
  expect(document.getElementById("google-drive-picker-api")).toBeNull();
});
