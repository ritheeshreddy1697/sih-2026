import { Languages } from "lucide-react";

import { supportedLanguages, useI18n } from "../../i18n/i18n-provider";
import { cn } from "../../lib/utils";

export function LanguageSelect({ compact = false }: { compact?: boolean }) {
  const { language, setLanguage, t } = useI18n();
  return (
    <label className={cn("flex min-h-11 items-center gap-2", compact ? "px-2" : "px-3")}>
      <Languages className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
      <span className={compact ? "sr-only" : "text-sm font-medium"}>{t("common.language")}</span>
      <select
        className="min-h-11 min-w-20 flex-1 rounded-md border bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
        aria-label={t("common.language")}
        value={language}
        onChange={(event) => setLanguage(event.target.value as typeof language)}
      >
        {supportedLanguages.map((option) => (
          <option key={option.code} value={option.code}>
            {option.nativeName}
          </option>
        ))}
      </select>
    </label>
  );
}
