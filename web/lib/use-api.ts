"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, apiRequest } from "./api-client";

export type ApiState<T> = {
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
  reload: () => void;
  setData: (data: T) => void;
};

/** Fetch a GET endpoint on mount and whenever `path` changes. Pass null to skip. */
export function useApi<T>(path: string | null): ApiState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<ApiError>();
  const [loading, setLoading] = useState(path !== null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let active = true;
    setLoading(true);
    setError(undefined);
    apiRequest<T>(path)
      .then((result) => active && setData(result))
      .catch((caught: ApiError) => active && setError(caught))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [path, version]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);
  return { data, error, loading, reload, setData };
}
