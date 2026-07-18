import { useRef, useState } from "react";

/**
 * 文件上传组件
 *
 * @param {string} accept - 接受的文件类型
 * @param {function} onUpload - 上传回调 (file) => Promise
 * @param {boolean} uploading - 上传中
 */
export default function FileUploader({ accept = "audio/*", onUpload, uploading }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);

  const handleChange = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    try {
      await onUpload(file);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      alert("上传失败: " + err.message);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        style={{ fontSize: "0.85rem" }}
        disabled={uploading}
      />
      {file && (
        <span style={{ fontSize: "0.85rem", color: "#666" }}>
          {file.name} ({(file.size / 1024 / 1024).toFixed(1)}MB)
        </span>
      )}
      <button
        className="btn btn-primary btn-sm"
        onClick={handleUpload}
        disabled={!file || uploading}
      >
        {uploading ? "上传中..." : "上传"}
      </button>
    </div>
  );
}
