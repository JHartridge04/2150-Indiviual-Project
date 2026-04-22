/**
 * App.js
 * Root component — sets up routing and the AuthProvider context.
 *
 * Route map:
 *   /           → Home (upload + style profile) — protected
 *   /recommendations → Recommendations page — protected
 *   /login      → Login page
 *   /signup     → Signup page
 *   /logout     → Logout (effect-only component)
 *   *           → Redirect to /
 */

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import PublicOnlyRoute from "./components/PublicOnlyRoute";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Logout from "./pages/Logout";
import Landing from "./pages/Landing";
import Recommendations from "./pages/Recommendations";
import History from "./pages/History";
import Profile from "./pages/Profile";
import Wardrobe from "./pages/Wardrobe";
import Compare from "./pages/Compare";
import GenerateLook from "./pages/GenerateLook";
import ResetPassword from "./pages/ResetPassword";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/landing" element={<PublicOnlyRoute><Landing /></PublicOnlyRoute>} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/logout" element={<Logout />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recommendations/:analysisId"
            element={
              <ProtectedRoute>
                <Recommendations />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <History />
              </ProtectedRoute>
            }
          />

          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />

          <Route
            path="/wardrobe"
            element={
              <ProtectedRoute>
                <Wardrobe />
              </ProtectedRoute>
            }
          />

          <Route
            path="/compare"
            element={
              <ProtectedRoute>
                <Compare />
              </ProtectedRoute>
            }
          />

          <Route
            path="/looks"
            element={
              <ProtectedRoute>
                <GenerateLook />
              </ProtectedRoute>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
