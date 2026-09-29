import {
  ArrowUpRight,
  Bot,
  CircleHelp,
  Headphones,
  History,
  MessageSquareText,
  Plus,
  Send,
  ThumbsDown,
  ThumbsUp,
  UserRound,
} from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/auth-context-value";
import { AppShell } from "../components/layout/app-shell";
import { EmptyState } from "../components/states/empty-state";
import { ErrorState } from "../components/states/error-state";
import { LoadingState } from "../components/states/loading-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  ApiError,
  apiClient,
  type CareerConversation,
  type CareerConversationSummary,
  type CareerFeedbackRating,
  type CareerLanguage,
} from "../lib/api/client";
import { cn } from "../lib/utils";

const languageLabels: Record<CareerLanguage, string> = {
  en: "English",
  hi: "हिन्दी",
  te: "తెలుగు",
};

const translations = {
  en: {
    title: "Career counsellor",
    trust: "Answers use approved FAQs and current platform records.",
    history: "Conversation history",
    newChat: "New conversation",
    noHistory: "No conversations yet",
    noHistoryDescription: "Start a conversation in your preferred language.",
    welcome: "What would you like to discuss?",
    unavailable: "No conversation selected.",
    placeholder: "Ask about training, jobs, resumes or interviews",
    send: "Send message",
    sending: "Preparing an answer",
    sources: "Platform references",
    helpful: "Helpful",
    notHelpful: "Not helpful",
    support: "Human support",
    supportReason: "What would you like help with?",
    requestSupport: "Send to support",
    cancel: "Cancel",
    escalated: "Sent to human support",
    start: "Start in English",
    language: "Conversation language",
  },
  hi: {
    title: "करियर परामर्शदाता",
    trust: "उत्तर स्वीकृत FAQ और मौजूदा प्लेटफ़ॉर्म रिकॉर्ड पर आधारित हैं।",
    history: "बातचीत का इतिहास",
    newChat: "नई बातचीत",
    noHistory: "अभी कोई बातचीत नहीं है",
    noHistoryDescription: "अपनी पसंदीदा भाषा में बातचीत शुरू करें।",
    welcome: "आप किस विषय पर बात करना चाहते हैं?",
    unavailable: "कोई बातचीत नहीं चुनी गई है।",
    placeholder: "प्रशिक्षण, नौकरी, रिज़्यूमे या साक्षात्कार के बारे में पूछें",
    send: "संदेश भेजें",
    sending: "उत्तर तैयार हो रहा है",
    sources: "प्लेटफ़ॉर्म संदर्भ",
    helpful: "उपयोगी",
    notHelpful: "उपयोगी नहीं",
    support: "मानव सहायता",
    supportReason: "आपको किस विषय में सहायता चाहिए?",
    requestSupport: "सहायता टीम को भेजें",
    cancel: "रद्द करें",
    escalated: "मानव सहायता टीम को भेजा गया",
    start: "हिन्दी में शुरू करें",
    language: "बातचीत की भाषा",
  },
  te: {
    title: "కెరీర్ కౌన్సెలర్",
    trust: "సమాధానాలు ఆమోదించిన FAQలు మరియు ప్రస్తుత ప్లాట్‌ఫారమ్ రికార్డులపై ఆధారపడతాయి.",
    history: "సంభాషణ చరిత్ర",
    newChat: "కొత్త సంభాషణ",
    noHistory: "ఇంకా సంభాషణలు లేవు",
    noHistoryDescription: "మీకు నచ్చిన భాషలో సంభాషణను ప్రారంభించండి.",
    welcome: "మీరు దేని గురించి మాట్లాడాలనుకుంటున్నారు?",
    unavailable: "ఏ సంభాషణను ఎంచుకోలేదు.",
    placeholder: "శిక్షణ, ఉద్యోగాలు, రెజ్యూమే లేదా ఇంటర్వ్యూ గురించి అడగండి",
    send: "సందేశం పంపండి",
    sending: "సమాధానం సిద్ధమవుతోంది",
    sources: "ప్లాట్‌ఫారమ్ ఆధారాలు",
    helpful: "ఉపయోగకరం",
    notHelpful: "ఉపయోగకరం కాదు",
    support: "మానవ సహాయం",
    supportReason: "మీకు ఏ విషయంలో సహాయం కావాలి?",
    requestSupport: "సహాయక బృందానికి పంపండి",
    cancel: "రద్దు చేయండి",
    escalated: "మానవ సహాయక బృందానికి పంపబడింది",
    start: "తెలుగులో ప్రారంభించండి",
    language: "సంభాషణ భాష",
  },
} as const;

const suggestions: Record<CareerLanguage, string[]> = {
  en: [
    "Which training programmes suit me?",
    "Show jobs matching my verified skills",
    "Help me prepare my resume",
    "How should I prepare for an interview?",
  ],
  hi: [
    "मेरे लिए कौन से प्रशिक्षण कार्यक्रम उपयुक्त हैं?",
    "मेरे सत्यापित कौशल से मेल खाने वाली नौकरियाँ दिखाएँ",
    "रिज़्यूमे तैयार करने में मदद करें",
    "साक्षात्कार की तैयारी कैसे करूँ?",
  ],
  te: [
    "నాకు సరిపోయే శిక్షణ కార్యక్రమాలు ఏవి?",
    "నా ధృవీకరించిన నైపుణ్యాలకు సరిపోయే ఉద్యోగాలు చూపించండి",
    "నా రెజ్యూమే సిద్ధం చేయడంలో సహాయం చేయండి",
    "ఇంటర్వ్యూకు ఎలా సిద్ధం కావాలి?",
  ],
};

function formatTime(value: string, language: CareerLanguage) {
  return new Intl.DateTimeFormat(language === "en" ? "en-IN" : language, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getError(caught: unknown) {
  return caught instanceof ApiError ? caught.message : "Career counselling is unavailable.";
}

export function CareerCounsellorPage() {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState<CareerConversationSummary[] | null>(null);
  const [conversation, setConversation] = useState<CareerConversation | null>(null);
  const [language, setLanguage] = useState<CareerLanguage>("en");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);
  const [supportReason, setSupportReason] = useState("");
  const [isEscalating, setIsEscalating] = useState(false);
  const messageEndRef = useRef<HTMLDivElement>(null);
  const copy = translations[conversation?.language ?? language];

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const items = await apiClient.careerConversations();
        if (!active) return;
        setConversations(items);
        if (items[0]) {
          const detail = await apiClient.careerConversation(items[0].id);
          if (!active) return;
          setConversation(detail);
          setLanguage(detail.language);
        }
      } catch (caught) {
        if (active) setError(getError(caught));
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [conversation?.messages.length, isSending]);

  if (!user) return null;

  const openConversation = async (item: CareerConversationSummary) => {
    setError(null);
    try {
      const detail = await apiClient.careerConversation(item.id);
      setConversation(detail);
      setLanguage(detail.language);
      setSupportOpen(false);
    } catch (caught) {
      setError(getError(caught));
    }
  };

  const startConversation = async (selectedLanguage = language) => {
    setError(null);
    try {
      const created = await apiClient.createCareerConversation(selectedLanguage);
      setConversation(created);
      setLanguage(selectedLanguage);
      setConversations((current) => [created, ...(current ?? [])]);
      setMessage("");
      setSupportOpen(false);
    } catch (caught) {
      setError(getError(caught));
    }
  };

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    const content = message.trim();
    if (!conversation || content.length < 2 || isSending) return;
    setError(null);
    setIsSending(true);
    try {
      const exchange = await apiClient.sendCareerMessage(conversation.id, content);
      setConversation((current) =>
        current
          ? {
              ...current,
              title: current.messages.length ? current.title : content,
              last_message_at: exchange.assistant_message.created_at,
              messages: [
                ...current.messages,
                exchange.user_message,
                exchange.assistant_message,
              ],
            }
          : current,
      );
      setConversations((current) =>
        (current ?? []).map((item) =>
          item.id === conversation.id
            ? {
                ...item,
                title: item.title === "New conversation" ? content : item.title,
                last_message_at: exchange.assistant_message.created_at,
              }
            : item,
        ),
      );
      setMessage("");
    } catch (caught) {
      setError(getError(caught));
    } finally {
      setIsSending(false);
    }
  };

  const recordFeedback = async (messageId: string, rating: CareerFeedbackRating) => {
    if (!conversation) return;
    try {
      const feedback = await apiClient.saveCareerFeedback(conversation.id, messageId, rating);
      setConversation((current) =>
        current
          ? {
              ...current,
              messages: current.messages.map((item) =>
                item.id === messageId ? { ...item, feedback } : item,
              ),
            }
          : current,
      );
    } catch (caught) {
      setError(getError(caught));
    }
  };

  const escalate = async (event: FormEvent) => {
    event.preventDefault();
    if (!conversation || supportReason.trim().length < 5) return;
    setIsEscalating(true);
    try {
      const escalation = await apiClient.escalateCareerConversation(
        conversation.id,
        supportReason.trim(),
      );
      setConversation({ ...conversation, status: "escalated", escalation });
      setSupportReason("");
      setSupportOpen(false);
    } catch (caught) {
      setError(getError(caught));
    } finally {
      setIsEscalating(false);
    }
  };

  return (
    <AppShell user={user} onLogout={logout}>
      <div className="space-y-5">
        <header className="flex flex-col gap-4 border-b pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold text-primary">NCCT guidance</p>
            <h1 className="mt-1 text-2xl font-semibold sm:text-3xl">{copy.title}</h1>
            <p className="mt-2 flex max-w-2xl items-center gap-2 text-sm text-muted-foreground">
              <CircleHelp className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              {copy.trust}
            </p>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground">{copy.language}</p>
            <div className="inline-flex rounded-md border bg-card p-1" role="group" aria-label={copy.language}>
              {(Object.keys(languageLabels) as CareerLanguage[]).map((code) => (
                <button
                  key={code}
                  type="button"
                  className={cn(
                    "min-h-11 rounded px-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                    language === code ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                  )}
                  onClick={() => {
                    if (conversation?.language === code) setLanguage(code);
                    else void startConversation(code);
                  }}
                >
                  {languageLabels[code]}
                </button>
              ))}
            </div>
          </div>
        </header>

        {error && conversations !== null ? (
          <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
            {error}
          </p>
        ) : null}

        {conversations === null && !error ? (
          <div className="mx-auto max-w-lg py-16">
            <LoadingState label="Loading conversation history" />
          </div>
        ) : null}

        {conversations !== null ? (
          <div className="grid min-h-[620px] overflow-hidden rounded-lg border bg-card lg:grid-cols-[280px_minmax(0,1fr)]">
            <aside className="border-b bg-muted/35 p-4 lg:border-b-0 lg:border-r" aria-label={copy.history}>
              <div className="flex items-center justify-between gap-3">
                <h2 className="flex items-center gap-2 text-sm font-semibold">
                  <History className="h-4 w-4 text-primary" aria-hidden="true" />
                  {copy.history}
                </h2>
                <Button
                  variant="outline"
                  size="icon"
                  aria-label={copy.newChat}
                  title={copy.newChat}
                  onClick={() => void startConversation()}
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
              {conversations.length ? (
                <div className="mt-4 flex gap-2 overflow-x-auto pb-1 lg:block lg:space-y-2 lg:overflow-visible">
                  {conversations.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={cn(
                        "min-h-16 min-w-56 rounded-md border p-3 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary lg:w-full lg:min-w-0",
                        conversation?.id === item.id
                          ? "border-primary bg-card"
                          : "border-transparent hover:bg-card",
                      )}
                      onClick={() => void openConversation(item)}
                    >
                      <span className="block truncate font-medium">{item.title}</span>
                      <span className="mt-1 block text-xs text-muted-foreground">
                        {languageLabels[item.language]} · {formatTime(item.last_message_at, item.language)}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="mt-4">
                  <EmptyState
                    icon={MessageSquareText}
                    title={copy.noHistory}
                    description={copy.noHistoryDescription}
                  />
                </div>
              )}
            </aside>

            <section className="flex min-h-[620px] min-w-0 flex-col" aria-label={copy.title}>
              {!conversation ? (
                <div className="flex flex-1 items-center justify-center p-6">
                  <div className="max-w-md text-center">
                    <Bot className="mx-auto h-8 w-8 text-primary" aria-hidden="true" />
                    <h2 className="mt-4 text-lg font-semibold">{copy.unavailable}</h2>
                    <Button className="mt-5" onClick={() => void startConversation()}>
                      <Plus className="h-4 w-4" aria-hidden="true" />
                      {copy.start}
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-3 border-b px-4 py-3 sm:px-6">
                    <div className="min-w-0">
                      <h2 className="truncate text-sm font-semibold">{conversation.title}</h2>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {languageLabels[conversation.language]}
                      </p>
                    </div>
                    {conversation.escalation?.status === "open" ? (
                      <Badge className="bg-amber-100 text-amber-900">{copy.escalated}</Badge>
                    ) : (
                      <Button variant="outline" size="sm" onClick={() => setSupportOpen(true)}>
                        <Headphones className="h-4 w-4" aria-hidden="true" />
                        <span className="hidden sm:inline">{copy.support}</span>
                      </Button>
                    )}
                  </div>

                  <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6" aria-live="polite">
                    {!conversation.messages.length ? (
                      <div className="py-8 text-center">
                        <Bot className="mx-auto h-8 w-8 text-primary" aria-hidden="true" />
                        <h2 className="mt-4 text-lg font-semibold">{copy.welcome}</h2>
                        <div className="mx-auto mt-5 grid max-w-2xl gap-2 sm:grid-cols-2">
                          {suggestions[conversation.language].map((suggestion) => (
                            <button
                              key={suggestion}
                              type="button"
                              className="min-h-12 rounded-md border px-4 py-3 text-left text-sm hover:border-primary hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                              onClick={() => setMessage(suggestion)}
                            >
                              {suggestion}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {conversation.messages.map((item) => (
                      <article
                        key={item.id}
                        className={cn(
                          "flex gap-3",
                          item.role === "user" ? "ml-auto max-w-2xl flex-row-reverse" : "max-w-3xl",
                        )}
                      >
                        <span
                          className={cn(
                            "flex h-9 w-9 shrink-0 items-center justify-center rounded-md",
                            item.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-primary",
                          )}
                        >
                          {item.role === "user" ? (
                            <UserRound className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <Bot className="h-4 w-4" aria-hidden="true" />
                          )}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div
                            className={cn(
                              "rounded-lg px-4 py-3 text-sm leading-6 whitespace-pre-wrap",
                              item.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted/70",
                            )}
                          >
                            {item.content}
                          </div>
                          {item.sources.length ? (
                            <div className="mt-3 space-y-2">
                              <p className="text-xs font-semibold text-muted-foreground">{copy.sources}</p>
                              {item.sources.map((source) => (
                                <Link
                                  key={`${source.source_type}-${source.record_id}`}
                                  to={source.url}
                                  className="flex min-h-11 items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                                >
                                  <span className="min-w-0">
                                    <span className="block text-xs uppercase text-muted-foreground">
                                      {source.source_type}
                                    </span>
                                    <span className="block truncate font-medium">{source.title}</span>
                                  </span>
                                  <ArrowUpRight className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                                </Link>
                              ))}
                            </div>
                          ) : null}
                          {item.role === "assistant" ? (
                            <div className="mt-2 flex gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                className={cn(item.feedback?.rating === "helpful" && "bg-emerald-50 text-emerald-800")}
                                aria-label={copy.helpful}
                                title={copy.helpful}
                                onClick={() => void recordFeedback(item.id, "helpful")}
                              >
                                <ThumbsUp className="h-4 w-4" aria-hidden="true" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className={cn(item.feedback?.rating === "not_helpful" && "bg-red-50 text-red-800")}
                                aria-label={copy.notHelpful}
                                title={copy.notHelpful}
                                onClick={() => void recordFeedback(item.id, "not_helpful")}
                              >
                                <ThumbsDown className="h-4 w-4" aria-hidden="true" />
                              </Button>
                            </div>
                          ) : null}
                        </div>
                      </article>
                    ))}
                    {isSending ? (
                      <div className="flex items-center gap-3 text-sm text-muted-foreground" role="status">
                        <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                        {copy.sending}
                      </div>
                    ) : null}
                    <div ref={messageEndRef} />
                  </div>

                  {supportOpen ? (
                    <form className="border-t bg-amber-50 p-4" onSubmit={(event) => void escalate(event)}>
                      <label className="text-sm font-medium" htmlFor="support-reason">
                        {copy.supportReason}
                      </label>
                      <textarea
                        id="support-reason"
                        className="mt-2 min-h-20 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        minLength={5}
                        maxLength={2000}
                        required
                        value={supportReason}
                        onChange={(event) => setSupportReason(event.target.value)}
                      />
                      <div className="mt-3 flex gap-2">
                        <Button type="submit" size="sm" disabled={isEscalating}>
                          <Headphones className="h-4 w-4" aria-hidden="true" />
                          {copy.requestSupport}
                        </Button>
                        <Button type="button" size="sm" variant="ghost" onClick={() => setSupportOpen(false)}>
                          {copy.cancel}
                        </Button>
                      </div>
                    </form>
                  ) : null}

                  <form className="border-t p-4 sm:p-5" onSubmit={(event) => void sendMessage(event)}>
                    <div className="flex items-end gap-2">
                      <div className="min-w-0 flex-1">
                        <label className="sr-only" htmlFor="career-message">
                          {copy.placeholder}
                        </label>
                        <textarea
                          id="career-message"
                          className="min-h-12 max-h-36 w-full resize-y rounded-md border bg-background px-3 py-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                          minLength={2}
                          maxLength={2000}
                          placeholder={copy.placeholder}
                          value={message}
                          onChange={(event) => setMessage(event.target.value)}
                        />
                        <p className="mt-1 text-right text-xs text-muted-foreground">{message.length}/2000</p>
                      </div>
                      <Button
                        type="submit"
                        size="icon"
                        disabled={message.trim().length < 2 || isSending}
                        aria-label={copy.send}
                        title={copy.send}
                      >
                        <Send className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </form>
                </>
              )}
            </section>
          </div>
        ) : null}

        {conversations === null && error ? (
          <ErrorState
            title="Career counsellor unavailable"
            description={error}
            onRetry={() => window.location.reload()}
          />
        ) : null}
      </div>
    </AppShell>
  );
}
