/**
 * Logout.js
 * Signs the user out and redirects to /login.
 * Rendered as a route so that a simple <Link to="/logout"> works.
 */

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import supabase from "../services/supabaseClient";

export default function Logout() {
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.signOut().finally(() => {
      navigate("/login", { replace: true });
    });
  }, [navigate]);

  // Nothing to render — redirect happens in the effect
  return null;
}
