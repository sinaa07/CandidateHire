"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Bot, User, Sparkles, X, Minimize2, Maximize2 } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { queryRAG } from "@/utils/api"

interface Message {
  role: "user" | "assistant" | "system"
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

export function RAGChat() {
  const { currentCollection } = useAppContext()
  const { collection_id, company_id } = currentCollection
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  const handleSend = async () => {
    if (!input.trim() || !collection_id || !company_id || isLoading) return

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      // Submit query
      const response = await queryRAG(collection_id, {
        company_id: company_id,
        query: input.trim(),
        top_k: 5,
        include_context: true,
      })

      const { task_id } = response

      // Stream response via SSE
      const eventSource = new EventSource(`${API_BASE_URL}/rag/stream/${task_id}`)
      eventSourceRef.current = eventSource

      let assistantMessage: Message = {
        role: "assistant",
        content: "",
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])

      eventSource.onmessage = (e) => {
        const chunk = e.data
        if (chunk && !chunk.startsWith("Error:")) {
          setMessages((prev) => {
            const updated = [...prev]
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: updated[updated.length - 1].content + chunk,
            }
            return updated
          })
        } else if (chunk.startsWith("Error:")) {
          setMessages((prev) => {
            const updated = [...prev]
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: chunk,
            }
            return updated
          })
          setIsLoading(false)
          eventSource.close()
        }
      }

      eventSource.onerror = () => {
        setIsLoading(false)
        eventSource.close()
      }
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Failed to process query"}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion)
  }

  if (isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className="fixed bottom-4 right-4 w-14 h-14 bg-[#6366F1] text-white rounded-full shadow-lg hover:bg-[#4F46E5] transition-all flex items-center justify-center z-50"
      >
        <Bot size={24} />
      </button>
    )
  }

  if (isExpanded) {
    return (
      <div className="fixed inset-0 bg-white z-50 flex flex-col">
        <div className="border-b border-[#E5E5E5] px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="text-[#6366F1]" size={24} />
            <h2 className="text-xl font-semibold text-[#262626]">AI-Powered Search</h2>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setIsExpanded(false)}
              className="p-2 hover:bg-[#F5F5F5] rounded-md transition-colors"
            >
              <Minimize2 size={20} />
            </button>
            <button
              onClick={() => setIsMinimized(true)}
              className="p-2 hover:bg-[#F5F5F5] rounded-md transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden flex">
          <div className="flex-1 flex flex-col">
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.length === 0 && (
                <div className="text-center py-12">
                  <Sparkles className="mx-auto text-[#6366F1] mb-4" size={48} />
                  <h3 className="text-xl font-semibold text-[#262626] mb-2">AI Assistant</h3>
                  <p className="text-[#737373] mb-6">Ask questions about your candidates</p>
                  <div className="grid grid-cols-2 gap-3 max-w-2xl mx-auto">
                    {SUGGESTIONS.map((suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSuggestion(suggestion)}
                        className="text-left p-3 bg-[#F5F5F5] hover:bg-[#E5E5E5] rounded-lg text-sm text-[#262626] transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-[#6366F1] flex items-center justify-center flex-shrink-0">
                      <Bot size={16} className="text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[70%] rounded-lg p-4 ${
                      msg.role === "user"
                        ? "bg-[#6366F1] text-white"
                        : "bg-white shadow-card text-[#262626]"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    <p className="text-xs mt-2 opacity-70">
                      {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  {msg.role === "user" && (
                    <div className="w-8 h-8 rounded-full bg-[#E5E5E5] flex items-center justify-center flex-shrink-0">
                      <User size={16} className="text-[#737373]" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-[#6366F1] flex items-center justify-center">
                    <Bot size={16} className="text-white" />
                  </div>
                  <div className="bg-white shadow-card rounded-lg p-4">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-[#6366F1] rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 bg-[#6366F1] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 bg-[#6366F1] rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="border-t border-[#E5E5E5] p-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                  placeholder="Type your question..."
                  className="flex-1 px-4 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6366F1] focus:border-transparent"
                  disabled={isLoading || !collection_id}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading || !collection_id}
                  className="px-6 py-2 bg-[#6366F1] text-white rounded-lg hover:bg-[#4F46E5] disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  <Send size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-[420px] border-l border-[#E5E5E5] bg-white flex flex-col h-full">
      <div className="border-b border-[#E5E5E5] px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="text-[#6366F1]" size={20} />
          <h3 className="font-semibold text-[#262626]">AI Assistant</h3>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setIsExpanded(true)}
            className="p-1.5 hover:bg-[#F5F5F5] rounded transition-colors"
          >
            <Maximize2 size={16} />
          </button>
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1.5 hover:bg-[#F5F5F5] rounded transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Sparkles className="mx-auto text-[#6366F1] mb-3" size={32} />
            <p className="text-sm text-[#737373] mb-4">Ask questions about your candidates</p>
            <div className="space-y-2">
              {SUGGESTIONS.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestion(suggestion)}
                  className="w-full text-left p-2 bg-[#F5F5F5] hover:bg-[#E5E5E5] rounded-lg text-xs text-[#262626] transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="w-6 h-6 rounded-full bg-[#6366F1] flex items-center justify-center flex-shrink-0">
                <Bot size={12} className="text-white" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-lg p-3 text-xs ${
                msg.role === "user"
                  ? "bg-[#6366F1] text-white"
                  : "bg-white shadow-card text-[#262626]"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
            {msg.role === "user" && (
              <div className="w-6 h-6 rounded-full bg-[#E5E5E5] flex items-center justify-center flex-shrink-0">
                <User size={12} className="text-[#737373]" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2 justify-start">
            <div className="w-6 h-6 rounded-full bg-[#6366F1] flex items-center justify-center">
              <Bot size={12} className="text-white" />
            </div>
            <div className="bg-white shadow-card rounded-lg p-3">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-[#6366F1] rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 bg-[#6366F1] rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 bg-[#6366F1] rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-[#E5E5E5] p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Type your question..."
            className="flex-1 px-3 py-2 text-sm border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6366F1] focus:border-transparent"
            disabled={isLoading || !collection_id}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || !collection_id}
            className="px-4 py-2 bg-[#6366F1] text-white rounded-lg hover:bg-[#4F46E5] disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
