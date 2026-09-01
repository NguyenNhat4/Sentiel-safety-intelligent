import "@testing-library/jest-dom/vitest";
import {cleanup} from "@testing-library/react";
import {afterEach} from "vitest";
import {clearQueryCache} from "./api/query-cache";

afterEach(() => {
  cleanup();
  clearQueryCache();
});

Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
  configurable: true,
  value: () => null
});
