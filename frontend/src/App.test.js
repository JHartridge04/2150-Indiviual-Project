/**
 * App.test.js
 * Smoke tests — verify pages render without crashing.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock the AuthContext so pages don't need a real Supabase session
jest.mock("./context/AuthContext", () => ({
  useAuth: () => ({ user: null, session: null, token: null, loading: false }),
  AuthProvider: ({ children }) => <>{children}</>,
}));

// Mock supabaseClient to avoid real network calls
jest.mock("./services/supabaseClient", () => ({
  __esModule: true,
  default: {},
}));

import Login from "./pages/Login";
import Signup from "./pages/Signup";

test("Login page renders a Sign In button", () => {
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
  expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
});

test("Signup page renders a Create Account button", () => {
  render(
    <MemoryRouter>
      <Signup />
    </MemoryRouter>
  );
  expect(
    screen.getByRole("button", { name: /create account/i })
  ).toBeInTheDocument();
});
