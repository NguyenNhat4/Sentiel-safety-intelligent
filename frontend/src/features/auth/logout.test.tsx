import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";
import App from "../../App";

const user = {id: "user-1", full_name: "Safety Manager", email: "antoan@sentinel.local", role: "safety_manager" as const, role_label: "Safety Manager", must_change_password: false};

afterEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

it("returns to login after server logout", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/auth/login")) return new Response(JSON.stringify({access_token: "token-1", token_type: "bearer", user}), {status: 200});
    return new Response(null, {status: 204});
  }));
  render(<App />);
  await screen.findByRole("button", {name: /\u0110\u0103ng nh\u1eadp/});
  fireEvent.change(screen.getByLabelText(/Email/), {target: {value: user.email}});
  fireEvent.change(screen.getByLabelText(/M\u1eadt kh\u1ea9u/), {target: {value: "Sentinel123!"}});
  fireEvent.click(screen.getByRole("button", {name: /\u0110\u0103ng nh\u1eadp/}));
  await screen.findByRole("button", {name: /\u0110\u0103ng xu\u1ea5t/});
  fireEvent.click(screen.getByRole("button", {name: /\u0110\u0103ng xu\u1ea5t/}));
  await waitFor(() => expect(screen.getByRole("button", {name: /\u0110\u0103ng nh\u1eadp/})).toBeInTheDocument());
});
