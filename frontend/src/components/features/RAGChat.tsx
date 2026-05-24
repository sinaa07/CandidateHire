"use client"

import { useState, useRef, useEffect, useCallback, memo } from "react"
import { Send, Bot, User, Sparkles, X, Minimize2, Maximize2 } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { queryRAG } from "@/utils/api"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

const SUGGESTIONS = [
  "Show top 5 frontend developers",
  "Find candidates with Python and ML experience",
  "Compare backend specialists",
  "Who has startup experience?",
]

function newMessageId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

/* Stable child components — must live outside RAGChat so typing does not remount the input */

const ChatInput = memo(function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
  compact,
}: {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled: boolean
  compact?: boolean
}) {
  return (
    <div className="border-t border-border bg-card p-4 shrink-0">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          onSend()
        }}
      >
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Type your question..."
          className={`flex-1 border border-border rounded-lg bg-input text-foreground focus:outline-none focus:ring-2 focus:ring-ring ${
            compact ? "px-3 py-2 text-sm" : "px-4 py-2"
          }`}
          disabled={disabled}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          className={`gradient-primary text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center ${
            compact ? "px-4 py-2" : "px-6 py-2"
          }`}
        >
          <Send size={compact ? 16 : 18} />
        </button>
      </form>
    </div>
  )
})

const EmptyState = memo(function EmptyState({
  compact,
  onSuggestion,
}: {
  compact?: boolean
  onSuggestion: (text: string) => void
}) {
  return (
    <div className={`text-center ${compact ? "py-8" : "py-12"}`}>
      <Sparkles className={`mx-auto text-primary mb-3 ${compact ? "w-8 h-8" : "w-12 h-12"}`} />
      <h3 className={`font-semibold text-foreground ${compact ? "text-sm" : "text-lg"}`}>AI Assistant</h3>
      <p className="text-muted-foreground text-sm mt-1 mb-4">Ask questions about your candidates</p>
      <div className={`grid gap-2 ${compact ? "grid-cols-1" : "grid-cols-2 max-w-2xl mx-auto"}`}>
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onSuggestion(suggestion)}
            className="text-left p-3 bg-muted hover:bg-muted/80 rounded-lg text-sm text-foreground transition-colors border border-border"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
})

const MessageBubble = memo(function MessageBubble({
  message,
  compact,
}: {
  message: Message
  compact?: boolean
}) {
  const isUser = message.role === "user"

  return (
    <div className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className={`rounded-full bg-primary flex items-center justify-center shrink-0 ${compact ? "w-6 h-6" : "w-8 h-8"}`}>
          <Bot size={compact ? 12 : 16} className="text-white" />
        </div>
      )}
      <div
        className={`rounded-lg shadow-card ${
          compact ? "max-w-[85%] p-3 text-xs" : "max-w-[70%] p-4 text-sm"
        } ${isUser ? "bg-primary text-white" : "bg-card text-foreground border border-border"}`}
      >
        <p className="whitespace-pre-wrap break-words">
          {message.content}
          {!isUser && message.content === "" && (
            <span className="inline-block w-0.5 h-4 bg-primary/60 animate-pulse align-middle ml-0.5" aria-hidden />
          )}
        </p>
        {!compact && (
          <p className="text-xs mt-2 opacity-70">
            {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
        )}
      </div>
      {isUser && (
        <div className={`rounded-full bg-muted flex items-center justify-center shrink-0 ${compact ? "w-6 h-6" : "w-8 h-8"}`}>
          <User size={compact ? 12 : 16} className="text-muted-foreground" />
        </div>
      )}
    </div>
  )
})

const TypingIndicator = memo(function TypingIndicator({ compact }: { compact?: boolean }) {
  return (
    <div className="flex gap-2 justify-start">
      <div className={`rounded-full bg-primary flex items-center justify-center ${compact ? "w-6 h-6" : "w-8 h-8"}`}>
        <Bot size={compact ? 12 : 16} className="text-white" />
      </div>
      <div className="bg-card border border-border shadow-card rounded-lg p-3">
        <div className="flex gap-1">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="w-2 h-2 bg-primary rounded-full animate-bounce"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
})

const MessageList = memo(function MessageList({
  messages,
  showTyping,
  compact,
  onSuggestion,
  messagesEndRef,
  scrollContainerRef,
}: {
  messages: Message[]
  showTyping: boolean
  compact?: boolean
  onSuggestion: (text: string) => void
  messagesEndRef: React.RefObject<HTMLDivElement | null>
  scrollContainerRef: React.RefObject<HTMLDivElement | null>
}) {
  return (
    <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
      {messages.length === 0 && <EmptyState compact={compact} onSuggestion={onSuggestion} />}
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} compact={compact} />
      ))}
      {showTyping && <TypingIndicator compact={compact} />}
      <div ref={messagesEndRef} />
    </div>
  )
})

const ChatHeader = memo(function ChatHeader({
  title,
  expanded,
  onExpand,
  onMinimize,
}: {
  title: string
  expanded?: boolean
  onExpand?: () => void
  onMinimize: () => void
}) {
  return (
    <div className={`border-b border-border flex items-center justify-between bg-card shrink-0 ${expanded ? "px-6 py-4" : "px-4 py-3"}`}>
      <div className="flex items-center gap-2">
        <Bot className="text-primary" size={expanded ? 24 : 20} />
        <h2 className={`font-semibold text-foreground ${expanded ? "text-xl" : "text-base"}`}>{title}</h2>
      </div>
      <div className="flex gap-1">
        {onExpand && (
          <button type="button" onClick={onExpand} className="p-1.5 hover:bg-muted rounded transition-colors">
            <Maximize2 size={expanded ? 20 : 16} />
          </button>
        )}
        <button type="button" onClick={onMinimize} className="p-1.5 hover:bg-muted rounded transition-colors">
          <X size={expanded ? 20 : 16} />
        </button>
      </div>
    </div>
  )
})

export function RAGChat() {
  const { currentCollection } = useAppContext()
  const { collection_id, company_id } = currentCollection

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const streamingMessageIdRef = useRef<string | null>(null)
  const streamBufferRef = useRef("")
  const rafRef = useRef<number | null>(null)
  const receivedChunkRef = useRef(false)
  const streamDoneRef = useRef(false)

  const flushStreamBuffer = useCallback(() => {
    const id = streamingMessageIdRef.current
    const chunk = streamBufferRef.current
    if (!id || !chunk) return

    streamBufferRef.current = ""
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, content: m.content + chunk } : m)),
    )
  }, [])

  const scheduleStreamFlush = useCallback(() => {
    if (rafRef.current !== null) return
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null
      flushStreamBuffer()
    })
  }, [flushStreamBuffer])

  const appendStreamChunk = useCallback(
    (chunk: string) => {
      streamBufferRef.current += chunk
      scheduleStreamFlush()
    },
    [scheduleStreamFlush],
  )

  const finishStreaming = useCallback(() => {
    if (streamDoneRef.current) return
    streamDoneRef.current = true

    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    flushStreamBuffer()
    streamingMessageIdRef.current = null
    setIsStreaming(false)
    setIsSubmitting(false)
    eventSourceRef.current?.close()
    eventSourceRef.current = null
  }, [flushStreamBuffer])

  const scrollToBottom = useCallback((smooth: boolean) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "end" })
  }, [])

  const showTyping = isSubmitting && !isStreaming

  // Auto-scroll when messages grow or stream updates (not when user types in the input)
  useEffect(() => {
    scrollToBottom(isStreaming)
  }, [messages, isStreaming, showTyping, scrollToBottom])

  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
      eventSourceRef.current?.close()
    }
  }, [])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || !collection_id || !company_id || isSubmitting) return

    const userMessage: Message = {
      id: newMessageId(),
      role: "user",
      content: text,
      timestamp: new Date(),
    }

    const assistantId = newMessageId()
    const assistantPlaceholder: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
    }

    setInput("")
    setMessages((prev) => [...prev, userMessage, assistantPlaceholder])
    setIsSubmitting(true)
    setIsStreaming(false)
    streamingMessageIdRef.current = assistantId
    streamBufferRef.current = ""
    receivedChunkRef.current = false
    streamDoneRef.current = false

    try {
      const response = await queryRAG(collection_id, {
        company_id,
        query: text,
        top_k: 5,
        include_context: true,
      })

      const eventSource = new EventSource(`${API_BASE_URL}/rag/stream/${response.task_id}`)
      eventSourceRef.current = eventSource

      eventSource.onmessage = (e) => {
        const chunk = e.data
        if (!chunk) return

        if (chunk.startsWith("Error:")) {
          if (rafRef.current !== null) {
            cancelAnimationFrame(rafRef.current)
            rafRef.current = null
          }
          streamBufferRef.current = ""
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: chunk } : m)),
          )
          finishStreaming()
          return
        }

        if (!receivedChunkRef.current) {
          receivedChunkRef.current = true
          setIsStreaming(true)
        }
        appendStreamChunk(chunk)
      }

      eventSource.onerror = () => {
        // EventSource fires onerror when the stream ends (including normal close)
        finishStreaming()
      }
    } catch (error) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: `Error: ${error instanceof Error ? error.message : "Failed to process query"}`,
              }
            : m,
        ),
      )
      finishStreaming()
    }
  }, [input, collection_id, company_id, isSubmitting, appendStreamChunk, finishStreaming])

  const handleSuggestion = useCallback((suggestion: string) => {
    setInput(suggestion)
  }, [])

  const inputDisabled = isSubmitting || !collection_id

  if (isMinimized) {
    return (
      <button
        type="button"
        onClick={() => setIsMinimized(false)}
        className="fixed bottom-4 right-4 w-14 h-14 gradient-primary text-white rounded-full shadow-lg hover:opacity-90 flex items-center justify-center z-50"
        aria-label="Open AI assistant"
      >
        <Bot size={24} />
      </button>
    )
  }

  const listProps = {
    messages,
    showTyping,
    onSuggestion: handleSuggestion,
    messagesEndRef,
    scrollContainerRef,
  }

  if (isExpanded) {
    return (
      <div className="fixed inset-0 bg-background z-50 flex flex-col">
        <ChatHeader title="AI-Powered Search" expanded onMinimize={() => setIsMinimized(true)} />
        <MessageList {...listProps} />
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          disabled={inputDisabled}
        />
      </div>
    )
  }

  return (
    <aside className="w-[420px] shrink-0 border-l border-border bg-card flex flex-col h-full hidden lg:flex">
      <ChatHeader
        title="AI Assistant"
        onExpand={() => setIsExpanded(true)}
        onMinimize={() => setIsMinimized(true)}
      />
      <MessageList {...listProps} compact />
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={inputDisabled}
        compact
      />
    </aside>
  )
}
