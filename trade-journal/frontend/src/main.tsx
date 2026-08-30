import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Applied before the first render so a saved light-theme preference
// doesn't flash dark on load.
try {
  if (localStorage.getItem("theme") === "light") {
    document.documentElement.dataset.theme = "light";
  }
} catch {
  // localStorage unavailable — falls back to the default dark theme
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
