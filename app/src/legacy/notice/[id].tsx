import { router, useLocalSearchParams } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, type NoticeDetail, type Status } from "../../api";
import { ChecklistSheet } from "../../components/ChecklistSheet";
import { Card, CategoryTag, DdayPill, ErrorBox, fmtDate, Icon, styles, T } from "../../components/ui";
import { addDeadlineToCalendar } from "../../deviceCalendar";
import { TOPIC_LABEL } from "../../profile";
import { useApp } from "../../store";
import { colors } from "../../theme";

/** Figma 'KHURATION · 공지 상세' */
export default function NoticeScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const nid = Number(id);
  const { call, profile, saved, save, unsave } = useApp();
  const insets = useSafeAreaInsets();
  const [n, setN] = useState<NoticeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sheet, setSheet] = useState(false);
  const isSaved = !!saved[nid];

  const load = useCallback(async () => {
    try {
      setError(null);
      setN(await call(() => api.notice(nid)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [call, nid]);
  useEffect(() => {
    load();
  }, [load]);

  const open = (url: string) => WebBrowser.openBrowserAsync(url).catch(() => Alert.alert("링크를 열 수 없어요", url));

  const saveToCalendar = async () => {
    if (!n) return;
    if (isSaved) return setSheet(true);
    await save({ id: n.id, title: n.title, source: n.source, category: n.category, deadline_date: n.deadline_date, url: n.url, checklist: n.checklist });
    let calMsg = "기기 캘린더에도 마감일을 추가했어요.";
    try {
      if (n.deadline_date) await addDeadlineToCalendar(n.title, n.deadline_date, n.url);
    } catch (e) {
      calMsg = `기기 캘린더 추가는 건너뛰었어요 (${e instanceof Error ? e.message : e}).`;
    }
    Alert.alert("저장했어요", `마감 3일 전·1일 전에 알려드릴게요.\n${calMsg}`);
  };

  if (error) return <View style={{ flex: 1, paddingTop: insets.top + 40 }}><ErrorBox message={error} onRetry={load} /></View>;
  if (!n) return <ActivityIndicator color={colors.primary} style={{ marginTop: insets.top + 80 }} />;

  const d = fmtDate(n.deadline_date);
  // 적합성 행: 서버 판정 + 관심 분야 일치
  const rows: { text: string; status: Status | "interest" }[] = n.reasons
    .filter((r) => r.field !== "all")
    .map((r) => ({ text: r.requirement, status: r.status }));
  const topics = n.topics.filter((t) => profile?.interests.includes(t)).map((t) => TOPIC_LABEL[t]);
  if (topics.length) rows.push({ text: `관심 분야 · ${topics.join(", ")}`, status: "interest" });
  const ok = rows.filter((r) => r.status === "match" || r.status === "interest").length;
  const s = saved[nid];

  const verdict =
    n.status === "match"
      ? { bg: colors.tint, title: `${profile?.name ?? ""} 님은 지원 대상자예요`, color: colors.primary }
      : n.status === "check"
        ? { bg: colors.warnBg, title: "지원 자격 일부는 확인이 필요해요", color: colors.warnText }
        : { bg: colors.divider, title: "지원 조건에 맞지 않아요", color: colors.sub };
  const basis = Array.from(new Set(n.reasons.map((r) => FIELD_LABEL[r.field]).filter(Boolean))).join(" · ") || "공지 조건";

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingTop: insets.top + 14, paddingBottom: 24 }}>
        <View style={[styles.row, { justifyContent: "space-between" }]}>
          <Pressable onPress={() => router.back()} hitSlop={10} style={{ marginLeft: -2 }}>
            <Icon name="back" size={24} />
          </Pressable>
          <View style={[styles.row, { gap: 22 }]}>
            <Pressable onPress={() => open(n.url)} style={[styles.row, { gap: 4 }]} hitSlop={8}>
              <Icon name="ext" size={16} />
              <T w="b" s={13} lh={19} c={colors.sub}>
                원문
              </T>
            </Pressable>
            {/* Figma에는 채워진 북마크만 있어, 저장 전에는 흐리게 표시 */}
            <Pressable onPress={() => (isSaved ? unsave(nid) : saveToCalendar())} hitSlop={8} style={{ opacity: isSaved ? 1 : 0.3 }}>
              <Icon name="bookmark_22" size={22} />
            </Pressable>
          </View>
        </View>

        <View style={[styles.row, { gap: 6, marginTop: 22 }]}>
          <CategoryTag label={n.category} />
          <T s={12} lh={17} c={colors.sub}>
            {n.source}
          </T>
        </View>
        <T w="b" s={21} lh={29.4} style={{ marginTop: 7 }}>
          {n.title}
        </T>
        <View style={[styles.row, { justifyContent: "space-between", marginTop: 12 }]}>
          <T s={13} lh={19} c={colors.sub}>
            게시 {fmtDate(n.posted_date).full.replace(/\(.\)$/, "")} · 마감 {d.full}
          </T>
          <DdayPill d={n.d_day} size="m" variant="tint" />
        </View>

        <View style={[styles.row, { backgroundColor: verdict.bg, borderRadius: 16, padding: 16, gap: 12, marginTop: 16 }]}>
          <View
            style={{
              width: 36,
              height: 36,
              borderRadius: 18,
              backgroundColor: n.status === "match" ? colors.primary : colors.white,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name={n.status === "match" ? "check_20_white" : "warn"} size={20} />
          </View>
          <View style={{ flex: 1 }}>
            <T w="b" s={15} lh={21} c={verdict.color}>
              {verdict.title}
            </T>
            <T s={12} lh={17} c={colors.sub}>
              {basis}을 기준으로 확인했어요
            </T>
          </View>
        </View>

        <Card style={{ padding: 17, marginTop: 12 }}>
          <View style={[styles.row, { gap: 6 }]}>
            <Icon name="ai_18_primary" size={18} />
            <T w="b" s={15} lh={21}>
              AI 요약
            </T>
          </View>
          <View style={{ gap: 7, marginTop: 10 }}>
            {n.summary_points.map((p, i) => (
              <View key={i} style={[styles.row, { gap: 8, alignItems: "flex-start" }]}>
                <View style={{ width: 5, height: 5, borderRadius: 3, backgroundColor: colors.primary, marginTop: 8 }} />
                <T s={14} lh={20} style={{ flex: 1 }}>
                  {p}
                </T>
              </View>
            ))}
          </View>
        </Card>

        <Card style={{ padding: 17, marginTop: 12 }}>
          <View style={[styles.row, { justifyContent: "space-between" }]}>
            <T w="b" s={15} lh={21}>
              나와의 적합성
            </T>
            <T s={12} lh={17} c={colors.sub}>
              {rows.length}개 중 {ok}개 충족
            </T>
          </View>
          <View style={{ gap: 12, marginTop: 13 }}>
            {rows.map((r, i) => (
              <View key={i} style={[styles.row, { gap: 8 }]}>
                <Icon name={r.status === "match" || r.status === "interest" ? "ok_circle" : "warn"} size={20} />
                <T s={14} lh={20} style={{ flex: 1 }}>
                  {r.text}
                </T>
                {r.status === "check" ? (
                  <View style={{ backgroundColor: colors.warnBg, borderRadius: 11, height: 22, paddingHorizontal: 8, justifyContent: "center" }}>
                    <T w="b" s={12} lh={17} c={colors.warnText}>
                      확인 필요
                    </T>
                  </View>
                ) : (
                  <T w="b" s={12} lh={17} c={r.status === "mismatch" ? colors.muted : colors.primary}>
                    {r.status === "match" ? "충족" : r.status === "interest" ? "일치" : "미충족"}
                  </T>
                )}
              </View>
            ))}
            {rows.length === 0 ? (
              <T s={14} c={colors.sub}>
                별도 지원 조건이 없어요
              </T>
            ) : null}
          </View>
        </Card>

        {n.checklist.length ? (
          <Pressable onPress={() => (isSaved ? setSheet(true) : saveToCalendar())}>
            <Card style={[styles.row, { paddingHorizontal: 17, height: 56, marginTop: 12, gap: 10 }]}>
              <Icon name="list" size={22} />
              <T w="b" s={15} lh={21} style={{ flex: 1 }}>
                신청 체크리스트
              </T>
              <T s={13} lh={19} c={colors.sub}>
                {n.checklist.length}개 중 {s?.done.length ?? 0}개 완료
              </T>
              <Icon name="right_18" size={18} />
            </Card>
          </Pressable>
        ) : null}
      </ScrollView>

      <View style={[styles.row, { gap: 10, paddingHorizontal: 24, paddingTop: 13, paddingBottom: insets.bottom + 16, backgroundColor: colors.white, borderTopWidth: 1, borderTopColor: colors.cardBorder }]}>
        <Pressable onPress={saveToCalendar} style={[styles.outlineBtn, styles.row, { flex: 1, height: 52, gap: 6 }]}>
          <Icon name="cal_18_primary" size={18} />
          <T w="b" s={15} lh={21} c={colors.primary}>
            {isSaved ? "저장됨 · 준비하기" : "캘린더에 저장"}
          </T>
        </Pressable>
        <Pressable onPress={() => open(n.apply_url)} style={{ flex: 1, height: 52, borderRadius: 14, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}>
          <T w="b" s={15} lh={21} c={colors.white}>
            신청하기
          </T>
        </Pressable>
      </View>

      <ChecklistSheet noticeId={sheet ? nid : null} dDay={n.d_day} onClose={() => setSheet(false)} />
    </View>
  );
}

const FIELD_LABEL: Record<string, string> = {
  campus: "캠퍼스",
  dept: "학과",
  grade: "학년",
  gpa: "학점",
  credits: "이수 학점",
  income: "소득분위",
  lang: "어학",
};
