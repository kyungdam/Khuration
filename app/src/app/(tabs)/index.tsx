import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, type FeedItem } from "../../api";
import { DateBox, highlightLine, reasonText } from "../../components/NoticeBits";
import { Card, DdayPill, ErrorBox, Icon, styles, T, Toggle } from "../../components/ui";
import { profileLine } from "../../profile";
import { useApp } from "../../store";
import { colors } from "../../theme";

type Tab = "ai" | "deadline";

/** Figma 'AI 맞춤 공지' + '마감 임박 공지' */
export default function Home() {
  const { profile, call } = useApp();
  const insets = useSafeAreaInsets();
  const [tab, setTab] = useState<Tab>("ai");
  const [onlyEligible, setOnlyEligible] = useState(true);
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      setItems(await call(() => api.feed(!onlyEligible)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [call, onlyEligible]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const eligible = (items ?? []).filter((i) => i.status !== "mismatch");
  const top = eligible.find((i) => i.status === "match") ?? eligible[0];
  const rest = eligible.filter((i) => i !== top).slice(0, 6);
  const urgent = [...(items ?? [])].filter((i) => i.d_day !== null).sort((a, b) => (a.d_day ?? 0) - (b.d_day ?? 0));
  const badge = eligible.filter((i) => i.d_day !== null && i.d_day <= 7).length;

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView
        contentContainerStyle={{ paddingHorizontal: 24, paddingTop: insets.top + 14, paddingBottom: 24 }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={async () => {
              setRefreshing(true);
              await load();
              setRefreshing(false);
            }}
          />
        }
      >
        {/* Home header */}
        <View style={[styles.row, { justifyContent: "space-between" }]}>
          <View style={[styles.row, { gap: 3 }]}>
            <T w="serif" s={19} lh={27} c={colors.primary}>
              KHU
            </T>
            <T w="serif" s={19} lh={27}>
              RATION
            </T>
          </View>
          <View style={[styles.row, { gap: 22 }]}>
            <Pressable onPress={() => setTab("deadline")} hitSlop={8}>
              <Icon name="bell" size={24} />
              {badge > 0 ? (
                <View
                  style={{
                    position: "absolute",
                    left: 10,
                    top: -3,
                    width: 18,
                    height: 18,
                    borderRadius: 9,
                    backgroundColor: colors.primary,
                    borderWidth: 2,
                    borderColor: colors.bg,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <T w="b" s={10} lh={13} c={colors.white}>
                    {badge > 9 ? "9+" : badge}
                  </T>
                </View>
              ) : null}
            </Pressable>
            <Pressable onPress={() => router.push("/settings")} hitSlop={8}>
              <Icon name="gear" size={24} />
            </Pressable>
          </View>
        </View>

        <View style={[styles.row, { gap: 12, marginTop: 20 }]}>
          <View style={{ width: 48, height: 48, borderRadius: 24, backgroundColor: colors.tint, alignItems: "center", justifyContent: "center" }}>
            <T w="b" s={17} lh={25} c={colors.primary}>
              {profile?.name.slice(0, 1) ?? ""}
            </T>
          </View>
          <View style={{ flex: 1 }}>
            <T s={12} lh={17} c={colors.sub}>
              {profileLine(profile)}
            </T>
            <T w="b" s={18} lh={26} numberOfLines={1}>
              {tab === "ai" ? `${profile?.name ?? ""} 님, 오늘의 추천이에요` : "이번 주 마감, 놓치지 마세요"}
            </T>
          </View>
        </View>

        {/* Segment */}
        <View style={[styles.row, { backgroundColor: colors.segment, borderRadius: 14, height: 52, padding: 4, marginTop: 14 }]}>
          <SegmentBtn active={tab === "ai"} onPress={() => setTab("ai")} label="AI 맞춤 공지" icon={<Icon name={tab === "ai" ? "ai_16_white" : "ai_16_gray"} size={16} />} />
          <SegmentBtn active={tab === "deadline"} onPress={() => setTab("deadline")} label="마감 임박 공지" icon={<ClockIcon active={tab === "deadline"} />} />
        </View>

        {error ? (
          <ErrorBox message={error} onRetry={load} />
        ) : items === null ? (
          <ActivityIndicator color={colors.primary} style={{ marginTop: 40 }} />
        ) : tab === "ai" ? (
          <>
            {top ? (
              <Pressable onPress={() => router.push(`/notice/${top.id}`)} style={{ backgroundColor: colors.primary, borderRadius: 20, padding: 18, marginTop: 14 }}>
                <View style={[styles.row, { justifyContent: "space-between" }]}>
                  <View style={[styles.row, { gap: 5 }]}>
                    <Icon name="ai_14_gold" size={14} />
                    <T w="b" s={12} lh={17} c={colors.goldLight}>
                      AI 추천 1순위
                    </T>
                  </View>
                  <DdayPill d={top.d_day} size="m" variant="white" />
                </View>
                <T s={12} lh={17} c={colors.onPrimarySub} style={{ marginTop: 10 }}>
                  {top.source} · {top.category}
                </T>
                <T w="b" s={18} lh={25} c={colors.white} style={{ marginTop: 3 }}>
                  {top.title}
                </T>
                <View style={{ backgroundColor: "rgba(255,255,255,0.12)", borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, marginTop: 12 }}>
                  <T s={13} lh={19.5} c={colors.white}>
                    <T w="b" s={13} lh={19.5} c={colors.goldLight}>
                      추천 이유{"  "}
                    </T>
                    {reasonText(top, profile)}
                  </T>
                </View>
              </Pressable>
            ) : (
              <Empty text="지금 조건에 맞는 공지가 없어요" />
            )}

            <View style={[styles.row, { justifyContent: "space-between", marginTop: 16, marginBottom: 10 }]}>
              <T w="b" s={16} lh={24}>
                나에게 맞는 공지
              </T>
              <Pressable onPress={() => router.navigate({ pathname: "/notices", params: { sort: "ai" } })} style={[styles.row, { gap: 3 }]}>
                <T s={13} lh={19} c={colors.sub}>
                  전체 보기
                </T>
                <Icon name="right_16" size={16} />
              </Pressable>
            </View>
            <View style={{ gap: 10 }}>
              {rest.map((it) => {
                const h = highlightLine(it, profile);
                return (
                  <Pressable key={it.id} onPress={() => router.push(`/notice/${it.id}`)}>
                    <Card style={{ paddingHorizontal: 17, paddingVertical: 15 }}>
                      <View style={[styles.row, { gap: 8 }]}>
                        <DdayPill d={it.d_day} />
                        <T s={12} lh={17} c={colors.sub} numberOfLines={1} style={{ flex: 1 }}>
                          {it.source} · {it.category}
                        </T>
                      </View>
                      <T w="b" s={15} lh={21} style={{ marginTop: 4 }} numberOfLines={2}>
                        {it.title}
                      </T>
                      <View style={[styles.row, { gap: 4, marginTop: 4 }]}>
                        {h.warn ? <Icon name="warn" size={12} /> : <Icon name="ai_12_primary" size={12} />}
                        <T w="m" s={12} lh={17} c={h.warn ? colors.warnText : colors.primary} numberOfLines={1} style={{ flex: 1 }}>
                          {h.text}
                        </T>
                      </View>
                    </Card>
                  </Pressable>
                );
              })}
            </View>
          </>
        ) : (
          <>
            <View style={[styles.row, { justifyContent: "space-between", marginTop: 20, marginBottom: 17 }]}>
              <T w="b" s={14} lh={20}>
                마감이 가까운 순
              </T>
              <View style={[styles.row, { gap: 9 }]}>
                <T s={13} lh={19} c={colors.sub}>
                  지원 가능한 공지만
                </T>
                <Toggle value={onlyEligible} onChange={setOnlyEligible} />
              </View>
            </View>
            <View style={{ gap: 10 }}>
              {urgent.map((it) => (
                <Pressable key={it.id} onPress={() => router.push(`/notice/${it.id}`)}>
                  <Card style={[styles.row, { padding: 13, gap: 14, opacity: it.status === "mismatch" ? 0.55 : 1 }]}>
                    <DateBox d={it.d_day} date={it.deadline_date} />
                    <View style={{ flex: 1 }}>
                      <T s={12} lh={17} c={colors.sub} numberOfLines={1}>
                        {it.source} · {it.category}
                        {it.status === "mismatch" ? " · 지원 불가" : ""}
                      </T>
                      <T w="b" s={15} lh={21} numberOfLines={2} style={{ marginTop: 3 }}>
                        {it.title}
                      </T>
                    </View>
                    <Icon name="right_18" size={18} />
                  </Card>
                </Pressable>
              ))}
              {urgent.length === 0 ? <Empty text="마감이 다가오는 공지가 없어요" /> : null}
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
}

function SegmentBtn({ active, onPress, label, icon }: { active: boolean; onPress: () => void; label: string; icon: React.ReactNode }) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.row, { flex: 1, height: 44, borderRadius: 10, justifyContent: "center", gap: 6, backgroundColor: active ? colors.primary : "transparent" }]}
    >
      {icon}
      <T w="b" s={14} lh={20} c={active ? colors.white : colors.sub}>
        {label}
      </T>
    </Pressable>
  );
}

/** 비활성 시계 아이콘은 Figma에서 테두리+바늘 두 조각으로 나뉘어 있어 겹쳐 그린다 */
function ClockIcon({ active }: { active: boolean }) {
  if (active) return <Icon name="clock_white" size={16} />;
  return (
    <View style={{ width: 16, height: 16 }}>
      <Icon name="clock_outline_gray" size={12} style={{ position: "absolute", left: 2, top: 2 }} />
      <Icon name="clock_glyph_gray" w={3.2} h={5.87} style={{ position: "absolute", left: 7.4, top: 4.07 }} />
    </View>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <Card style={{ padding: 24, alignItems: "center", marginTop: 14 }}>
      <T s={14} c={colors.muted}>
        {text}
      </T>
    </Card>
  );
}
