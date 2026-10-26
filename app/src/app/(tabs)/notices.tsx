import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, type FeedItem } from "../../api";
import { CategoryTag, Chip, ErrorBox, fmtDate, Icon, styles, T } from "../../components/ui";
import { useApp } from "../../store";
import { colors, fonts } from "../../theme";

const CATS = ["전체", "장학", "공모전", "현장실습", "국제교류", "근로", "비교과", "취업", "학사"];
const SORTS = [
  { key: "latest", label: "최신순" },
  { key: "deadline", label: "마감임박순" },
  { key: "ai", label: "AI 추천순" },
] as const;
type Sort = (typeof SORTS)[number]["key"];

/** Figma 'KHURATION · 공지사항' */
export default function Notices() {
  const { call } = useApp();
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ sort?: string; category?: string }>();
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("전체");
  const [sort, setSort] = useState<Sort>("latest");
  const [items, setItems] = useState<FeedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.sort === "ai" || params.sort === "deadline" || params.sort === "latest") setSort(params.sort);
    if (params.category) setCat(params.category);
  }, [params.sort, params.category]);

  const load = useCallback(async () => {
    try {
      setError(null);
      setItems(await call(() => api.notices({ q, category: cat === "전체" ? undefined : cat, sort })));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [call, q, cat, sort]);

  useFocusEffect(
    useCallback(() => {
      const t = setTimeout(load, 250); // 검색어 입력 디바운스
      return () => clearTimeout(t);
    }, [load]),
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + 14, paddingBottom: 24 }} keyboardShouldPersistTaps="handled">
        <View style={{ paddingHorizontal: 24 }}>
          <T w="serif" s={24} lh={35}>
            공지사항
          </T>
          <T s={13} lh={19} c={colors.sub} style={{ marginTop: 4 }}>
            학과 · 단과대 · 본부 공지를 한곳에서
          </T>
          <View style={[styles.row, { height: 48, borderRadius: 14, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.white, paddingHorizontal: 14, gap: 10, marginTop: 15 }]}>
            <Icon name="search" size={20} />
            <TextInput
              value={q}
              onChangeText={setQ}
              placeholder="제목, 기관, 키워드로 검색"
              placeholderTextColor={colors.muted}
              returnKeyType="search"
              style={{ flex: 1, fontFamily: fonts.regular, fontSize: 15, color: colors.text, paddingVertical: 0 }}
            />
          </View>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 24, gap: 8, marginTop: 12 }}>
          {CATS.map((c) => (
            <Chip key={c} label={c} active={cat === c} height={40} onPress={() => setCat(c)} />
          ))}
        </ScrollView>

        <View style={{ paddingHorizontal: 24 }}>
          <View style={[styles.row, { marginTop: 18, marginBottom: 16 }]}>
            {SORTS.map((s, i) => (
              <React.Fragment key={s.key}>
                {i > 0 ? <View style={{ width: 1, height: 12, backgroundColor: colors.sortDivider, marginHorizontal: 9 }} /> : null}
                <Pressable onPress={() => setSort(s.key)} style={[styles.row, { gap: 4 }]}>
                  {sort === s.key ? <Icon name="check_14_primary" size={14} /> : null}
                  <T w={sort === s.key ? "b" : "m"} s={13} lh={19} c={sort === s.key ? colors.primary : colors.sub}>
                    {s.label}
                  </T>
                </Pressable>
              </React.Fragment>
            ))}
            <View style={{ flex: 1 }} />
            <T s={12} lh={17} c={colors.muted}>
              {items?.length ?? 0}건
            </T>
          </View>

          {error ? (
            <ErrorBox message={error} onRetry={load} />
          ) : items === null ? (
            <ActivityIndicator color={colors.primary} style={{ marginTop: 30 }} />
          ) : (
            <View style={{ backgroundColor: colors.white, borderRadius: 18, borderWidth: 1, borderColor: colors.cardBorder, overflow: "hidden" }}>
              {items.length === 0 ? (
                <T s={14} c={colors.muted} style={{ padding: 24, textAlign: "center" }}>
                  검색 결과가 없어요
                </T>
              ) : null}
              {items.map((it, i) => (
                <Pressable
                  key={it.id}
                  onPress={() => router.push(`/notice/${it.id}`)}
                  style={{ paddingHorizontal: 16, paddingVertical: 13, borderTopWidth: i ? 1 : 0, borderTopColor: colors.divider }}
                >
                  <View style={[styles.row, { gap: 6 }]}>
                    <CategoryTag label={it.category} />
                    <T s={12} lh={17} c={colors.sub} numberOfLines={1} style={{ flex: 1 }}>
                      {it.source} · {fmtDate(it.posted_date).md}
                    </T>
                    {it.d_day !== null ? (
                      <T w="b" s={12} lh={17} c={it.d_day <= 7 ? colors.primary : colors.sub}>
                        D-{it.d_day}
                      </T>
                    ) : null}
                  </View>
                  <T w="b" s={15} lh={21} style={{ marginTop: 6 }} numberOfLines={2}>
                    {it.title}
                  </T>
                </Pressable>
              ))}
            </View>
          )}
        </View>
      </ScrollView>
    </View>
  );
}
