import { router } from "expo-router";
import React, { useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, type ChatOut } from "../api";
import { Icon, styles, T, DdayPill } from "../components/ui";
import { TOPIC_LABEL } from "../profile";
import { type ChatThread, useApp } from "../store";
import { colors, fonts } from "../theme";

const SUGGESTIONS = ["AI 관련 공모전 있어?", "이번 주 마감 장학금 알려줘", "현장실습 학점 인정돼?"];
const newThread = (): ChatThread => ({ id: String(Date.now()), title: "", createdAt: Date.now(), messages: [] });

/** Figma 'KHU AI 빈 대화' / '공모전 추천 대화' / '대화 목록' */
export default function Ai() {
  const { call, upsertChat, chats, profile } = useApp();
  const insets = useSafeAreaInsets();
  const [thread, setThread] = useState<ChatThread>(newThread);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const scroll = useRef<ScrollView>(null);

  const send = async (msg: string) => {
    const m = msg.trim();
    if (!m || busy) return;
    setText("");
    let t: ChatThread = { ...thread, title: thread.title || m, messages: [...thread.messages, { role: "user", text: m }] };
    setThread(t);
    setBusy(true);
    try {
      const r = await call(() => api.chat(m));
      t = { ...t, messages: [...t.messages, { role: "ai", text: r.answer, result: r }] };
    } catch (e) {
      t = { ...t, messages: [...t.messages, { role: "ai", text: e instanceof Error ? e.message : String(e) }] };
    }
    setThread(t);
    upsertChat(t);
    setBusy(false);
    setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 50);
  };

  const canSend = text.trim().length > 0 && !busy;

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <View style={[styles.row, { paddingTop: insets.top + 14, paddingHorizontal: 22, height: insets.top + 52, justifyContent: "space-between" }]}>
        <Pressable onPress={() => setDrawer(true)} hitSlop={8}>
          <Icon name="menu" size={24} />
        </Pressable>
        <View pointerEvents="none" style={{ position: "absolute", left: 0, right: 0, top: insets.top + 13, alignItems: "center" }}>
          <T w="serif" s={17} lh={25}>
            KHU AI
          </T>
        </View>
        <View style={[styles.row, { gap: 22 }]}>
          <Pressable onPress={() => setThread(newThread())} hitSlop={8}>
            <Icon name="plus" size={22} />
          </Pressable>
          <Pressable onPress={() => router.back()} hitSlop={8}>
            <Icon name="close" size={22} />
          </Pressable>
        </View>
      </View>

      {thread.messages.length === 0 ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 32, paddingBottom: 60 }}>
          <Icon name="arch" w={56} h={78.4} />
          <T w="serif" s={22} lh={32} style={{ marginTop: 12 }}>
            무엇을 도와드릴까요?
          </T>
          <T s={13} lh={19} c={colors.sub} style={{ marginTop: 12 }}>
            학사 일정, 장학, 공모전 무엇이든 물어보세요
          </T>
          <View style={{ alignSelf: "stretch", gap: 8, marginTop: 22 }}>
            {SUGGESTIONS.map((s) => (
              <Pressable key={s} onPress={() => send(s)} style={[styles.row, { height: 44, borderRadius: 22, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.white, paddingHorizontal: 17, gap: 8 }]}>
                <Icon name="ai_14_primary_b" size={14} />
                <T s={14} lh={20}>
                  {s}
                </T>
              </Pressable>
            ))}
          </View>
        </View>
      ) : (
        <ScrollView ref={scroll} contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 16, paddingBottom: 16, gap: 14 }}>
          {thread.messages.map((m, i) =>
            m.role === "user" ? (
              <View key={i} style={{ alignSelf: "flex-end", backgroundColor: colors.primary, borderRadius: 18, borderBottomRightRadius: 4, paddingHorizontal: 16, paddingVertical: 10, maxWidth: "80%" }}>
                <T s={15} lh={21} c={colors.white}>
                  {m.text}
                </T>
              </View>
            ) : (
              <AiMessage key={i} text={m.text} result={m.result} onAsk={send} interests={profile?.interests ?? []} />
            ),
          )}
          {busy ? <ActivityIndicator color={colors.primary} style={{ alignSelf: "flex-start", marginLeft: 38 }} /> : null}
        </ScrollView>
      )}

      <View style={{ paddingHorizontal: 16, paddingBottom: insets.bottom + 8 }}>
        <View style={[styles.row, { height: 54, borderRadius: 26, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.white, paddingLeft: 19, paddingRight: 7 }]}>
          <TextInput
            value={text}
            onChangeText={setText}
            onSubmitEditing={() => send(text)}
            placeholder="궁금한 학사 정보를 물어보세요"
            placeholderTextColor={colors.muted}
            returnKeyType="send"
            style={{ flex: 1, fontFamily: fonts.regular, fontSize: 15, color: colors.text, paddingVertical: 0 }}
          />
          <Pressable
            onPress={() => send(text)}
            disabled={!canSend}
            style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: canSend ? colors.sendActive : colors.dot, alignItems: "center", justifyContent: "center" }}
          >
            <Icon name={canSend ? "send" : "send_disabled"} size={20} />
          </Pressable>
        </View>
        <T s={11} lh={16} c={colors.muted} style={{ textAlign: "center", marginTop: 8 }}>
          AI 답변은 원문 공지와 함께 확인해 주세요
        </T>
      </View>

      <Drawer
        visible={drawer}
        chats={chats}
        currentId={thread.id}
        onClose={() => setDrawer(false)}
        onNew={() => {
          setThread(newThread());
          setDrawer(false);
        }}
        onPick={(t) => {
          setThread(t);
          setDrawer(false);
        }}
      />
    </KeyboardAvoidingView>
  );
}

function AiMessage({ text, result, onAsk, interests }: { text: string; result?: ChatOut; onAsk: (m: string) => void; interests: string[] }) {
  const { saved, save, call } = useApp();
  const items = result?.items ?? [];
  // 관심 분야 라벨은 굵게 강조
  const labels = Object.values(TOPIC_LABEL).filter((l) => text.includes(l));
  const parts = labels.length ? text.split(new RegExp(`(${labels.join("|")})`)) : [text];
  const first = items[0];
  return (
    <View style={[styles.row, { alignItems: "flex-start", gap: 10 }]}>
      <View style={{ width: 28, height: 28, borderRadius: 14, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}>
        <Icon name="ai_16_white" size={16} />
      </View>
      <View style={{ flex: 1, gap: 10 }}>
        <T s={15} lh={24}>
          {parts.map((p, i) =>
            labels.includes(p) ? (
              <T key={i} w="b" s={15} lh={24} c={colors.primary}>
                {p}
              </T>
            ) : (
              p
            ),
          )}
        </T>
        {items.map((it) => {
          const s = saved[it.id];
          const tag = it.topics.filter((t) => interests.includes(t)).map((t) => TOPIC_LABEL[t])[0];
          const line = s?.checklist.length ? `체크리스트 ${s.done.length}/${s.checklist.length} 진행 중` : (it.reasons.find((r) => r.field !== "all" && r.status === "match")?.requirement ?? tag ?? it.category);
          return (
            <Pressable key={it.id} onPress={() => router.push(`/notice/${it.id}`)} style={{ backgroundColor: colors.white, borderWidth: 1, borderColor: colors.cardBorder, borderRadius: 14, padding: 14 }}>
              <View style={[styles.row, { gap: 8 }]}>
                <DdayPill d={it.d_day} variant={it.d_day !== null && it.d_day > 14 ? "outline" : "tint"} />
                <T s={12} lh={17} c={colors.sub} style={{ flex: 1 }} numberOfLines={1}>
                  {it.source}
                </T>
                {s ? <Icon name="bookmark_16" size={16} /> : null}
              </View>
              <T w="b" s={15} lh={21} style={{ marginTop: 4 }}>
                {it.title}
              </T>
              <T w="m" s={12} lh={17} c={it.status === "check" ? colors.warnText : colors.primary} style={{ marginTop: 4 }}>
                {it.status === "check" ? "확인 필요" : "지원 가능"} · {line}
              </T>
            </Pressable>
          );
        })}
        {first ? (
          <>
            <T s={15} lh={24}>
              마감이 가장 가까운 공지부터 준비해 보세요. 남은 준비를 캘린더 알림으로 받아 볼까요?
            </T>
            <View style={[styles.row, { gap: 8, flexWrap: "wrap" }]}>
              <Pressable
                onPress={async () => {
                  if (!saved[first.id]) {
                    const d = await call(() => api.notice(first.id)).catch(() => null);
                    await save({ id: first.id, title: first.title, source: first.source, category: first.category, deadline_date: first.deadline_date, url: first.url, checklist: d?.checklist ?? [] });
                  }
                  router.push("/calendar");
                }}
                style={[styles.row, { height: 44, borderRadius: 22, borderWidth: 1.5, borderColor: colors.primary, paddingHorizontal: 16, gap: 4 }]}
              >
                <Icon name="cal_16_primary" size={16} />
                <T w="b" s={13} lh={19} c={colors.primary}>
                  {saved[first.id] ? "알림 설정됨" : "캘린더 알림 받기"}
                </T>
              </Pressable>
              <Pressable
                onPress={() => router.navigate({ pathname: "/notices", params: { category: first.category, sort: "deadline" } })}
                style={{ height: 44, borderRadius: 22, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.white, paddingHorizontal: 16, justifyContent: "center" }}
              >
                <T w="b" s={13} lh={19} c={colors.sub}>
                  다른 {first.category} 더 보기
                </T>
              </Pressable>
            </View>
            <View style={[styles.row, { gap: 4 }]}>
              <Icon name="link" size={14} />
              <T s={12} lh={17} c={colors.muted} style={{ flex: 1 }}>
                출처 · {result?.sources.join(", ")}
              </T>
            </View>
          </>
        ) : (
          <View style={[styles.row, { gap: 8, flexWrap: "wrap" }]}>
            {SUGGESTIONS.filter((s) => s !== text).slice(0, 2).map((s) => (
              <Pressable key={s} onPress={() => onAsk(s)} style={{ height: 40, borderRadius: 20, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.white, paddingHorizontal: 14, justifyContent: "center" }}>
                <T s={13} c={colors.sub}>
                  {s}
                </T>
              </Pressable>
            ))}
          </View>
        )}
      </View>
    </View>
  );
}

function Drawer({
  visible,
  chats,
  currentId,
  onClose,
  onNew,
  onPick,
}: {
  visible: boolean;
  chats: ChatThread[];
  currentId: string;
  onClose: () => void;
  onNew: () => void;
  onPick: (t: ChatThread) => void;
}) {
  const { profile } = useApp();
  const insets = useSafeAreaInsets();
  const [q, setQ] = useState("");
  const now = Date.now();
  const groups: { label: string; items: ChatThread[] }[] = [
    { label: "오늘", items: [] },
    { label: "이번 주", items: [] },
    { label: "지난 대화", items: [] },
  ];
  for (const c of chats.filter((c) => c.title.includes(q))) {
    const age = (now - c.createdAt) / 86400000;
    groups[age < 1 ? 0 : age < 7 ? 1 : 2].items.push(c);
  }
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={{ flex: 1, flexDirection: "row" }}>
        <View style={{ width: 300, backgroundColor: colors.white, paddingTop: insets.top + 14, paddingBottom: insets.bottom + 12 }}>
          <View style={[styles.row, { paddingHorizontal: 20, gap: 8 }]}>
            <Icon name="ai_20_primary" size={20} />
            <T w="serif" s={20} lh={29} c={colors.primary} style={{ flex: 1 }}>
              KHU AI
            </T>
            <Pressable onPress={onNew} style={{ width: 32, height: 34, borderRadius: 17, backgroundColor: colors.tint, alignItems: "center", justifyContent: "center" }}>
              <Icon name="plus_18" size={18} />
            </Pressable>
          </View>
          <View style={[styles.row, { marginHorizontal: 16, marginTop: 14, height: 44, borderRadius: 12, backgroundColor: colors.searchBg, paddingHorizontal: 12, gap: 8 }]}>
            <Icon name="search_18" size={18} />
            <TextInput value={q} onChangeText={setQ} placeholder="대화 검색" placeholderTextColor={colors.muted} style={{ flex: 1, fontFamily: fonts.regular, fontSize: 14, color: colors.text, paddingVertical: 0 }} />
          </View>
          <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 6 }}>
            {groups
              .filter((g) => g.items.length)
              .map((g) => (
                <View key={g.label}>
                  <T w="b" s={12} lh={17} c={colors.muted} style={{ marginTop: 12, marginBottom: 6, marginLeft: 12 }}>
                    {g.label}
                  </T>
                  {g.items.map((c) => {
                    const on = c.id === currentId;
                    return (
                      <Pressable key={c.id} onPress={() => onPick(c)} style={{ height: 44, borderRadius: 10, justifyContent: "center", paddingHorizontal: 12, backgroundColor: on ? colors.tint : "transparent" }}>
                        <T w={on ? "b" : "r"} s={14} lh={20} c={on ? colors.primary : colors.text} numberOfLines={1}>
                          {c.title}
                        </T>
                      </Pressable>
                    );
                  })}
                </View>
              ))}
            {chats.length === 0 ? (
              <T s={13} c={colors.muted} style={{ marginTop: 16, marginLeft: 12 }}>
                아직 대화가 없어요
              </T>
            ) : null}
          </ScrollView>
          <View style={[styles.row, { borderTopWidth: 1, borderTopColor: colors.divider, marginHorizontal: 16, paddingTop: 18, gap: 10 }]}>
            <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: colors.tint, alignItems: "center", justifyContent: "center" }}>
              <T w="b" s={14} lh={20} c={colors.primary}>
                {profile?.name.slice(0, 1)}
              </T>
            </View>
            <View style={{ flex: 1 }}>
              <T w="b" s={14} lh={20}>
                {profile?.name}
              </T>
              <T s={12} lh={17} c={colors.sub}>
                {profile?.dept} {profile?.grade ? `${profile.grade}학년` : ""}
              </T>
            </View>
            <Pressable
              onPress={() => {
                onClose();
                router.push("/settings");
              }}
            >
              <Icon name="gear_22" size={22} />
            </Pressable>
          </View>
        </View>
        <Pressable style={{ flex: 1, backgroundColor: colors.overlay }} onPress={onClose} />
      </View>
    </Modal>
  );
}
