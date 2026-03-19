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
import StyleProfile from "./components/StyleProfile";
import RecommendationCard from "./components/RecommendationCard";

// ---------------------------------------------------------------------------
// Auth pages
// ---------------------------------------------------------------------------

test("Login page renders a Sign In button", () => {
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
  expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
});

test("Login page renders email and password inputs", () => {
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
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

test("Signup page renders confirm password field", () => {
  render(
    <MemoryRouter>
      <Signup />
    </MemoryRouter>
  );
  expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
});

// ---------------------------------------------------------------------------
// StyleProfile component
// ---------------------------------------------------------------------------

test("StyleProfile displays colors, silhouettes, tags, and summary", () => {
  const mockProfile = {
    colors: ["navy", "white"],
    silhouettes: ["slim-fit"],
    style_tags: ["casual", "minimalist"],
    summary: "A clean, understated look.",
  };

  render(<StyleProfile profile={mockProfile} imageUrl={null} />);
  expect(screen.getByText("navy")).toBeInTheDocument();
  expect(screen.getByText("white")).toBeInTheDocument();
  expect(screen.getByText("slim-fit")).toBeInTheDocument();
  expect(screen.getByText("casual")).toBeInTheDocument();
  expect(screen.getByText("minimalist")).toBeInTheDocument();
  expect(screen.getByText("A clean, understated look.")).toBeInTheDocument();
});

test("StyleProfile shows image when imageUrl is provided", () => {
  const mockProfile = { colors: [], silhouettes: [], style_tags: [], summary: "" };
  render(
    <StyleProfile profile={mockProfile} imageUrl="https://example.com/img.jpg" />
  );
  const img = screen.getByAltText("Analysed outfit");
  expect(img).toBeInTheDocument();
  expect(img).toHaveAttribute("src", "https://example.com/img.jpg");
});

// ---------------------------------------------------------------------------
// RecommendationCard component
// ---------------------------------------------------------------------------

test("RecommendationCard displays item details", () => {
  const item = {
    name: "Classic White T-Shirt",
    image: "https://example.com/tshirt.jpg",
    price: "$25",
    link: "https://www.uniqlo.com",
  };

  render(<RecommendationCard item={item} />);
  expect(screen.getByText("Classic White T-Shirt")).toBeInTheDocument();
  expect(screen.getByText("$25")).toBeInTheDocument();
  const shopLink = screen.getByRole("link", { name: /shop now/i });
  expect(shopLink).toHaveAttribute("href", "https://www.uniqlo.com");
  expect(shopLink).toHaveAttribute("target", "_blank");
  expect(shopLink).toHaveAttribute("rel", "noopener noreferrer");
});
