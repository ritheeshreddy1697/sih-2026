import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Bot, RotateCcw, Send, Sparkles, UserRound, X } from "lucide-react";
import { useLocation } from "react-router-dom";

import { useI18n } from "../../i18n/i18n-provider";
import {
  ApiError,
  apiClient,
  type AssistantChatTurn,
  type CareerLanguage,
  type User,
} from "../../lib/api/client";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";

type DisplayMessage = AssistantChatTurn & {
  id: string;
  provider?: string;
};

const copy = {
  en: {
    title: "NCCT assistant",
    subtitle: "Ask about this page or your next step",
    open: "Open AI assistant",
    close: "Close AI assistant",
    clear: "Clear conversation",
    welcome: "Hello. I can help you find features and understand what to do on any NCCT page.",
    placeholder: "Ask about this page...",
    send: "Send message",
    thinking: "Thinking...",
    error: "The assistant could not respond. Please try again.",
    gemini: "Gemini",
    local: "Local guide",
  },
  hi: {
    title: "एनसीसीटी सहायक",
    subtitle: "इस पेज या अगले चरण के बारे में पूछें",
    open: "एआई सहायक खोलें",
    close: "एआई सहायक बंद करें",
    clear: "बातचीत साफ करें",
    welcome: "नमस्ते। मैं एनसीसीटी के किसी भी पेज पर सुविधाएं खोजने और अगला चरण समझने में आपकी मदद कर सकता हूं।",
    placeholder: "इस पेज के बारे में पूछें...",
    send: "संदेश भेजें",
    thinking: "सोच रहा हूं...",
    error: "सहायक उत्तर नहीं दे सका। कृपया फिर से प्रयास करें।",
    gemini: "Gemini",
    local: "स्थानीय गाइड",
  },
  te: {
    title: "ఎన్‌సీసీటీ సహాయకుడు",
    subtitle: "ఈ పేజీ లేదా తదుపరి దశ గురించి అడగండి",
    open: "ఏఐ సహాయకుడిని తెరవండి",
    close: "ఏఐ సహాయకుడిని మూసివేయండి",
    clear: "సంభాషణను తొలగించండి",
    welcome: "నమస్కారం. ఏ ఎన్‌సీసీటీ పేజీలోనైనా ఫీచర్లను కనుగొని, తదుపరి దశను అర్థం చేసుకోవడంలో సహాయపడగలను.",
    placeholder: "ఈ పేజీ గురించి అడగండి...",
    send: "సందేశం పంపండి",
    thinking: "ఆలోచిస్తోంది...",
    error: "సహాయకుడు స్పందించలేకపోయాడు. దయచేసి మళ్లీ ప్రయత్నించండి.",
    gemini: "Gemini",
    local: "స్థానిక గైడ్",
  },
} as const;

function loadMessages(storageKey: string): DisplayMessage[] {
  try {
    const saved = window.sessionStorage.getItem(storageKey);
    if (!saved) return [];
    const parsed = JSON.parse(saved) as DisplayMessage[];
    return Array.isArray(parsed) ? parsed.slice(-20) : [];
  } catch {
    return [];
  }
}

function messageId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

export function GlobalAssistant({ user }: { user: User }) {
  const { language } = useI18n();
  const location = useLocation();
  const storageKey = `ncct-assistant:${user.id}`;
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>(() => loadMessages(storageKey));
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const labels = copy[language];

  const conversationHistory = useMemo<AssistantChatTurn[]>(
    () => messages.slice(-8).map(({ role, content }) => ({ role, content })),
    [messages],
  );

  useEffect(() => {
    window.sessionStorage.setItem(storageKey, JSON.stringify(messages.slice(-20)));
  }, [messages, storageKey]);

  useEffect(() => {
    if (!isOpen) return;
    inputRef.current?.focus();
    if (typeof messageEndRef.current?.scrollIntoView === "function") {
      messageEndRef.current.scrollIntoView({ block: "end" });
    }
  }, [isOpen, messages, isSending]);

  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);

  const clearConversation = () => {
    setMessages([]);
    setError(null);
    window.sessionStorage.removeItem(storageKey);
  };

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    const content = message.trim();
    if (content.length < 2 || isSending) return;

    const userMessage: DisplayMessage = { id: messageId(), role: "user", content };
    setMessages((current) => [...current, userMessage]);
    setMessage("");
    setError(null);
    setIsSending(true);
    try {
      const response = await apiClient.platformAssistant({
        message: content,
        history: conversationHistory,
        page_path: `${location.pathname}${location.search}`.slice(0, 200),
        language: language as CareerLanguage,
      });
      setMessages((current) => [
        ...current,
        {
          id: messageId(),
          role: "assistant",
          content: response.answer,
          provider: response.provider,
        },
      ]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : labels.error);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <>
      {isOpen ? (
        <section
          className="fixed inset-x-3 bottom-20 z-50 flex max-h-[min(680px,calc(100vh-6rem))] flex-col overflow-hidden rounded-lg border bg-card shadow-2xl sm:left-auto sm:right-5 sm:w-[400px]"
          role="dialog"
          aria-label={labels.title}
        >
          <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Sparkles className="h-4 w-4" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h2 className="truncate text-sm font-semibold">{labels.title}</h2>
                <p className="truncate text-xs text-muted-foreground">{labels.subtitle}</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={labels.clear}
                title={labels.clear}
                onClick={clearConversation}
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={labels.close}
                title={labels.close}
                onClick={() => setIsOpen(false)}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </header>

          <div className="min-h-64 flex-1 space-y-4 overflow-y-auto bg-background p-4" aria-live="polite">
            {!messages.length ? (
              <div className="flex gap-3 text-sm leading-6">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-primary">
                  <Bot className="h-4 w-4" aria-hidden="true" />
                </span>
                <p className="rounded-lg bg-muted px-3 py-2.5">{labels.welcome}</p>
              </div>
            ) : null}

            {messages.map((item) => (
              <article
                key={item.id}
                className={cn(
                  "flex gap-2 text-sm",
                  item.role === "user" ? "ml-8 flex-row-reverse" : "mr-3",
                )}
              >
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-md",
                    item.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-primary",
                  )}
                >
                  {item.role === "user" ? (
                    <UserRound className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <Bot className="h-4 w-4" aria-hidden="true" />
                  )}
                </span>
                <div className="min-w-0">
                  <p
                    className={cn(
                      "whitespace-pre-wrap rounded-lg px-3 py-2.5 leading-6",
                      item.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted",
                    )}
                  >
                    {item.content}
                  </p>
                  {item.role === "assistant" && item.provider ? (
                    <p className="mt-1 px-1 text-[11px] text-muted-foreground">
                      {item.provider === "gemini" ? labels.gemini : labels.local}
                    </p>
                  ) : null}
                </div>
              </article>
            ))}

            {isSending ? (
              <p className="flex items-center gap-2 text-xs text-muted-foreground" role="status">
                <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                {labels.thinking}
              </p>
            ) : null}
            {error ? <p className="text-sm text-destructive" role="alert">{error}</p> : null}
            <div ref={messageEndRef} />
          </div>

          <form className="border-t p-3" onSubmit={(event) => void sendMessage(event)}>
            <div className="flex items-end gap-2">
              <label className="sr-only" htmlFor="global-assistant-message">
                {labels.placeholder}
              </label>
              <textarea
                ref={inputRef}
                id="global-assistant-message"
                className="max-h-28 min-h-11 flex-1 resize-y rounded-md border bg-background px-3 py-2.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                minLength={2}
                maxLength={2000}
                rows={1}
                placeholder={labels.placeholder}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
              />
              <Button
                type="submit"
                size="icon"
                disabled={message.trim().length < 2 || isSending}
                aria-label={labels.send}
                title={labels.send}
              >
                <Send className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </form>
        </section>
      ) : null}

      <Button
        type="button"
        size="icon"
        className="fixed bottom-5 right-5 z-50 h-12 w-12 shadow-lg"
        aria-label={isOpen ? labels.close : labels.open}
        title={isOpen ? labels.close : labels.open}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
      >
        {isOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Sparkles className="h-5 w-5" aria-hidden="true" />}
      </Button>
    </>
  );
}
