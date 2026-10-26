import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, type FeedItem } from "../../api";
import { ChecklistSheet } from "../../components/ChecklistSheet";
import { DateBox } from "../../components/NoticeBits";
import { Card, ErrorBox, fmtDate, Icon, styles, T } from "../../components/ui";
import { useApp } from "../../store";
import { colors } from "../../theme";

const WEEK = ["월", "화", "수", "목", "금", "토", "일"];
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

interface Ev {
  id: number;
  title: string;
  category: string;
  date: string;
  d_day: number | null;
}

/** Figma 'KHURATION · 월간 캘린더' — 맞춤 공지 + 저장한 공지의 마감일 */
export default function CalendarScreen() {
  const { call, saved } = useApp();
  const insets = useSafeAreaInsets();
  const today = new Date();
  const [month, setMonth] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sheet, setSheet] = useState<{ id: number; d: number | null } | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setFeed(await call(() => api.feed(false)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [call]);
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const events = useMemo(() => {
    const m = new Map<number, Ev>();
    for (const f of feed) if (f.deadline_date) m.set(f.id, { id: f.id, title: f.title, category: f.category, date: f.deadline_date, d_day: f.d_day });
    for (const s of Object.values(saved))
      if (s.deadline_date && !m.has(s.id)) {
        const [y, mo, d] = s.deadline_date.split("-").map(Number);
        const dd = Math.round((new Date(y, mo - 1, d).getTime() - new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()) / 86400000);
        m.set(s.id, { id: s.id, title: s.title, category: s.category, date: s.deadline_date, d_day: dd });
      }
    return [...m.values()].filter((e) => e.d_day === null || e.d_day >= 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feed, saved]);

  const byDate = useMemo(() => {
    const m: Record<string, Ev[]> = {};
    for (const e of events) (m[e.date] ??= []).push(e);
    return m;
  }, [events]);

  // 월요일 시작 그리드
  const start = new Date(month);
  start.setDate(1 - ((month.getDay() + 6) % 7));
  const lastDay = new Date(month.getFullYear(), month.getMonth() + 1, 0);
  const cells: Date[] = [];
  for (let d = new Date(start); cells.length < 42; d.setDate(d.getDate() + 1)) {
    cells.push(new Date(d));
    if (cells.length % 7 === 0 && d >= lastDay) break;
  }
  const weeks = Array.from({ length: cells.length / 7 }, (_, i) => cells.slice(i * 7, i * 7 + 7));
  const todayIso = iso(today);
  const upcoming = [...events].sort((a, b) => (a.d_day ?? 999) - (b.d_day ?? 999)).slice(0, 3);

  const openEvent = (e: Ev) => (saved[e.id]?.checklist.length ? setSheet({ id: e.id, d: e.d_day }) : router.push(`/notice/${e.id}`));

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingTop: insets.top + 22, paddingBottom: 24 }}>
        <View style={[styles.row, { justifyContent: "space-between" }]}>
          <T w="serif" s={22} lh={32}>
            {month.getFullYear()}년 {month.getMonth() + 1}월
          </T>
          <View style={[styles.row, { gap: 26 }]}>
            <Pressable hitSlop={10} onPress={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>
              <Icon name="cal_prev" size={22} />
            </Pressable>
            <Pressable hitSlop={10} onPress={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>
              <Icon name="cal_next" size={22} />
            </Pressable>
          </View>
        </View>

        <Card style={{ borderRadius: 18, paddingHorizontal: 7, paddingTop: 11, paddingBottom: 6, marginTop: 18 }}>
          <View style={styles.row}>
            {WEEK.map((w, i) => (
              <T key={w} w="b" s={12} lh={17} c={i === 6 ? colors.primary : colors.muted} style={{ flex: 1, textAlign: "center" }}>
                {w}
              </T>
            ))}
          </View>
          {weeks.map((wk, wi) => (
            <View key={wi} style={[styles.row, { height: 54, alignItems: "flex-start", paddingTop: 7 }]}>
              {wk.map((day, di) => {
                const key = iso(day);
                const inMonth = day.getMonth() === month.getMonth();
                const isToday = key === todayIso;
                const ev = byDate[key]?.[0];
                return (
                  <Pressable key={key} disabled={!ev} onPress={() => ev && openEvent(ev)} style={{ flex: 1, alignItems: "center" }}>
                    <View style={{ width: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: isToday ? colors.primary : "transparent" }}>
                      <T
                        w={isToday ? "b" : inMonth ? "m" : "r"}
                        s={13}
                        lh={19}
                        c={isToday ? colors.white : !inMonth ? colors.dateMuted : di === 6 ? colors.primary : colors.text}
                      >
                        {day.getDate()}
                      </T>
                    </View>
                    {isToday && !ev ? (
                      <T w="b" s={10} lh={15} c={colors.primary}>
                        오늘
                      </T>
                    ) : ev ? (
                      <View style={{ height: 16, borderRadius: 4, paddingHorizontal: 3, marginTop: 2, justifyContent: "center", backgroundColor: ev.d_day !== null && ev.d_day <= 7 ? colors.primary : colors.tint }}>
                        <T w="b" s={10} lh={15} c={ev.d_day !== null && ev.d_day <= 7 ? colors.white : colors.primary} numberOfLines={1}>
                          {ev.category}
                          {byDate[key].length > 1 ? `+${byDate[key].length - 1}` : ""}
                        </T>
                      </View>
                    ) : null}
                  </Pressable>
                );
              })}
            </View>
          ))}
        </Card>

        <View style={[styles.row, { justifyContent: "space-between", marginTop: 18, marginBottom: 10 }]}>
          <T w="b" s={16} lh={24}>
            다가오는 마감
          </T>
          <Pressable onPress={() => router.navigate({ pathname: "/notices", params: { sort: "deadline" } })} style={[styles.row, { gap: 3 }]}>
            <T s={13} lh={19} c={colors.sub}>
              전체 보기
            </T>
            <Icon name="right_16" size={16} />
          </Pressable>
        </View>
        {error ? <ErrorBox message={error} onRetry={load} /> : null}
        <View style={{ gap: 8 }}>
          {upcoming.map((e) => {
            const s = saved[e.id];
            const { md, wd } = fmtDate(e.date);
            return (
              <Pressable key={e.id} onPress={() => openEvent(e)}>
                <Card style={[styles.row, { borderRadius: 14, padding: 8, gap: 12 }]}>
                  <DateBox d={e.d_day} date={e.date} size={44} />
                  <View style={{ flex: 1 }}>
                    <T w="b" s={14} lh={20} numberOfLines={1}>
                      {e.title}
                    </T>
                    <T s={12} lh={17} c={colors.sub}>
                      {md} ({wd}) · {e.category}
                    </T>
                  </View>
                  {s?.checklist.length ? (
                    <View style={{ backgroundColor: colors.tint, borderRadius: 12, height: 24, paddingHorizontal: 8, justifyContent: "center", marginRight: 4 }}>
                      <T w="b" s={12} lh={17} c={colors.primary}>
                        준비 {s.done.length}/{s.checklist.length}
                      </T>
                    </View>
                  ) : null}
                </Card>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>
      <ChecklistSheet noticeId={sheet?.id ?? null} dDay={sheet?.d ?? null} onClose={() => setSheet(null)} />
    </View>
  );
}
