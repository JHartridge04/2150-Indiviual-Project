/**
 * ProtectedRoute.js
 * Renders its children only if the user is authenticated.
 * While auth state is loading it shows nothing; when unauthenticated
 * it redirects to /login.
 */

import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    // Optionally render a spinner here
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
