import React from "react";
import { Modal, Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "../theme";
import { T } from "./ui";

/** 학년·학과·소득분위 선택용 아래에서 올라오는 목록 */
export function OptionSheet<V>({
  visible,
  title,
  options,
  value,
  onSelect,
  onClose,
}: {
  visible: boolean;
  title: string;
  options: { label: string; value: V; sub?: string }[];
  value: V | null;
  onSelect: (v: V) => void;
  onClose: () => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: colors.overlay }} onPress={onClose} />
      <View
        style={{
          backgroundColor: colors.white,
          borderTopLeftRadius: 24,
          borderTopRightRadius: 24,
          maxHeight: "70%",
          paddingBottom: insets.bottom + 12,
        }}
      >
        <View style={{ alignSelf: "center", width: 36, height: 4, borderRadius: 2, backgroundColor: colors.border, marginTop: 12 }} />
        <T w="b" s={16} style={{ paddingHorizontal: 24, paddingVertical: 14 }}>
          {title}
        </T>
        <ScrollView>
          {options.map((o) => {
            const on = o.value === value;
            return (
              <Pressable
                key={String(o.value)}
                onPress={() => {
                  onSelect(o.value);
                  onClose();
                }}
                style={{
                  paddingHorizontal: 24,
                  paddingVertical: 14,
                  borderTopWidth: 1,
                  borderTopColor: colors.divider,
                  backgroundColor: on ? colors.tint : colors.white,
                  flexDirection: "row",
                  justifyContent: "space-between",
                }}
              >
                <T w={on ? "b" : "r"} s={15} c={on ? colors.primary : colors.text}>
                  {o.label}
                </T>
                {o.sub ? (
                  <T s={12} c={colors.muted}>
                    {o.sub}
                  </T>
                ) : null}
              </Pressable>
            );
          })}
        </ScrollView>
      </View>
    </Modal>
  );
}
