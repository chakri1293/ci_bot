import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

export default function App() {
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState([]);
  const inputRef = useRef(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  async function sendQuery() {
    if (!query.trim()) return;
    setHistory((h) => [...h, { sender: "user", text: query }]);

    try {
      const response = await fetch("http://127.0.0.1:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      const content = data?.data?.markdown || data?.data?.summary || JSON.stringify(data?.data, null, 2);

      setHistory((h) => [...h, { sender: "bot", text: content, isMarkdown: true }]);
    } catch {
      setHistory((h) => [...h, { sender: "bot", text: "Error: Unable to fetch response." }]);
    }

    setQuery("");
    inputRef.current?.focus();
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuery();
    }
  };

  return (
    <div className="app-container">
      <header className="header">Competitive Intelligence Chatbot</header>
      <main className="chat-window" role="log" aria-live="polite">
        {history.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.sender}`}>
            <div className="avatar" aria-hidden="true">
              {msg.sender === "user" ? "👤" : "🤖"}
            </div>
            <div className="message-content">
              {msg.isMarkdown ? <ReactMarkdown>{msg.text}</ReactMarkdown> : msg.text}
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </main>

      <textarea
        ref={inputRef}
        className="chat-input"
        rows={3}
        placeholder="Type your message here..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button className="send-button" onClick={sendQuery}>Send</button>
    </div>
  );
}
