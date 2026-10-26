import AsyncStorage from "@react-native-async-storage/async-storage";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError, type ChatOut, setDeviceToken } from "./api";
import { type Profile, profileToTags } from "./profile";
import { cancelReminders, getDeviceToken, scheduleDeadlineReminders } from "./push";

/** 캘린더에 저장한 공지 (기기에만 저장) */
export interface Saved {
  id: number;
  title: string;
  source: string;
  category: string;
  deadline_date: string | null;
  url: string;
  checklist: string[];
  done: number[];
  remind: boolean;
  notifIds: string[];
}

export interface ChatMsg {
  role: "user" | "ai";
  text: string;
  result?: ChatOut;
}
export interface ChatThread {
  id: string;
  title: string;
  createdAt: number;
  messages: ChatMsg[];
}

interface Persisted {
  profile: Profile | null;
  token: string | null;
  saved: Record<number, Saved>;
  chats: ChatThread[];
}

const KEY = "khuration_state_v1";
const initial: Persisted = { profile: null, token: null, saved: {}, chats: [] };

interface Ctx extends Persisted {
  ready: boolean;
  /** 프로필 저장 + 서버에 익명 태그 등록 */
  register: (p: Profile) => Promise<void>;
  /** API 호출. 서버 DB가 초기화돼 기기를 모르면 자동 재등록 후 1회 재시도 */
  call: <T>(fn: () => Promise<T>) => Promise<T>;
  save: (s: Omit<Saved, "done" | "remind" | "notifIds">) => Promise<void>;
  unsave: (id: number) => Promise<void>;
  toggleDone: (id: number, idx: number) => void;
  setRemind: (id: number, on: boolean) => Promise<void>;
  upsertChat: (t: ChatThread) => void;
  reset: () => Promise<void>;
}

const AppContext = createContext<Ctx | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<Persisted>(initial);
  const [ready, setReady] = useState(false);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        if (!raw) return;
        const s = { ...initial, ...(JSON.parse(raw) as Persisted) };
        setDeviceToken(s.token);
        setState(s);
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  const update = useCallback((fn: (s: Persisted) => Persisted) => {
    setState((prev) => {
      const next = fn(prev);
      AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, []);

  const register = useCallback(
    async (p: Profile) => {
      const token = await getDeviceToken();
      setDeviceToken(token);
      await api.registerDevice(token, profileToTags(p));
      if (p.intentText.trim()) await api.setIntent(p.intentText.trim());
      update((s) => ({ ...s, profile: p, token }));
    },
    [update],
  );

  const call = useCallback(
    async <T,>(fn: () => Promise<T>): Promise<T> => {
      try {
        return await fn();
      } catch (e) {
        const p = stateRef.current.profile;
        if (e instanceof ApiError && (e.status === 404 || e.status === 401) && p) {
          await register(p);
          return await fn();
        }
        throw e;
      }
    },
    [register],
  );

  const save: Ctx["save"] = useCallback(
    async (n) => {
      const notifIds = await scheduleDeadlineReminders(n.id, n.title, n.deadline_date).catch(() => []);
      update((s) => ({ ...s, saved: { ...s.saved, [n.id]: { ...n, done: s.saved[n.id]?.done ?? [], remind: true, notifIds } } }));
    },
    [update],
  );

  const unsave = useCallback(
    async (id: number) => {
      const cur = stateRef.current.saved[id];
      if (cur) await cancelReminders(cur.notifIds);
      update((s) => {
        const { [id]: _, ...rest } = s.saved;
        return { ...s, saved: rest };
      });
    },
    [update],
  );

  const toggleDone = useCallback(
    (id: number, idx: number) =>
      update((s) => {
        const cur = s.saved[id];
        if (!cur) return s;
        const done = cur.done.includes(idx) ? cur.done.filter((i) => i !== idx) : [...cur.done, idx];
        return { ...s, saved: { ...s.saved, [id]: { ...cur, done } } };
      }),
    [update],
  );

  const setRemind = useCallback(
    async (id: number, on: boolean) => {
      const cur = stateRef.current.saved[id];
      if (!cur) return;
      await cancelReminders(cur.notifIds);
      const notifIds = on ? await scheduleDeadlineReminders(id, cur.title, cur.deadline_date).catch(() => []) : [];
      update((s) => ({ ...s, saved: { ...s.saved, [id]: { ...s.saved[id], remind: on, notifIds } } }));
    },
    [update],
  );

  const upsertChat = useCallback(
    (t: ChatThread) => update((s) => ({ ...s, chats: [t, ...s.chats.filter((c) => c.id !== t.id)].slice(0, 30) })),
    [update],
  );

  const reset = useCallback(async () => {
    await Promise.all(Object.values(stateRef.current.saved).map((s) => cancelReminders(s.notifIds)));
    await AsyncStorage.multiRemove([KEY, "device_token"]);
    setDeviceToken(null);
    setState(initial);
  }, []);

  const value = useMemo<Ctx>(
    () => ({ ...state, ready, register, call, save, unsave, toggleDone, setRemind, upsertChat, reset }),
    [state, ready, register, call, save, unsave, toggleDone, setRemind, upsertChat, reset],
  );
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("AppProvider 밖에서 useApp 사용");
  return ctx;
}
