"use client";

import { createContext, useContext } from "react";

export const AuthContext = createContext<{ accessToken: string } | null>(null);

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("Chat must be inside an authenticated session.");
  return auth;
}
