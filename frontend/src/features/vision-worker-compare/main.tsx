import {StrictMode} from "react";
import {createRoot} from "react-dom/client";

import {VisionWorkerComparePage} from "./VisionWorkerComparePage";
import "./vision-worker-compare.css";

const root = document.getElementById("vision-worker-compare-root");
if (!root) throw new Error("Vision worker compare root element is missing");

createRoot(root).render(
  <StrictMode>
    <VisionWorkerComparePage />
  </StrictMode>
);
