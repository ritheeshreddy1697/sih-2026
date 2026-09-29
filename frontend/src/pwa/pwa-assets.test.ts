// @vitest-environment node

import { readFile } from "node:fs/promises";

describe("PWA application shell", () => {
  it("provides an installable manifest with full-size icons", async () => {
    const manifest = JSON.parse(
      await readFile(new URL("../../public/manifest.webmanifest", import.meta.url), "utf8"),
    ) as { display: string; start_url: string; icons: Array<{ sizes: string }> };

    expect(manifest.display).toBe("standalone");
    expect(manifest.start_url).toBe("/");
    expect(manifest.icons.map((icon) => icon.sizes)).toEqual(["192x192", "512x512"]);
  });

  it("never places API or authorized responses in the service-worker cache", async () => {
    const worker = await readFile(new URL("../../public/sw.js", import.meta.url), "utf8");

    expect(worker).toContain('url.pathname.startsWith("/api/")');
    expect(worker).toContain('request.headers.has("Authorization")');
    expect(worker).toContain("if (isPrivateRequest(request, url)) return");
  });
});
