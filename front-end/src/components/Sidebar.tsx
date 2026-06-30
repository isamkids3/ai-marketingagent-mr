import React from "react";

interface Session {
  id: string;
  title: string | null;
  created_at: string;
}

interface SidebarProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
  tone: string;
  onChangeTone: (tone: string) => void;
  backendUrl: string;
  onChangeBackendUrl: (url: string) => void;
  status: {
    fastapi: string;
    mcp_server: string;
    comfyui: string;
  };
  onLogout: () => void;
  userEmail: string | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onRenameSession,
  tone,
  onChangeTone,
  backendUrl,
  onChangeBackendUrl,
  status,
  onLogout,
  userEmail,
}) => {
  const [hoveredTone, setHoveredTone] = React.useState<string | null>(null);
  const [editingSessionId, setEditingSessionId] = React.useState<string | null>(null);
  const [editingTitle, setEditingTitle] = React.useState<string>("");

  const handleSaveRename = (id: string) => {
    if (editingTitle.trim()) {
      onRenameSession(id, editingTitle.trim());
    }
    setEditingSessionId(null);
  };

  return (
    <aside className="w-80 border-r border-slate-800 bg-slate-950 flex flex-col h-full overflow-hidden text-slate-200">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
            M
          </div>
          <div>
            <h2 className="font-bold tracking-tight text-white leading-none">Radius AI</h2>
            <span className="text-[10px] text-slate-500 font-semibold tracking-wider uppercase">Layer 1 Portal</span>
          </div>
        </div>
      </div>

      {/* Service Status Indicators */}
      <div className="px-6 py-4 border-b border-slate-800/50 bg-slate-900/10">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Service Monitors</h3>
        <div className="grid grid-cols-3 gap-2">
          {/* FastAPI */}
          <div className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900/40 border border-slate-800/60 shadow-inner">
            <span className="text-[9px] text-slate-500 font-medium uppercase tracking-wider mb-1">FastAPI</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${status.fastapi === "online" ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"} animate-pulse`}></span>
              <span className="text-xs font-bold text-white uppercase">{status.fastapi === "online" ? "OK" : "ERR"}</span>
            </div>
          </div>
          {/* MCP Server */}
          <div className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900/40 border border-slate-800/60 shadow-inner">
            <span className="text-[9px] text-slate-500 font-medium uppercase tracking-wider mb-1">Creator MCP</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${status.mcp_server === "online" ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"} animate-pulse`}></span>
              <span className="text-xs font-bold text-white uppercase">{status.mcp_server === "online" ? "OK" : "ERR"}</span>
            </div>
          </div>
          {/* ComfyUI */}
          <div className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900/40 border border-slate-800/60 shadow-inner">
            <span className="text-[9px] text-slate-500 font-medium uppercase tracking-wider mb-1">ComfyUI</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${status.comfyui === "online" ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"} animate-pulse`}></span>
              <span className="text-xs font-bold text-white uppercase">{status.comfyui === "online" ? "OK" : "ERR"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tone & Settings */}
      <div className="p-6 border-b border-slate-800/50 space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Agent Demeanor</label>
          <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
            {["Creative", "Professional", "Strict Coder"].map((t) => {
              const isHovered = hoveredTone === t;
              let tooltipEl = null;
              if (t === "Creative") {
                tooltipEl = (
                  <div
                    className={`absolute left-0 bottom-full mb-2.5 w-64 p-3 rounded-xl bg-slate-950/95 backdrop-blur-md border border-slate-800/80 text-[10px] text-slate-300 shadow-2xl transition-all duration-200 pointer-events-none text-left leading-normal z-[100] ${
                      isHovered ? "opacity-100 visible translate-y-0" : "opacity-0 invisible translate-y-1"
                    }`}
                  >
                    <span className="font-semibold text-indigo-400 block mb-1">Creative Mode (Temp: 0.9)</span>
                    <span>Best for brainstorming ideas & creative prompts. <span className="text-amber-500 font-semibold">Warning: High temp may cause minor workflow parameter issues.</span></span>
                  </div>
                );
              } else if (t === "Professional") {
                tooltipEl = (
                  <div
                    className={`absolute left-1/2 -translate-x-1/2 bottom-full mb-2.5 w-64 p-3 rounded-xl bg-slate-950/95 backdrop-blur-md border border-slate-800/80 text-[10px] text-slate-300 shadow-2xl transition-all duration-200 pointer-events-none text-left leading-normal z-[100] ${
                      isHovered ? "opacity-100 visible translate-y-0" : "opacity-0 invisible translate-y-1"
                    }`}
                  >
                    <span className="font-semibold text-indigo-400 block mb-1">Professional Mode (Temp: 0.6)</span>
                    <span>Balanced setting for standard marketing copy, strategy, and tool calls.</span>
                  </div>
                );
              } else if (t === "Strict Coder") {
                tooltipEl = (
                  <div
                    className={`absolute right-0 bottom-full mb-2.5 w-64 p-3 rounded-xl bg-slate-950/95 backdrop-blur-md border border-slate-800/80 text-[10px] text-slate-300 shadow-2xl transition-all duration-200 pointer-events-none text-left leading-normal z-[100] ${
                      isHovered ? "opacity-100 visible translate-y-0" : "opacity-0 invisible translate-y-1"
                    }`}
                  >
                    <span className="font-semibold text-indigo-400 block mb-1">Strict Coder Mode (Temp: 0.3)</span>
                    <span>High determinism. Perfect for file writing and structured tool executions.</span>
                  </div>
                );
              }

              return (
                <div key={t} className="relative">
                  <button
                    type="button"
                    onClick={() => onChangeTone(t)}
                    onMouseEnter={() => setHoveredTone(t)}
                    onMouseLeave={() => setHoveredTone(null)}
                    className={`w-full py-1.5 text-[10px] font-bold rounded-md transition-all duration-200 cursor-pointer ${
                      tone === t
                        ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {t.split(" ")[0]}
                  </button>
                  {tooltipEl}
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Gateway Node</label>
          <input
            type="text"
            value={backendUrl}
            onChange={(e) => onChangeBackendUrl(e.target.value)}
            className="w-full px-3 py-1.5 text-xs rounded-md bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-all font-mono"
            placeholder="http://localhost:8000"
          />
        </div>
      </div>

      {/* Chat Sessions History */}
      <div className="flex-1 flex flex-col overflow-hidden p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Histories</span>
          <button
            onClick={onCreateSession}
            className="p-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-900 transition-all flex items-center gap-1 text-[11px] font-medium"
            title="Create New Chat"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3.5 h-3.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Session
          </button>
        </div>

        {/* Scrollable list */}
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-2 custom-scrollbar">
          {sessions.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-600 font-medium">
              No historical interactions.
            </div>
          ) : (
            sessions.map((session) => {
              const isActive = session.id === currentSessionId;
              const isEditing = session.id === editingSessionId;
              return (
                <div
                  key={session.id}
                  onClick={() => !isEditing && onSelectSession(session.id)}
                  className={`group w-full flex items-center justify-between p-3 rounded-xl border text-left cursor-pointer transition-all duration-200 ${
                    isActive
                      ? "bg-slate-900 border-indigo-600/50 text-white shadow-lg shadow-indigo-600/5"
                      : "bg-slate-950/20 border-slate-800/40 text-slate-400 hover:bg-slate-900/40 hover:border-slate-800/80 hover:text-slate-200"
                  }`}
                >
                  <div className="flex items-center gap-2.5 overflow-hidden w-[72%]">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className={`w-4 h-4 shrink-0 ${isActive ? "text-indigo-400" : "text-slate-600"}`}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"
                      />
                    </svg>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onBlur={() => handleSaveRename(session.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            handleSaveRename(session.id);
                          } else if (e.key === "Escape") {
                            setEditingSessionId(null);
                          }
                        }}
                        className="bg-slate-950 border border-indigo-500 rounded px-1.5 py-0.5 text-xs text-white focus:outline-none focus:ring-0 w-full font-sans"
                        autoFocus
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <span className="truncate text-xs font-semibold select-none leading-none pt-0.5">
                        {session.title || "Untitled Session"}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all shrink-0">
                    {!isEditing && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingSessionId(session.id);
                          setEditingTitle(session.title || "");
                        }}
                        className="p-1 rounded-md text-slate-500 hover:text-indigo-400 hover:bg-slate-800/80 transition-all"
                        title="Rename session"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-3.5 h-3.5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.83 20.013a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                        </svg>
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                      className="p-1 rounded-md text-slate-500 hover:text-red-400 hover:bg-slate-800/80 transition-all"
                      title="Delete session"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-3.5 h-3.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Footer Profile */}
      <div className="p-6 border-t border-slate-800/80 flex items-center justify-between bg-slate-900/10">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center font-bold text-indigo-300 text-sm select-none shrink-0">
            {userEmail ? userEmail[0].toUpperCase() : "U"}
          </div>
          <div className="overflow-hidden">
            <p className="text-xs font-semibold text-white truncate leading-none mb-0.5">Active User</p>
            <p className="text-[10px] text-slate-500 truncate leading-none">{userEmail || "anonymous@example.com"}</p>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-slate-900 transition-all border border-transparent hover:border-slate-800/60"
          title="Sign Out"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75" />
          </svg>
        </button>
      </div>
    </aside>
  );
};
