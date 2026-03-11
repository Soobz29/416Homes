const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Alert {
  id: string;
  min_price?: number | null;
  max_price?: number | null;
  min_beds?: number | null;
  property_types?: string[] | null;
  neighbourhoods?: string[] | null;
  cities?: string[] | null;
  keywords?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface AlertPayload {
  min_price?: number;
  max_price?: number;
  min_beds?: number;
  property_types?: string[];
  neighbourhoods?: string[];
  cities?: string[];
  keywords?: string;
  is_active?: boolean;
}

async function requestAlerts<T>(
  path: string,
  options: RequestInit & { email: string },
): Promise<T> {
  const { email, ...init } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "x-user-email": email,
      ...(init.headers || {}),
    },
  });

  if (!res.ok) {
    let msg = `Alerts API failed: ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) msg = typeof body.detail === "string" ? body.detail : msg;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function fetchAlerts(email: string): Promise<Alert[]> {
  return requestAlerts<Alert[]>("/api/alerts", {
    method: "GET",
    email,
  });
}

export async function createAlert(
  email: string,
  payload: AlertPayload,
): Promise<Alert> {
  return requestAlerts<Alert>("/api/alerts", {
    method: "POST",
    body: JSON.stringify(payload),
    email,
  });
}

export async function updateAlert(
  email: string,
  id: string,
  payload: AlertPayload,
): Promise<Alert> {
  return requestAlerts<Alert>(`/api/alerts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
    email,
  });
}

export async function deleteAlert(email: string, id: string): Promise<void> {
  await requestAlerts<void>(`/api/alerts/${id}`, {
    method: "DELETE",
    email,
  });
}

export async function generateLinkCode(
  email: string,
): Promise<{ code: string; expires_at?: string }> {
  return requestAlerts<{ code: string; expires_at?: string }>("/api/link-code", {
    method: "POST",
    email,
  });
}

export interface MeResponse {
  id: string;
  email: string | null;
  telegram_chat_id: number | null;
  telegram_username: string | null;
}

export async function fetchMe(email: string): Promise<MeResponse> {
  return requestAlerts<MeResponse>("/api/me", {
    method: "GET",
    email,
  });
}


