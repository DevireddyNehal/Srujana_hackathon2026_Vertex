import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Dashboard from "./Dashboard";

const root = document.getElementById("root");

if (!root) {
  throw new Error("The portfolio risk dashboard root element is missing.");
}

createRoot(root).render(
  <StrictMode>
    <Dashboard />
  </StrictMode>,
);
