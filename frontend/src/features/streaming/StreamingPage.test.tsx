import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {expect, it} from "vitest";
import App from "../../App";

it("opens the browser streaming simulator from the safety-manager baseline", async () => {
  const {container} = render(<App />);
  const email = container.querySelector('input[type="email"]')!;
  const password = container.querySelector('input[type="password"]')!;
  fireEvent.change(email, {target: {value: "antoan@sentinel.local"}});
  fireEvent.change(password, {target: {value: "Sentinel123!"}});
  fireEvent.submit(container.querySelector("form")!);
  await waitFor(() => expect(screen.getByRole("heading", {name: "Live Monitor"})).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", {name: /streaming/i}));
  expect(screen.getByText("Browser simulation")).toBeInTheDocument();
});
