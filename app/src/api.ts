import { API_BASE_URL } from "./config";

export type Status = "match" | "check" | "mismatch";

export interface Reason {
  field: string;
  status: Status;
  requirement: string;
  note: string;
}

export interface FeedItem {
  id: number;
  title: string;
  source: string;
  category: string;
  summary: string;
  url: string;
  posted_date: string | null;
  deadline_date: string | null;
  d_day: number | null;
  status: Status;
  reasons: Reason[];
  interest_score: number;
  topics: string[];
}

export interface NoticeDetail extends FeedItem {
  requirements: string[];
  summary_points: string[];
  checklist: string[];
  apply_url: string;
}

export interface ChatOut {
  answer: string;
  keywords: string[];
  items: FeedItem[];
  sources: string[];
  engine: string;
}

/** 서버로 보내는 익명 태그. 이름·학번·정확한 학점은 절대 넣지 않는다. */
export interface Tags {
  campus?: "seoul" | "global";
  college?: string;
  dept?: string;
  grade?: number;
  gpa_floor?: number;
  last_gpa_floor?: number;
  credits_floor?: number;
  income_band?: number;
  interests: string[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let deviceToken: string | null = null;
export function setDeviceToken(t: string | null) {
  deviceToken = t;
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const ctrl = new AbortController();
  // 무료 배포 서버는 잠들었다 깨면 30~60초 걸릴 수 있다
  const timer = setTimeout(() => ctrl.abort(), 60000);
  try {
    const res = await fetch(API_BASE_URL + path, {
      ...init,
      signal: ctrl.signal,
      headers: {
        "Content-Type": "application/json",
        ...(deviceToken ? { "X-Device-Token": deviceToken } : {}),
        ...(init.headers ?? {}),
      },
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(0, `서버(${API_BASE_URL})에 연결할 수 없어요`);
  } finally {
    clearTimeout(timer);
  }
}

const qs = (o: Record<string, string | number | boolean | undefined>) => {
  const s = Object.entries(o)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");
  return s ? `?${s}` : "";
};

export const api = {
  health: () => req<{ ok: boolean; mode: string }>("/health"),
  registerDevice: (push_token: string, tags: Tags) =>
    req<{ id: number }>("/devices", { method: "POST", body: JSON.stringify({ push_token, tags }) }),
  setIntent: (text: string) =>
    req<{ keywords: string[] }>("/devices/intent", { method: "POST", body: JSON.stringify({ text }) }),
  deleteDevice: () => req<{ deleted: boolean }>("/devices", { method: "DELETE" }),
  feed: (includeMismatch = false) => req<FeedItem[]>(`/feed${qs({ include_mismatch: includeMismatch })}`),
  notices: (o: { q?: string; category?: string; sort?: "latest" | "deadline" | "ai" }) =>
    req<FeedItem[]>(`/notices${qs(o)}`),
  notice: (id: number) => req<NoticeDetail>(`/notices/${id}`),
  chat: (message: string) => req<ChatOut>("/ai/chat", { method: "POST", body: JSON.stringify({ message }) }),
  demo: {
    advance: (days: number) =>
      req<{ offset_days: number }>("/demo/advance-clock", { method: "POST", body: JSON.stringify({ days }) }),
    reset: () => req<{ offset_days: number }>("/demo/reset-clock", { method: "POST" }),
    reseed: () => req<{ loaded: number }>("/demo/reseed", { method: "POST" }),
    firePush: (kind: "new" | "d3" | "changed") =>
      req<{ sent: boolean; reason?: string }>("/demo/fire-push", {
        method: "POST",
        body: JSON.stringify({ kind }),
      }),
  },
};
