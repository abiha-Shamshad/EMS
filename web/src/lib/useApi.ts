"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, get, post } from "./api";

type Query = Record<string, string | number | boolean | null | undefined>;
export type Loadable<T> = { data: T | undefined; error: ApiError | undefined; loading: boolean; reload: () => void };
type Result<T> = { key: string; data: T | undefined; error: ApiError | undefined };

/** Shared request state: state changes only in request callbacks; `loading` is "the latest request has not answered yet".
 *  The previous data stays visible while a reload or a new filter is loading. */
function useRequest<T>(key: string | null, run: (signal: AbortSignal) => Promise<T>): Loadable<T> {
  const [result, setResult] = useState<Result<T>>();
  const [tick, setTick] = useState(0);
  const runRef = useRef(run);
  useEffect(() => {
    runRef.current = run;
  });
  const full = key === null ? null : `${key}#${tick}`;

  useEffect(() => {
    if (full === null) return;
    const ctrl = new AbortController();
    runRef.current(ctrl.signal)
      .then((data) => setResult({ key: full, data, error: undefined }))
      .catch((e: unknown) => {
        if ((e as Error).name !== "AbortError") setResult((prev) => ({ key: full, data: prev?.data, error: e as ApiError }));
      });
    return () => ctrl.abort();
  }, [full]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data: result?.data, error: result?.error, loading: full !== null && result?.key !== full, reload };
}

/** GET a path and keep it in state. `path = null` skips the request (e.g. until the user may see it). */
export function useApi<T>(path: string | null, query?: Query): Loadable<T> {
  const queryJson = JSON.stringify(query ?? {});
  return useRequest<T>(path === null ? null : `GET ${path}?${queryJson}`, (signal) => get<T>(path!, JSON.parse(queryJson) as Query, signal));
}

/** A read-only POST kept in state (contact search, API-046, carries the search text in the body, not the URL). */
export function usePost<T>(path: string | null, body: unknown): Loadable<T> {
  const json = JSON.stringify(body ?? {});
  return useRequest<T>(path === null ? null : `POST ${path} ${json}`, () => post<T>(path!, JSON.parse(json)));
}

/** Re-run `fn` every `ms` while the tab is visible (live grid, notifications badge). */
export function usePoll(fn: () => void, ms: number): void {
  const ref = useRef(fn);
  useEffect(() => {
    ref.current = fn;
  });
  useEffect(() => {
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") ref.current();
    }, ms);
    return () => window.clearInterval(id);
  }, [ms]);
}
