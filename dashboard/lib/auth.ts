export const getAuthToken = (): string | null => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("saiss_token");
};

export const setAuthToken = (token: string) => {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem("saiss_token", token);
};

export const clearAuthToken = () => {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem("saiss_token");
};

export const getAuthHeaders = (): Record<string, string> => {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "ngrok-skip-browser-warning": "true"
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
};
