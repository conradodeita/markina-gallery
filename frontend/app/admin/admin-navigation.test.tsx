import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const { mockPathname } = vi.hoisted(() => ({ mockPathname: vi.fn() }));

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => <a href={href} {...props}>{children}</a> }));
vi.mock("next/navigation", () => ({ usePathname: () => mockPathname() }));

import { AdminNavigation } from "./admin-navigation";

describe("navegação administrativa", () => {
  it("indica Galerias como entrada operacional e omite a rota legada", () => {
    mockPathname.mockReturnValue("/admin/galleries/sources/example/edit/imagens");
    render(<AdminNavigation />);
    expect(screen.getByRole("link", { name: "Galerias" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Notificações" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Operação" })).toBeNull();
  });

  it("expõe o diretório global e indica a rota ativa", () => {
    mockPathname.mockReturnValue("/admin/clients");
    render(<AdminNavigation />);
    const clients = screen.getByRole("link", { name: "Clientes" });
    expect(clients.getAttribute("href")).toBe("/admin/clients");
    expect(clients.getAttribute("aria-current")).toBe("page");
  });
});
