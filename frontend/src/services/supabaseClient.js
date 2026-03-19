/**
 * supabaseClient.js
 * Initialises and exports a shared Supabase client instance.
 * Credentials are read from environment variables so they are never hard-coded.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing Supabase environment variables (REACT_APP_SUPABASE_URL and " +
      "REACT_APP_SUPABASE_ANON_KEY). " +
      "Please copy .env.example to .env and fill in the values."
  );
}

const supabase = createClient(supabaseUrl, supabaseAnonKey);

export default supabase;
