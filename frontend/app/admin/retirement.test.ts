import { existsSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";

it("a rota antiga de Estatísticas deixa de ser uma página do App Router", () => {
  expect(existsSync(join(process.cwd(), "app/admin/statistics/page.tsx"))).toBe(false);
});
