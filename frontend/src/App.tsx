import { useTranslation } from "react-i18next";

// Phase 0 placeholder home page. Real pages (consent, assessment, results,
// Family Decision Room) arrive in Phases 6-7.
export default function App() {
  const { t, i18n } = useTranslation();

  const toggleLang = () => {
    void i18n.changeLanguage(i18n.language === "en" ? "hi" : "en");
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-3xl font-bold text-brand">{t("app.title")}</h1>
      <p className="text-lg text-gray-700">{t("app.tagline")}</p>
      <p className="text-sm text-gray-500">{t("home.placeholder")}</p>
      <div className="flex gap-3">
        <button
          type="button"
          className="rounded bg-brand px-5 py-3 font-medium text-white"
        >
          {t("home.startCta")}
        </button>
        <button
          type="button"
          onClick={toggleLang}
          className="rounded border border-brand px-5 py-3 font-medium text-brand"
        >
          {t("lang.switchTo")}
        </button>
      </div>
    </main>
  );
}
