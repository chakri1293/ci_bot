import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

export default function App() {
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading]);

  const sendQuery = async () => {
    if (!query.trim()) return;

    setHistory((h) => [...h, { sender: "user", text: query }]);
    const userQuery = query;
    setQuery("");
    inputRef.current?.focus();

    setLoading(true);

    try {
      // const response = await fetch("http://ci-news-system-backendapi-env.eba-8fpv57cs.us-west-2.elasticbeanstalk.com/query", {
      const response = await fetch("http://127.0.0.1:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userQuery }),
      });

      const data = await response.json();

      let content = "";
      let isMarkdown = true;

      // ---------- Handle pipeline rich output ----------
      const output = data?.data || {};

      if (output.type === "text") {
        content = output.content;
        isMarkdown = false;
      } else if (output.type === "mixed" || output.type === "rich") {
        if (Array.isArray(output.content)) {
          // Convert structured content blocks to markdown
          content = output.content
            .map((block) => {
              switch (block.type) {
                case "paragraph":
                  return block.text;
                case "bullet":
                  return `- ${block.text}`;
                case "topic":
                  return `### ${block.title}\n${block.text}`;
                case "image":
                  return `![${block.meta?.caption || ""}](${block.content})`;
                default:
                  return block.text || "";
              }
            })
            .join("\n\n");
        } else {
          // fallback: treat as plain string
          content = String(output.content);
        }
        isMarkdown = true;
      } else {
        // fallback: stringified object
        content = JSON.stringify(output, null, 2);
        isMarkdown = true;
      }

      setHistory((h) => [...h, { sender: "bot", text: content, isMarkdown }]);
    } catch (error) {
      console.error(error);
      setHistory((h) => [
        ...h,
        { sender: "bot", text: "Error: Unable to fetch response.", isMarkdown: false },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuery();
    }
  };

  return (
    <div className="app-wrapper">
      <div className="app-container">
        <header className="header">Next-Gen Competitive & News Intelligence Bot</header>

        <main className="chat-window" role="log" aria-live="polite">
          {history.map((msg, idx) => (
            <div
              key={idx}
              className={`chat-message ${msg.sender}`}
              style={{
                flexDirection: msg.sender === "user" ? "row-reverse" : "row",
                justifyContent: msg.sender === "user" ? "flex-end" : "flex-start",
              }}
            >
              <div className="avatar">{msg.sender === "user" ? "👤" : "🤖"}</div>
              <div
                className="message-content"
                style={{ width: msg.sender === "user" ? "80%" : "87%" }}
              >
                {msg.isMarkdown ? <ReactMarkdown>{msg.text}</ReactMarkdown> : msg.text}
              </div>
            </div>
          ))}

          {loading && (
            <div className="chat-message bot">
              <div className="avatar">🤖</div>
              <div className="message-content typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </main>

        <div className="input-container">
          <textarea
            ref={inputRef}
            className="chat-input"
            rows={1}
            placeholder="Type your message..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="send-button" onClick={sendQuery}>⬆️</button>
        </div>
      </div>
    </div>
  );
}
