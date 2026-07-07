import React, { useEffect, useRef } from "react";

interface Message {
  id: string;
  role: string;
  content: {
    text?: string;
    parts?: any[];
    tool_calls?: any[];
  };
  created_at: string;
  meta_data?: {
    tool_name?: string;
    [key: string]: any;
  };
}

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  backendUrl: string;
}

const resolveUrl = (path: string, backendUrl: string): string => {
  let url = path;

  // 1. If it's an absolute filesystem path containing /gen-content/
  if (url.includes("/gen-content/")) {
    const idx = url.indexOf("/gen-content/");
    url = "/sandbox/" + url.substring(idx + "/gen-content/".length);
  }

  // 2. Resolve relative path to backend URL
  if (url.startsWith("/")) {
    url = `${backendUrl.replace(/\/$/, "")}${url}`;
  }

  return url;
};

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  isLoading,
  backendUrl,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Format message text and resolve relative image paths to backend URL
  const formatText = (text: string) => {
    if (!text) return "";
    const trimmedText = text.trim();
    if (!trimmedText) return "";

    // 1. Regex to match markdown images: ![caption](url)
    const imgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    let parts: any[] = [];
    let lastIndex = 0;
    let match;

    while ((match = imgRegex.exec(trimmedText)) !== null) {
      // Add text before image
      if (match.index > lastIndex) {
        parts.push(trimmedText.substring(lastIndex, match.index));
      }

      const caption = match[1];
      const url = resolveUrl(match[2], backendUrl);

      parts.push(
        <div 
          key={`img-${match.index}`} 
          onClick={() => window.open(url, "_blank")}
          className="my-4 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/40 shadow-xl max-w-lg cursor-pointer hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/5 transition-all duration-300"
          title="Click to view full resolution"
        >
          <img src={url} alt={caption || "Generated Visual"} className="w-full h-auto object-cover max-h-[400px]" />
          {caption && (
            <div className="p-3 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-400 font-semibold tracking-wide uppercase select-none">
              {caption}
            </div>
          )}
        </div>
      );

      lastIndex = imgRegex.lastIndex;
    }

    if (lastIndex < trimmedText.length) {
      parts.push(trimmedText.substring(lastIndex));
    }

    // 2. Process markdown links pointing to images: [caption](url)
    const mdLinkImgRegex = /\[([^\]]*)\]\(([^)]*(?:\.(?:png|jpg|jpeg|gif|webp)|view\?filename=)[^)]*)\)/gi;
    let partsAfterMdLinks: any[] = [];

    for (const part of parts) {
      if (typeof part !== "string") {
        partsAfterMdLinks.push(part);
        continue;
      }

      let subParts = [];
      let lastSubIndex = 0;
      let subMatch;

      while ((subMatch = mdLinkImgRegex.exec(part)) !== null) {
        if (subMatch.index > lastSubIndex) {
          subParts.push(part.substring(lastSubIndex, subMatch.index));
        }

        const caption = subMatch[1];
        const rawUrl = subMatch[2];
        const resolvedUrl = resolveUrl(rawUrl, backendUrl);

        subParts.push(
          <div 
            key={`md-link-img-${subMatch.index}`} 
            onClick={() => window.open(resolvedUrl, "_blank")}
            className="my-4 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/40 shadow-xl max-w-lg cursor-pointer hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/5 transition-all duration-300"
            title="Click to view full resolution"
          >
            <img src={resolvedUrl} alt={caption || "Generated Visual"} className="w-full h-auto object-cover max-h-[400px]" />
            <div className="p-3 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-400 font-semibold tracking-wide uppercase select-none">
              {caption || "Generated Asset"}
            </div>
          </div>
        );

        lastSubIndex = mdLinkImgRegex.lastIndex;
      }

      if (lastSubIndex < part.length) {
        subParts.push(part.substring(lastSubIndex));
      }

      partsAfterMdLinks.push(...subParts);
    }
    parts = partsAfterMdLinks;

    // 3. Process raw image paths, absolute paths, or ComfyUI view URLs
    const rawPathRegex = /(?:`|\(|\[)?((?:https?:\/\/[^\s`"'()\]]+)?(?:\/[^\s`"'()\]]*)?\/(?:sandbox|workspace|shares|gen-content)\/[^\s`"'\)\],]+\.(?:png|jpg|jpeg|gif|webp)(:\?[^\s`"'\)\],]*)?|(?:https?:\/\/[^\s`"'()\]]+)?\/view\?filename=[^\s`"'\)\],]+)(?:`|\)|\])?/gi;
    let partsAfterRawPaths: any[] = [];

    for (const part of parts) {
      if (typeof part !== "string") {
        partsAfterRawPaths.push(part);
        continue;
      }

      let subParts = [];
      let lastSubIndex = 0;
      let subMatch;

      while ((subMatch = rawPathRegex.exec(part)) !== null) {
        if (subMatch.index > lastSubIndex) {
          subParts.push(part.substring(lastSubIndex, subMatch.index));
        }

        const rawUrl = subMatch[1];
        const resolvedUrl = resolveUrl(rawUrl, backendUrl);

        subParts.push(
          <div 
            key={`raw-path-img-${subMatch.index}`} 
            onClick={() => window.open(resolvedUrl, "_blank")}
            className="my-4 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/40 shadow-xl max-w-lg cursor-pointer hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/5 transition-all duration-300"
            title="Click to view full resolution"
          >
            <img src={resolvedUrl} alt="Generated Visual" className="w-full h-auto object-cover max-h-[400px]" />
            <div className="p-3 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-400 font-semibold tracking-wide uppercase select-none">
              Generated Asset
            </div>
          </div>
        );

        lastSubIndex = rawPathRegex.lastIndex;
      }

      if (lastSubIndex < part.length) {
        subParts.push(part.substring(lastSubIndex));
      }

      partsAfterRawPaths.push(...subParts);
    }
    parts = partsAfterRawPaths;

    // 4. Fallback: If no image was parsed, but the entire text is a path ending with an image extension
    if (parts.length === 1 && typeof parts[0] === "string") {
      const trimmed = parts[0].trim();
      const hasImageExt = /\.(?:png|jpg|jpeg|gif|webp)(?:\?.*)?$/i.test(trimmed);
      const isPathLike = trimmed.startsWith("/") || trimmed.startsWith("http://") || trimmed.startsWith("https://");

      if (isPathLike && hasImageExt) {
        const resolvedUrl = resolveUrl(trimmed, backendUrl);
        return (
          <div 
            onClick={() => window.open(resolvedUrl, "_blank")}
            className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950/40 shadow-xl max-w-lg my-2 cursor-pointer hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/5 transition-all duration-300"
            title="Click to view full resolution"
          >
            <img src={resolvedUrl} alt="Generated Asset" className="w-full h-auto object-cover max-h-[400px]" />
            <div className="p-3 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-400 font-semibold tracking-wide uppercase select-none">
              Generated Asset
            </div>
          </div>
        );
      }
    }

    // Process line breaks and markdown-style bold/inline code
    return parts.map((part, i) => {
      if (typeof part !== "string") return part;

      return (
        <span key={`part-str-${i}`} className="whitespace-pre-wrap break-words leading-relaxed text-sm block">
          {part.split("\n").map((line, lineIdx) => {
            // Process basic bold text: **text**
            const boldRegex = /\*\*([^*]+)\*\*/g;
            const lineParts = [];
            let lastLineIndex = 0;
            let boldMatch;

            while ((boldMatch = boldRegex.exec(line)) !== null) {
              if (boldMatch.index > lastLineIndex) {
                lineParts.push(line.substring(lastLineIndex, boldMatch.index));
              }
              lineParts.push(
                <strong key={`bold-${boldMatch.index}`} className="text-white font-bold">
                  {boldMatch[1]}
                </strong>
              );
              lastLineIndex = boldRegex.lastIndex;
            }

            if (lastLineIndex < line.length) {
              lineParts.push(line.substring(lastLineIndex));
            }

            // Process inline code blocks: `code`
            const processedLineParts = lineParts.map((item, itemIdx) => {
              if (typeof item !== "string") return item;

              const codeRegex = /`([^`]+)`/g;
              const codeParts = [];
              let lastCodeIndex = 0;
              let codeMatch;

              while ((codeMatch = codeRegex.exec(item)) !== null) {
                if (codeMatch.index > lastCodeIndex) {
                  codeParts.push(item.substring(lastCodeIndex, codeMatch.index));
                }
                codeParts.push(
                  <code key={`code-${codeMatch.index}`} className="px-1.5 py-0.5 rounded bg-slate-950 text-indigo-300 font-mono text-xs border border-slate-800">
                    {codeMatch[1]}
                  </code>
                );
                lastCodeIndex = codeRegex.lastIndex;
              }

              if (lastCodeIndex < item.length) {
                codeParts.push(item.substring(lastCodeIndex));
              }

              return <React.Fragment key={`line-part-frag-${itemIdx}`}>{codeParts}</React.Fragment>;
            });

            return (
              <span key={`line-${lineIdx}`} className="block min-h-[1rem]">
                {processedLineParts}
              </span>
            );
          })}
        </span>
      );
    });
  };

  const renderToolCall = (toolCall: any) => {
    return null;
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 py-8 custom-scrollbar">
      <div className="max-w-4xl mx-auto space-y-6">
        {messages.length === 0 ? (
          <div className="h-[50vh] flex flex-col items-center justify-center text-center px-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center font-bold text-white shadow-xl shadow-indigo-500/20 text-xl mb-4">
              R
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white mb-2 bg-gradient-to-r from-indigo-200 via-white to-violet-200 bg-clip-text text-transparent">
              Welcome to Radius AI
            </h1>
            <p className="text-sm text-slate-500 max-w-md leading-relaxed">
              Ingest marketing briefs, query competitor updates, and design brand assets with a ComfyUI and MCP integrated agent stack.
            </p>
          </div>
        ) : (
          messages.map((message, idx) => {
            try {
              const isUser = message.role === "user";
              const isTool = message.role === "tool";

              if (isTool) {
                return null;
              }

              // Hide intermediate assistant messages that contain tool calls (since tools should not be seen permanently),
              // but ONLY if there is a subsequent non-empty assistant response in the history.
              const hasSubsequentFinalResponse = messages.slice(idx + 1).some(
                m => m?.role === "assistant" &&
                  m?.content?.text &&
                  m.content.text.trim() !== "" &&
                  (!m.content.tool_calls || m.content.tool_calls.length === 0)
              );

              if (
                message?.role === "assistant" &&
                !message?.meta_data?._streaming &&
                message?.content?.tool_calls &&
                message.content.tool_calls.length > 0 &&
                hasSubsequentFinalResponse
              ) {
                return null;
              }

              return (
                <div key={message.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                  <div className={`flex gap-4 max-w-3xl ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                    {/* Avatar */}
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 select-none ${isUser
                      ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/10"
                      : message.meta_data?._streaming
                        ? "bg-gradient-to-tr from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/10 animate-pulse"
                        : "bg-gradient-to-tr from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/10"
                      }`}>
                      {isUser ? "U" : "AI"}
                    </div>

                    {/* Bubble content */}
                    <div className="space-y-1.5">
                      {message.meta_data?._streaming && (
                        <div className="text-[10px] text-indigo-400 font-semibold uppercase tracking-widest animate-pulse mb-1 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping"></span>
                          Thinking…
                        </div>
                      )}
                      <div className={`rounded-2xl p-4 border transition-all duration-300 ${isUser
                        ? "bg-slate-900 border-slate-800/60 text-slate-100"
                        : message.meta_data?._streaming
                          ? "bg-slate-900/30 border-indigo-500/20 text-slate-200"
                          : "bg-slate-900/30 border-slate-800/40 text-slate-200"
                        }`}>
                        {/* Render main text */}
                        {message.content?.text && formatText(message.content.text)}

                        {/* Render uploaded image preview if present */}
                        {message.meta_data?.image_path && (
                          <div 
                            onClick={() => {
                              if (message.meta_data?.image_path) {
                                window.open(resolveUrl(message.meta_data.image_path, backendUrl), "_blank");
                              }
                            }}
                            className="mt-3 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/60 shadow-xl max-w-sm cursor-pointer hover:border-indigo-500/50 transition-all duration-300"
                            title="Click to view full resolution"
                          >
                            <img 
                              src={resolveUrl(message.meta_data.image_path || "", backendUrl)} 
                              alt="Uploaded visual reference 1" 
                              className="w-full h-auto object-cover max-h-[200px]" 
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                            <div className="p-2 bg-slate-900 border-t border-slate-800 text-[10px] text-slate-400 font-semibold tracking-wide uppercase select-none flex items-center gap-1.5">
                              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3 text-indigo-400">
                                <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Z" />
                              </svg>
                              Uploaded Image 1
                            </div>
                          </div>
                        )}

                        {/* Render uploaded image 2 preview if present */}
                        {message.meta_data?.image2_path && (
                          <div 
                            onClick={() => {
                              if (message.meta_data?.image2_path) {
                                window.open(resolveUrl(message.meta_data.image2_path, backendUrl), "_blank");
                              }
                            }}
                            className="mt-3 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/60 shadow-xl max-w-sm cursor-pointer hover:border-indigo-500/50 transition-all duration-300"
                            title="Click to view full resolution"
                          >
                            <img 
                              src={resolveUrl(message.meta_data.image2_path || "", backendUrl)} 
                              alt="Uploaded visual reference 2" 
                              className="w-full h-auto object-cover max-h-[200px]" 
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                            <div className="p-2 bg-slate-900 border-t border-slate-800 text-[10px] text-slate-400 font-semibold tracking-wide uppercase select-none flex items-center gap-1.5">
                              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3 text-indigo-400">
                                <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Z" />
                              </svg>
                              Uploaded Image 2
                            </div>
                          </div>
                        )}

                        {/* Render uploaded image 3 preview if present */}
                        {message.meta_data?.image3_path && (
                          <div 
                            onClick={() => {
                              if (message.meta_data?.image3_path) {
                                window.open(resolveUrl(message.meta_data.image3_path, backendUrl), "_blank");
                              }
                            }}
                            className="mt-3 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/60 shadow-xl max-w-sm cursor-pointer hover:border-indigo-500/50 transition-all duration-300"
                            title="Click to view full resolution"
                          >
                            <img 
                              src={resolveUrl(message.meta_data.image3_path || "", backendUrl)} 
                              alt="Uploaded visual reference 3" 
                              className="w-full h-auto object-cover max-h-[200px]" 
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                            <div className="p-2 bg-slate-900 border-t border-slate-800 text-[10px] text-slate-400 font-semibold tracking-wide uppercase select-none flex items-center gap-1.5">
                              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3 text-indigo-400">
                                <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Z" />
                              </svg>
                              Uploaded Image 3
                            </div>
                          </div>
                        )}

                        {/* Render uploaded document chip if present */}
                        {message.meta_data?.doc_path && (
                          <div 
                            onClick={() => {
                              if (message.meta_data?.doc_path) {
                                window.open(resolveUrl(message.meta_data.doc_path, backendUrl), "_blank");
                              }
                            }}
                            className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-850 bg-slate-950/80 text-xs text-slate-300 hover:border-indigo-500/50 cursor-pointer transition-all max-w-xs"
                            title="Click to view document"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-indigo-400 shrink-0">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                            </svg>
                            <span className="font-semibold truncate max-w-[200px] text-[10px] text-slate-300">
                              {message.meta_data.doc_name || (message.meta_data.doc_path || "").split("/").pop()}
                            </span>
                          </div>
                        )}

                        {/* Blinking cursor while streaming */}
                        {message.meta_data?._streaming && (
                          <span className="inline-block w-0.5 h-4 bg-indigo-400 ml-0.5 align-middle animate-[blink_1s_step-end_infinite]" />
                        )}

                        {/* Render tool calls inside assistant bubbles */}
                        {!isUser && message.content?.tool_calls && message.content.tool_calls.map(renderToolCall)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            } catch (err) {
              console.error("Error rendering message:", message, err);
              return null;
            }
          })
        )}

        {/* Loading Spinner */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex gap-4 items-center">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 text-white flex items-center justify-center text-sm font-bold animate-pulse">
                AI
              </div>
              <div className="flex items-center gap-1.5 px-4 py-3 rounded-2xl border border-slate-800 bg-slate-900/10 text-xs text-slate-400 font-semibold select-none">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }}></span>
                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }}></span>
                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }}></span>
                Agent reasoning...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
