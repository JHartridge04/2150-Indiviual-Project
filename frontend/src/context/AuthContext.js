/**
 * AuthContext.js
 * Provides authentication state (user, session, token) and helper methods
 * (login, logout, signup) throughout the component tree.
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import supabase from "../services/supabaseClient";

const AuthContext = createContext(null);

/**
 * Wrap your application with <AuthProvider> to make auth state available
 * everywhere via the useAuth() hook.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore session from local storage on first mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Keep state in sync whenever the auth state changes (e.g. sign-out, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const value = {
    user,
    session,
    token: session?.access_token ?? null,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook for consuming auth context.
 * @returns {{ user, session, token, loading }}
 */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
