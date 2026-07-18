import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// React 18 新式挂载
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
