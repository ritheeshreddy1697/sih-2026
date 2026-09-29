import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { LanguageSelect } from "../components/pwa/language-select";
import { I18nProvider, useI18n } from "./i18n-provider";

function TranslatedStatus() {
  const { t } = useI18n();
  return <p>{t("pwa.offline")}</p>;
}

describe("interface localization", () => {
  beforeEach(() => window.localStorage.clear());

  it("switches the document and interface between supported Indian languages", async () => {
    render(
      <I18nProvider>
        <LanguageSelect />
        <TranslatedStatus />
      </I18nProvider>,
    );

    fireEvent.change(screen.getByRole("combobox", { name: "Language" }), {
      target: { value: "te" },
    });

    expect(screen.getByText("ఆఫ్‌లైన్")).toBeInTheDocument();
    await waitFor(() => expect(document.documentElement.lang).toBe("te"));
    expect(window.localStorage.getItem("ncct-language")).toBe("te");
  });
});
