"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatInterface } from "@/components/ChatInterface";
import { InputArea } from "@/components/InputArea";

interface Session {
  id: string;
  title: string | null;
  created_at: string;
}

interface Message {
  id: string;
  role: string;
  content: {
    text?: string;
    parts?: any[];
    tool_calls?: any[];
  };
  created_at: string;
  meta_data?: any;
}

export default function Home() {
  // Authentication states
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  
  // App configuration
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [tone, setTone] = useState("Strict Coder");
  
  // Service status
  const [status, setStatus] = useState({
    fastapi: "offline",
    mcp_server: "offline",
    comfyui: "offline",
  });

  // Chat states
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [appError, setAppError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Initialize and load saved values
  useEffect(() => {
    setIsMounted(true);
    const savedUrl = localStorage.getItem("backend_url");
    if (savedUrl) setBackendUrl(savedUrl);

    const savedToken = localStorage.getItem("auth_token");
    const savedEmail = localStorage.getItem("auth_email");
    if (savedToken) {
      setToken(savedToken);
      setEmail(savedEmail || "");
    }
  }, []);

  // Poll service status when logged in
  useEffect(() => {
    if (!token) return;

    const fetchStatus = async () => {
      try {
        const resp = await fetch(`${backendUrl}/api/v1/agent/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (resp.ok) {
          const data = await resp.json();
          setStatus(data);
        } else {
          setStatus({ fastapi: "online", mcp_server: "offline", comfyui: "offline" });
        }
      } catch (err) {
        setStatus({ fastapi: "offline", mcp_server: "offline", comfyui: "offline" });
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 8000);
    return () => clearInterval(interval);
  }, [token, backendUrl]);

  // Load chat sessions
  const loadSessions = useCallback(async (authToken: string) => {
    try {
      const resp = await fetch(`${backendUrl}/api/v1/chat/sessions`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setSessions(data);
        // Automatically select the first session or create one if none exist
        if (data.length > 0 && !currentSessionId) {
          setCurrentSessionId(data[0].id);
        }
      } else if (resp.status === 401) {
        handleLogout();
      }
    } catch (err) {
      setAppError("Could not connect to FastAPI server. Please check settings.");
    }
  }, [backendUrl, currentSessionId]);

  // Load messages for the selected session
  const loadMessages = useCallback(async (sessionId: string, authToken: string) => {
    try {
      const resp = await fetch(`${backendUrl}/api/v1/chat/sessions/${sessionId}/messages`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        // Transform the DB message formats into local message formats
        const formatted = data.map((msg: any) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          created_at: msg.created_at,
          meta_data: msg.meta_data,
        }));
        setMessages(formatted);
      }
    } catch (err) {
      setAppError("Error loading session messages.");
    }
  }, [backendUrl]);

  // Sync sessions list when logged in
  useEffect(() => {
    if (token) {
      loadSessions(token);
    }
  }, [token, loadSessions]);

  // Sync messages when session changes
  useEffect(() => {
    if (token && currentSessionId) {
      loadMessages(currentSessionId, token);
    } else {
      setMessages([]);
    }
  }, [currentSessionId, token, loadMessages]);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthSuccess(null);
    setIsLoading(true);

    try {
      if (isRegisterMode) {
        const response = await fetch(`${backendUrl}/api/v1/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim(), password }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || "Registration failed.");
        }

        setAuthSuccess("Account successfully registered! You can now sign in.");
        setIsRegisterMode(false);
        setPassword("");
      } else {
        const params = new URLSearchParams();
        params.append("username", email.trim());
        params.append("password", password);

        const response = await fetch(`${backendUrl}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: params.toString(),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || "Invalid email or password.");
        }

        const data = await response.json();
        const accessToken = data.access_token;
        setToken(accessToken);
        localStorage.setItem("auth_token", accessToken);
        localStorage.setItem("auth_email", email.trim());
        setPassword("");
      }
    } catch (err: any) {
      setAuthError(err.message || "Connection timeout.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_email");
    setSessions([]);
    setCurrentSessionId(null);
    setMessages([]);
    setAuthError(null);
    setAuthSuccess(null);
  };

  const handleCreateSession = async () => {
    if (!token) return;
    try {
      const resp = await fetch(`${backendUrl}/api/v1/chat/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title: `Campaign Thread ${sessions.length + 1}` }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setSessions(prev => [data, ...prev]);
        setCurrentSessionId(data.id);
        setAppError(null);
      }
    } catch (err) {
      setAppError("Error creating new session.");
    }
  };

  const handleDeleteSession = async (id: string) => {
    if (!token) return;
    try {
      const resp = await fetch(`${backendUrl}/api/v1/chat/sessions/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        setSessions(prev => prev.filter(s => s.id !== id));
        if (currentSessionId === id) {
          setCurrentSessionId(null);
        }
      }
    } catch (err) {
      setAppError("Error deleting session.");
    }
  };

  const handleRenameSession = async (id: string, newTitle: string) => {
    if (!token) return;
    try {
      const resp = await fetch(`${backendUrl}/api/v1/chat/sessions/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title: newTitle }),
      });
      if (resp.ok) {
        const updated = await resp.json();
        setSessions(prev => prev.map(s => s.id === id ? updated : s));
      }
    } catch (err) {
      setAppError("Error renaming session.");
    }
  };

  const handleCancelResponse = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const handleSendMessage = async (
    text: string,
    image: File | null,
    document: File | null,
    mask: File | null
  ) => {
    if (!token) return;
    
    // Create new AbortController for this request
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    // Ensure we have an active session
    let targetSessionId = currentSessionId;
    if (!targetSessionId) {
      // Create session first
      try {
        const resp = await fetch(`${backendUrl}/api/v1/chat/sessions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ title: text.substring(0, 30) + "..." }),
        });
        if (resp.ok) {
          const data = await resp.json();
          setSessions(prev => [data, ...prev]);
          targetSessionId = data.id;
          setCurrentSessionId(data.id);
        } else {
          setAppError("Failed to auto-create session.");
          return;
        }
      } catch (err) {
        setAppError("Connection issue while auto-creating session.");
        return;
      }
    }

    // 1. Stage user message in UI immediately
    const tempUserMsg: Message = {
      id: Math.random().toString(),
      role: "user",
      content: { text },
      created_at: new Date().toISOString(),
      meta_data: {
        image_path: image ? URL.createObjectURL(image) : undefined,
        doc_path: document ? URL.createObjectURL(document) : undefined,
        doc_name: document ? document.name : undefined,
      }
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setIsLoading(true);
    setAppError(null);

    // Streaming thought accumulator message (shows while agent is thinking)
    const streamMsgId = "stream-" + Math.random().toString();

    // 2. Build FormData
    const formData = new FormData();
    formData.append("prompt", text);
    formData.append("session_id", targetSessionId as string);
    formData.append("tone", tone);
    if (image) formData.append("image", image);
    if (document) formData.append("document", document);
    if (mask) formData.append("mask", mask);

    try {
      const resp = await fetch(`${backendUrl}/api/v1/agent/chat`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`Server returned error status ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamingThought = "";
      let activeTools: string[] = [];

      // Insert a placeholder streaming message
      setMessages(prev => [...prev, {
        id: streamMsgId,
        role: "assistant",
        content: { text: "" },
        created_at: new Date().toISOString(),
        meta_data: { _streaming: true },
      }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages (separated by double newlines)
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.trim()) continue;
          
          let eventName = "message";
          let eventData = "";

          for (const line of part.split("\n")) {
            if (line.startsWith("event: ")) {
              eventName = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              eventData = line.slice(6).trim();
            }
          }

          if (!eventData) continue;

          try {
            const payload = JSON.parse(eventData);

            if (eventName === "agent_thought") {
              // Accumulate streamed text and update the placeholder bubble
              streamingThought += payload.delta ?? "";
              setMessages(prev => prev.map(m =>
                m.id === streamMsgId
                  ? { ...m, content: { text: streamingThought + (activeTools.length > 0 ? `\n\n⚙️ Running: ${activeTools.join(", ")}` : "") }, meta_data: { _streaming: true } }
                  : m
              ));

            } else if (eventName === "tool_start") {
              const toolName = payload.tool ?? "tool";

              // Human-readable labels for every known tool.
              // internet_search is tracked silently (no bubble text) to avoid cluttering the UI.
              const TOOL_LABELS: Record<string, string> = {
                internet_search:                     "", // intentionally blank — hidden
                write_file_to_sandbox:               "✏️ Writing to workspace…",
                read_user_document_tool:             "📄 Reading document…",
                write_todos:                         "📋 Planning tasks…",
                text_image:                          "🎨 Generating image…",
                image_reference_and_text_to_image:   "🖼️ Generating reference image…",
                image_to_image:                      "🔄 Transforming image…",
              };

              const label = TOOL_LABELS[toolName] ?? `⚙️ Running ${toolName.replace(/_/g, " ")}…`;

              if (!activeTools.includes(toolName)) {
                activeTools.push(toolName);
              }

              // Only update the bubble if this tool has a visible label
              if (label) {
                setMessages(prev => prev.map(m =>
                  m.id === streamMsgId
                    ? { ...m, content: { text: streamingThought + `\n\n${label}` }, meta_data: { _streaming: true } }
                    : m
                ));
              }

            } else if (eventName === "tool_end") {
              const toolName = payload.tool ?? "tool";
              activeTools = activeTools.filter(t => t !== toolName);

              // If there are still active tools with visible labels, keep showing the last one;
              // otherwise restore the accumulated thought text
              const TOOL_LABELS: Record<string, string> = {
                internet_search:                     "",
                write_file_to_sandbox:               "✏️ Writing to workspace…",
                read_user_document_tool:             "📄 Reading document…",
                write_todos:                         "📋 Planning tasks…",
                text_image:                          "🎨 Generating image…",
                image_reference_and_text_to_image:   "🖼️ Generating reference image…",
                image_to_image:                      "🔄 Transforming image…",
              };
              const remainingVisible = activeTools.filter(t => TOOL_LABELS[t] !== "");
              const nextLabel = remainingVisible.length > 0
                ? TOOL_LABELS[remainingVisible[remainingVisible.length - 1]] ?? ""
                : "";

              setMessages(prev => prev.map(m =>
                m.id === streamMsgId
                  ? { ...m, content: { text: streamingThought + (nextLabel ? `\n\n${nextLabel}` : "") }, meta_data: { _streaming: true } }
                  : m
              ));

            } else if (eventName === "agent_message") {
              // Final complete message — replace the streaming placeholder
              const finalText = payload.text ?? streamingThought;
              setMessages(prev => prev.map(m =>
                m.id === streamMsgId
                  ? { ...m, content: { text: finalText }, meta_data: {} }
                  : m
              ));
              streamingThought = finalText;

            } else if (eventName === "error") {
              const errMsg = payload.message ?? "Unknown agent error.";
              setMessages(prev => prev.map(m =>
                m.id === streamMsgId
                  ? { ...m, content: { text: `⚠️ ${errMsg}` }, meta_data: {} }
                  : m
              ));

            } else if (eventName === "done") {
              // Stream finished — reload session messages from DB for persistence sync
              await loadMessages(targetSessionId as string, token);
              await loadSessions(token);
            }
          } catch (parseErr) {
            // Ignore parse errors for partial chunks
          }
        }
      }

    } catch (err: any) {
      if (err.name === "AbortError") {
        // User aborted the prompt — remove the streaming placeholder cleanly
        setMessages(prev => prev.filter(m => m.id !== streamMsgId));
        return;
      }
      setAppError(err.message || "Connection timed out. Please verify FastAPI is running on port 8000.");
      // Replace streaming placeholder (or add error message if placeholder is gone)
      setMessages(prev => {
        const hasStreamMsg = prev.some(m => m.id === streamMsgId);
        const errorResponse: Message = {
          id: Math.random().toString(),
          role: "assistant",
          content: { text: `⚠️ Failed to connect to FastAPI Backend at **${backendUrl}**.\n\nPlease verify that the Python backend server is running and listening on port 8000.` },
          created_at: new Date().toISOString(),
        };
        if (hasStreamMsg) {
          return prev.map(m => m.id === streamMsgId ? errorResponse : m);
        }
        return [...prev, errorResponse];
      });
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleBackendUrlChange = (url: string) => {
    setBackendUrl(url);
    localStorage.setItem("backend_url", url);
  };

  // Prevent flash during hydration
  if (!isMounted) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  // Login Screen
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center relative overflow-hidden p-4 selection:bg-indigo-500/30 selection:text-indigo-200">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none animate-pulse duration-[8000ms]"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl pointer-events-none animate-pulse duration-[10000ms]"></div>
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-30"></div>

        <div className="w-full max-w-md p-8 rounded-2xl bg-slate-900/40 backdrop-blur-xl border border-slate-800/80 shadow-[0_20px_50px_rgba(0,0,0,0.5)] relative z-10 transition-all duration-300">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-200 via-white to-violet-200 bg-clip-text text-transparent">
              Millenium Radius
            </h2>
            <p className="text-slate-400 mt-2 text-sm">
              Marketing Campaign Agent Stack
            </p>
          </div>

          {/* Login / Register Toggle */}
          <div className="flex rounded-lg bg-slate-950/80 p-1 mb-6 border border-slate-800/60">
            <button
              type="button"
              onClick={() => {
                setIsRegisterMode(false);
                setAuthError(null);
                setAuthSuccess(null);
              }}
              className={`flex-1 py-2 text-sm font-semibold rounded-md text-center transition-all duration-200 ${
                !isRegisterMode
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setIsRegisterMode(true);
                setAuthError(null);
                setAuthSuccess(null);
              }}
              className={`flex-1 py-2 text-sm font-semibold rounded-md text-center transition-all duration-200 ${
                isRegisterMode
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register
            </button>
          </div>

          {authError && (
            <div className="mb-5 p-3 rounded-lg border border-red-500/20 bg-red-500/10 text-red-300 text-xs leading-relaxed animate-shake">
              <span className="font-semibold block mb-0.5 font-sans">Authentication Error</span>
              {authError}
            </div>
          )}

          {authSuccess && (
            <div className="mb-5 p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-300 text-xs leading-relaxed">
              <span className="font-semibold block mb-0.5 font-sans">Success</span>
              {authSuccess}
            </div>
          )}

          <form onSubmit={handleAuthSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                required
                className="w-full px-4 py-3 rounded-lg bg-slate-950/60 border border-slate-800 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/80 transition-all text-sm font-sans"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full px-4 py-3 rounded-lg bg-slate-950/60 border border-slate-800 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/80 transition-all text-sm font-sans"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">FastAPI Gateway</label>
              <input
                type="text"
                value={backendUrl}
                onChange={(e) => handleBackendUrlChange(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-slate-950/30 border border-slate-800/80 text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-xs font-mono"
                placeholder="http://localhost:8000"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/10 hover:shadow-indigo-600/20 transition-all duration-300 flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
              ) : isRegisterMode ? (
                "Create Account"
              ) : (
                "Access Dashboard"
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Authenticated Dashboard
  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={setCurrentSessionId}
        onCreateSession={handleCreateSession}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        tone={tone}
        onChangeTone={setTone}
        backendUrl={backendUrl}
        onChangeBackendUrl={handleBackendUrlChange}
        status={status}
        onLogout={handleLogout}
        userEmail={email}
      />

      <main className="flex-1 flex flex-col h-full bg-slate-900/10 overflow-hidden relative">
        {/* Glow decoration */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-3xl pointer-events-none"></div>

        {/* Top bar header */}
        <header className="px-6 py-4 border-b border-slate-800/60 bg-slate-950/20 backdrop-blur-md flex items-center justify-between shrink-0 z-10">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-bold text-white uppercase tracking-wider">Active Stream</h1>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400 font-medium">
              {sessions.find(s => s.id === currentSessionId)?.title || "Select or start a chat"}
            </span>
          </div>

          {/* Quick status alerts */}
          {appError && (
            <div className="px-3 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-[11px] font-semibold flex items-center gap-1.5 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
              {appError}
            </div>
          )}
        </header>

        {/* Messaging Stream viewport */}
        <ChatInterface
          messages={messages}
          isLoading={isLoading}
          backendUrl={backendUrl}
        />

        {/* Input box bottom */}
        <InputArea
          onSendMessage={handleSendMessage}
          onCancelResponse={handleCancelResponse}
          isLoading={isLoading}
        />
      </main>
    </div>
  );
}
