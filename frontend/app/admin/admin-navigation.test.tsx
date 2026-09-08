import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => <a href={href} {...props}>{children}</a> }));
vi.mock("next/navigation", () => ({ usePathname: () => "/admin/galleries/sources/example/edit/imagens" }));

import { AdminNavigation } from "./admin-navigation";

describe("navegação administrativa", () => {
  it("indica a seção atual sem esconder as rotas operacionais", () => {
    render(<AdminNavigation />);
    expect(screen.getByRole("link", { name: "Galerias" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "Operação" })).toBeTruthy();
  });
});
