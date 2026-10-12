"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { ApiError, get, post, selectOrg } from "./api";
import type { Me, Permission } from "./types";

type Session = {
  me: Me;
  can: (p: Permission) => boolean;
  refresh: () => void;
  signOut: () => Promise<void>;
  timeZone: string;
};

const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const s = useContext(SessionContext);
  if (!s) throw new Error("useSession outside <SessionProvider>");
  return s;
}

/** Loads /me (API-009) and guards the signed-in area: no session -> /login; several companies -> /select-company. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let live = true;
    get<Me>("/me")
      .then((m) => {
        if (!live) return;
        setMe(m);
        setError(null);
      })
      .catch((e: ApiError) => {
        if (!live) return;
        if (e.code === "AUTHENTICATION_REQUIRED") router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
        else if (e.code === "ORG_NOT_SELECTED") router.replace("/select-company");
        else {
          if (e.code === "MEMBER_DEACTIVATED") selectOrg(null);
          setError(e);
        }
      });
    return () => {
      live = false;
    };
  }, [router, tick]);

  const refresh = useCallback(() => setTick((t) => t + 1), []);
  const signOut = useCallback(async () => {
    try {
      await post("/auth/logout");
    } finally {
      selectOrg(null);
      router.replace("/login");
    }
  }, [router]);

  if (error) {
    return (
      <div className="center-page">
        <div className="card narrow">
          <h1 className="h2">{error.code === "MEMBER_DEACTIVATED" ? "Access removed" : "EMS is unavailable"}</h1>
          <p className="muted">{error.message}</p>
          <div className="row gap" style={{ marginTop: 14 }}>
            <button className="btn" onClick={refresh}>Try again</button>
            <button className="btn ghost" onClick={() => void signOut()}>Sign out</button>
          </div>
        </div>
      </div>
    );
  }
  if (!me) return <div className="center-page"><div className="spinner" aria-label="Loading" /></div>;

  const value: Session = { me, can: (p) => me.permissions.includes(p), refresh, signOut, timeZone: me.active_org.time_zone };
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
