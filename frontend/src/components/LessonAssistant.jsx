import { useState } from "react";
import { assistantAPI } from "../services/api";

/**
 * 当前课节 AI 问答
 */
export default function LessonAssistant({ lessonId }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || asking) return;

    setMessages((current) => [
      ...current,
      { role: "user", content: trimmedQuestion },
    ]);
    setQuestion("");
    setError(null);
    setAsking(true);

    try {
      const result = await assistantAPI.ask(lessonId, trimmedQuestion);
      setMessages((current) => [
        ...current,
        { role: "assistant", content: result.answer },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
    }
  };

  return (
    <section className="card lesson-assistant">
      <div className="lesson-assistant-header">
        <div>
          <h3>AI 学习助手</h3>
          <p>基于当前课节转写内容回答问题</p>
        </div>
      </div>

      {messages.length > 0 && (
        <div className="lesson-assistant-messages" aria-live="polite">
          {messages.map((message, index) => (
            <div
              className={`lesson-assistant-message ${message.role}`}
              key={`${message.role}-${index}`}
            >
              <span>{message.role === "user" ? "你" : "AI"}</span>
              <p>{message.content}</p>
            </div>
          ))}
          {asking && (
            <div className="lesson-assistant-message assistant pending">
              <span>AI</span>
              <p>正在查找当前课节内容...</p>
            </div>
          )}
        </div>
      )}

      {error && <div className="lesson-assistant-error">{error}</div>}

      <form className="lesson-assistant-form" onSubmit={handleSubmit}>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="例如：这节课的核心知识点是什么？"
          maxLength={1000}
          rows={2}
          disabled={asking}
        />
        <button
          className="btn btn-primary"
          type="submit"
          disabled={!question.trim() || asking}
        >
          {asking ? "回答中..." : "提问"}
        </button>
      </form>
    </section>
  );
}
