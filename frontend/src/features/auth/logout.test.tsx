import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {expect, it} from "vitest";
import App from "../../App";
it("returns to login after mock logout", async () => { const {container} = render(<App />); fireEvent.change(container.querySelector('input[type="email"]')!, {target: {value: "antoan@sentinel.local"}}); fireEvent.change(container.querySelector('input[type="password"]')!, {target: {value: "Sentinel123!"}}); fireEvent.submit(container.querySelector("form")!); await waitFor(() => expect(screen.getByRole("button", {name: "Đăng xuất"})).toBeInTheDocument()); fireEvent.click(screen.getByRole("button", {name: "Đăng xuất"})); await waitFor(() => expect(container.querySelector('input[type="email"]')).toBeInTheDocument()); });
