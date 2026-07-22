import { useState } from "react";

export default function ExecutionPackageSection({ title, copyText, children, featured = false }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(copyText);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <section className={`execution-section${featured ? " featured" : ""}`}>
      <header>
        <h2>{title}</h2>
        {copyText && (
          <button className="btn btn-secondary btn-sm" onClick={copy}>
            {copied ? "已复制" : "复制"}
          </button>
        )}
      </header>
      {children}
    </section>
  );
}
