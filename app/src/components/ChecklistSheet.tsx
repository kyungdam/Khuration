import { router } from "expo-router";
import React from "react";
import { Modal, Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useApp } from "../store";
import { colors } from "../theme";
import { DdayPill, fmtDate, Icon, styles, T, Toggle } from "./ui";

/** Figma '신청 준비 시트': 체크리스트 진행 + 마감 알림 토글 */
export function ChecklistSheet({ noticeId, dDay, onClose }: { noticeId: number | null; dDay: number | null; onClose: () => void }) {
  const { saved, toggleDone, setRemind } = useApp();
  const insets = useSafeAreaInsets();
  const s = noticeId !== null ? saved[noticeId] : undefined;
  const total = s?.checklist.length ?? 0;
  const done = s?.done.length ?? 0;
  return (
    <Modal visible={!!s} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: colors.overlay }} onPress={onClose} />
      {s ? (
        <View
          style={{
            backgroundColor: colors.white,
            borderTopLeftRadius: 24,
            borderTopRightRadius: 24,
            paddingHorizontal: 24,
            paddingBottom: insets.bottom + 20,
          }}
        >
          <View style={{ alignSelf: "center", width: 36, height: 4, borderRadius: 2, backgroundColor: colors.border, marginTop: 12, marginBottom: 14 }} />
          <View style={[styles.row, { gap: 8 }]}>
            <DdayPill d={dDay} size="m" variant="tint" />
            <T s={13} c={colors.sub} numberOfLines={1} style={{ flex: 1 }}>
              {fmtDate(s.deadline_date).kor} 마감 · {s.source}
            </T>
          </View>
          <T w="b" s={18} lh={26} style={{ marginTop: 8 }}>
            {s.title}
          </T>
          <View style={[styles.row, { justifyContent: "space-between", marginTop: 14 }]}>
            <T w="b" s={13} c={colors.sub}>
              신청 준비
            </T>
            <T w="b" s={13} c={colors.primary}>
              {done} / {total} 완료
            </T>
          </View>
          <View style={{ height: 6, borderRadius: 3, backgroundColor: colors.segment, marginTop: 8, overflow: "hidden" }}>
            <View style={{ height: 6, borderRadius: 3, backgroundColor: colors.primary, width: total ? (`${(done / total) * 100}%` as `${number}%`) : 0 }} />
          </View>
          <View style={{ marginTop: 16 }}>
            {s.checklist.map((item, i) => {
              const on = s.done.includes(i);
              return (
                <Pressable
                  key={i}
                  onPress={() => toggleDone(s.id, i)}
                  style={[styles.row, { gap: 12, paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderTopColor: colors.divider }]}
                >
                  <View
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: 6,
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: on ? colors.primary : colors.white,
                      borderWidth: on ? 0 : 1.5,
                      borderColor: colors.checkboxBorder,
                    }}
                  >
                    {on ? <Icon name="check_14_white" size={14} /> : null}
                  </View>
                  <T s={15} lh={21} c={on ? colors.muted : colors.text} style={on ? { textDecorationLine: "line-through" } : undefined}>
                    {item}
                  </T>
                </Pressable>
              );
            })}
          </View>
          <View style={[styles.row, { backgroundColor: colors.bg, borderRadius: 12, height: 52, paddingHorizontal: 12, gap: 10, marginTop: 12 }]}>
            <Icon name="bell_20" size={20} />
            <T s={13} c={colors.textDeep} style={{ flex: 1 }}>
              마감 3일 전 · 1일 전에 알려드려요
            </T>
            <Toggle value={s.remind} onChange={(v) => setRemind(s.id, v)} />
          </View>
          <Pressable
            style={[styles.outlineBtn, { height: 48, marginTop: 12 }]}
            onPress={() => {
              onClose();
              router.push(`/notice/${s.id}`);
            }}
          >
            <T w="b" s={15} c={colors.primary}>
              공지 상세 보기
            </T>
          </Pressable>
        </View>
      ) : null}
    </Modal>
  );
}
