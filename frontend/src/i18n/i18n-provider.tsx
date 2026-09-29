import { createContext, useContext, useEffect, useMemo, useState } from "react";

export const supportedLanguages = [
  { code: "en", name: "English", nativeName: "English", direction: "ltr" },
  { code: "hi", name: "Hindi", nativeName: "हिन्दी", direction: "ltr" },
  { code: "te", name: "Telugu", nativeName: "తెలుగు", direction: "ltr" },
] as const;

export type LanguageCode = (typeof supportedLanguages)[number]["code"];

const english = {
  "brand.name": "NCCT Training",
  "brand.network": "Cooperative network",
  "common.language": "Language",
  "common.skipWorkspace": "Skip to workspace content",
  "common.signedInAs": "Signed in as",
  "common.closeNavigation": "Close navigation",
  "common.openNavigation": "Open navigation",
  "common.notifications": "Notifications",
  "common.unread": "unread",
  "common.noNotifications": "No new notifications.",
  "common.openProfile": "Open profile menu",
  "common.profile": "My profile",
  "common.settings": "Account settings",
  "common.signOut": "Sign out",
  "nav.dashboard": "Dashboard",
  "nav.profile": "My profile",
  "nav.institutions": "Institutions",
  "nav.trainees": "People",
  "nav.notifications": "Send notification",
  "nav.programmes": "Programmes",
  "nav.learning": "Learning",
  "nav.attendance": "Attendance",
  "nav.operations": "Operations",
  "nav.certificates": "Certificates",
  "nav.applications": "Applications",
  "nav.nominations": "Nominations",
  "nav.employment": "Employment",
  "nav.career": "Career counsellor",
  "nav.analytics": "Analytics",
  "pwa.online": "Online",
  "pwa.offline": "Offline",
  "pwa.offlineHint": "You can continue downloaded lessons. Changes will sync later.",
  "pwa.queued": "{count} changes waiting",
  "pwa.sync": "Sync now",
  "pwa.syncing": "Syncing",
  "pwa.install": "Install app",
  "pwa.reducedData": "Reduced-data mode",
  "pwa.reducedDataHint": "Media loads only when you choose it.",
  "pwa.updateReady": "An app update is ready.",
  "pwa.update": "Update",
  "learning.download": "Download for offline",
  "learning.downloaded": "Available offline",
  "learning.downloading": "Downloading",
  "learning.loadMedia": "Load media",
  "learning.remove": "Remove download",
  "learning.offlineCopy": "Showing your downloaded copy.",
  "learning.offlineUnavailable": "This lesson is not downloaded on this device.",
  "learning.progressQueued": "Progress saved on this device and will sync when online.",
  "auth.email": "Email address",
  "auth.password": "Password",
  "auth.signIn": "Sign in",
  "auth.signingIn": "Signing in...",
  "auth.showPassword": "Show password",
  "auth.hidePassword": "Hide password",
} as const;

export type TranslationKey = keyof typeof english;

const translations: Record<LanguageCode, Record<TranslationKey, string>> = {
  en: english,
  hi: {
    ...english,
    "brand.name": "एनसीसीटी प्रशिक्षण",
    "brand.network": "सहकारी नेटवर्क",
    "common.language": "भाषा",
    "common.skipWorkspace": "कार्यस्थान की सामग्री पर जाएं",
    "common.signedInAs": "भूमिका",
    "common.closeNavigation": "नेविगेशन बंद करें",
    "common.openNavigation": "नेविगेशन खोलें",
    "common.notifications": "सूचनाएं",
    "common.unread": "अपठित",
    "common.noNotifications": "कोई नई सूचना नहीं।",
    "common.openProfile": "प्रोफ़ाइल मेनू खोलें",
    "common.profile": "मेरी प्रोफ़ाइल",
    "common.settings": "खाता सेटिंग",
    "common.signOut": "साइन आउट",
    "nav.dashboard": "डैशबोर्ड",
    "nav.profile": "मेरी प्रोफ़ाइल",
    "nav.institutions": "संस्थान",
    "nav.trainees": "लोग",
    "nav.notifications": "सूचना भेजें",
    "nav.programmes": "कार्यक्रम",
    "nav.learning": "अध्ययन",
    "nav.attendance": "उपस्थिति",
    "nav.operations": "संचालन",
    "nav.certificates": "प्रमाणपत्र",
    "nav.applications": "आवेदन",
    "nav.nominations": "नामांकन",
    "nav.employment": "रोज़गार",
    "nav.career": "करियर परामर्श",
    "nav.analytics": "विश्लेषण",
    "pwa.online": "ऑनलाइन",
    "pwa.offline": "ऑफ़लाइन",
    "pwa.offlineHint": "डाउनलोड किए पाठ जारी रखें। बदलाव बाद में सिंक होंगे।",
    "pwa.queued": "{count} बदलाव प्रतीक्षारत",
    "pwa.sync": "अभी सिंक करें",
    "pwa.syncing": "सिंक हो रहा है",
    "pwa.install": "ऐप इंस्टॉल करें",
    "pwa.reducedData": "कम डेटा मोड",
    "pwa.reducedDataHint": "मीडिया केवल आपके चुनने पर लोड होगा।",
    "pwa.updateReady": "ऐप अपडेट तैयार है।",
    "pwa.update": "अपडेट करें",
    "learning.download": "ऑफ़लाइन डाउनलोड करें",
    "learning.downloaded": "ऑफ़लाइन उपलब्ध",
    "learning.downloading": "डाउनलोड हो रहा है",
    "learning.loadMedia": "मीडिया लोड करें",
    "learning.remove": "डाउनलोड हटाएं",
    "learning.offlineCopy": "डाउनलोड की गई प्रति दिखाई जा रही है।",
    "learning.offlineUnavailable": "यह पाठ इस डिवाइस पर डाउनलोड नहीं है।",
    "learning.progressQueued": "प्रगति इस डिवाइस पर सहेजी गई है और ऑनलाइन होने पर सिंक होगी।",
    "auth.email": "ईमेल पता",
    "auth.password": "पासवर्ड",
    "auth.signIn": "साइन इन करें",
    "auth.signingIn": "साइन इन हो रहा है...",
    "auth.showPassword": "पासवर्ड दिखाएं",
    "auth.hidePassword": "पासवर्ड छिपाएं",
  },
  te: {
    ...english,
    "brand.name": "ఎన్‌సీసీటీ శిక్షణ",
    "brand.network": "సహకార నెట్‌వర్క్",
    "common.language": "భాష",
    "common.skipWorkspace": "కార్యస్థల విషయానికి వెళ్లండి",
    "common.signedInAs": "పాత్ర",
    "common.closeNavigation": "నావిగేషన్ మూసివేయండి",
    "common.openNavigation": "నావిగేషన్ తెరవండి",
    "common.notifications": "నోటిఫికేషన్లు",
    "common.unread": "చదవనివి",
    "common.noNotifications": "కొత్త నోటిఫికేషన్లు లేవు.",
    "common.openProfile": "ప్రొఫైల్ మెనూ తెరవండి",
    "common.profile": "నా ప్రొఫైల్",
    "common.settings": "ఖాతా సెట్టింగులు",
    "common.signOut": "సైన్ అవుట్",
    "nav.dashboard": "డ్యాష్‌బోర్డ్",
    "nav.profile": "నా ప్రొఫైల్",
    "nav.institutions": "సంస్థలు",
    "nav.trainees": "వ్యక్తులు",
    "nav.notifications": "నోటిఫికేషన్ పంపండి",
    "nav.programmes": "కార్యక్రమాలు",
    "nav.learning": "అభ్యాసం",
    "nav.attendance": "హాజరు",
    "nav.operations": "నిర్వహణ",
    "nav.certificates": "సర్టిఫికెట్లు",
    "nav.applications": "దరఖాస్తులు",
    "nav.nominations": "నామినేషన్లు",
    "nav.employment": "ఉపాధి",
    "nav.career": "కెరీర్ సలహా",
    "nav.analytics": "విశ్లేషణ",
    "pwa.online": "ఆన్‌లైన్",
    "pwa.offline": "ఆఫ్‌లైన్",
    "pwa.offlineHint": "డౌన్‌లోడ్ చేసిన పాఠాలను కొనసాగించండి. మార్పులు తర్వాత సింక్ అవుతాయి.",
    "pwa.queued": "{count} మార్పులు వేచి ఉన్నాయి",
    "pwa.sync": "ఇప్పుడే సింక్ చేయండి",
    "pwa.syncing": "సింక్ అవుతోంది",
    "pwa.install": "యాప్ ఇన్‌స్టాల్ చేయండి",
    "pwa.reducedData": "తక్కువ డేటా మోడ్",
    "pwa.reducedDataHint": "మీరు ఎంచుకున్నప్పుడు మాత్రమే మీడియా లోడ్ అవుతుంది.",
    "pwa.updateReady": "యాప్ నవీకరణ సిద్ధంగా ఉంది.",
    "pwa.update": "నవీకరించండి",
    "learning.download": "ఆఫ్‌లైన్ కోసం డౌన్‌లోడ్ చేయండి",
    "learning.downloaded": "ఆఫ్‌లైన్‌లో అందుబాటులో ఉంది",
    "learning.downloading": "డౌన్‌లోడ్ అవుతోంది",
    "learning.loadMedia": "మీడియా లోడ్ చేయండి",
    "learning.remove": "డౌన్‌లోడ్ తొలగించండి",
    "learning.offlineCopy": "డౌన్‌లోడ్ చేసిన కాపీ చూపబడుతోంది.",
    "learning.offlineUnavailable": "ఈ పాఠం ఈ పరికరంలో డౌన్‌లోడ్ కాలేదు.",
    "learning.progressQueued": "పురోగతి ఈ పరికరంలో సేవ్ అయింది. ఆన్‌లైన్‌లో సింక్ అవుతుంది.",
    "auth.email": "ఈమెయిల్ చిరునామా",
    "auth.password": "పాస్‌వర్డ్",
    "auth.signIn": "సైన్ ఇన్",
    "auth.signingIn": "సైన్ ఇన్ అవుతోంది...",
    "auth.showPassword": "పాస్‌వర్డ్ చూపించండి",
    "auth.hidePassword": "పాస్‌వర్డ్ దాచండి",
  },
};

type I18nContextValue = {
  language: LanguageCode;
  setLanguage: (language: LanguageCode) => void;
  t: (key: TranslationKey, values?: Record<string, string | number>) => string;
};

function initialLanguage(): LanguageCode {
  const saved = window.localStorage?.getItem("ncct-language") ?? null;
  if (supportedLanguages.some((item) => item.code === saved)) return saved as LanguageCode;
  const browserLanguage = navigator.language.split("-")[0];
  return supportedLanguages.some((item) => item.code === browserLanguage)
    ? (browserLanguage as LanguageCode)
    : "en";
}

const defaultValue: I18nContextValue = {
  language: "en",
  setLanguage: () => undefined,
  t: (key, values) => {
    let message: string = english[key];
    Object.entries(values ?? {}).forEach(([name, value]) => {
      message = message.split(`{${name}}`).join(String(value));
    });
    return message;
  },
};

const I18nContext = createContext<I18nContextValue>(defaultValue);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<LanguageCode>(initialLanguage);

  useEffect(() => {
    const option = supportedLanguages.find((item) => item.code === language)!;
    window.localStorage?.setItem("ncct-language", language);
    document.documentElement.lang = language;
    document.documentElement.dir = option.direction;
  }, [language]);

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      t: (key, values) => {
        let message = translations[language][key] ?? english[key];
        Object.entries(values ?? {}).forEach(([name, replacement]) => {
          message = message.split(`{${name}}`).join(String(replacement));
        });
        return message;
      },
    }),
    [language],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
