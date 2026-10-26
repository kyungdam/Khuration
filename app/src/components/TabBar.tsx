import { router } from "expo-router";
import React from "react";
import { Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import type { IconName } from "../icons";
import { colors } from "../theme";
import { Icon, T } from "./ui";

const TABS: Record<string, { label: string; on: IconName; off: IconName }> = {
  index: { label: "홈", on: "tab_home_active", off: "tab_home" },
  notices: { label: "공지사항", on: "tab_mega_active", off: "tab_mega" },
  calendar: { label: "캘린더", on: "tab_cal_active", off: "tab_cal" },
};

/** Figma '주요 메뉴' 하단 탭 (KHU AI는 전체 화면 대화로 이동) */
type Props = {
  state: { index: number; routes: { key: string; name: string }[] };
  navigation: { navigate: (name: string) => void };
};

export function TabBar({ state, navigation }: Props) {
  const insets = useSafeAreaInsets();
  return (
    <View
      style={{
        flexDirection: "row",
        backgroundColor: colors.white,
        borderTopWidth: 1,
        borderTopColor: colors.cardBorder,
        paddingTop: 12,
        paddingBottom: Math.max(insets.bottom, 12),
      }}
    >
      {state.routes.map((route, i) => {
        const tab = TABS[route.name];
        if (!tab) return null;
        const focused = state.index === i;
        return (
          <Pressable key={route.key} onPress={() => navigation.navigate(route.name)} style={{ flex: 1, alignItems: "center", gap: 3 }}>
            <Icon name={focused ? tab.on : tab.off} size={24} />
            <T w={focused ? "b" : "m"} s={11} lh={16} c={focused ? colors.primary : colors.muted}>
              {tab.label}
            </T>
          </Pressable>
        );
      })}
      <Pressable onPress={() => router.push("/ai")} style={{ flex: 1, alignItems: "center", gap: 3, marginTop: -2 }}>
        <View style={{ width: 28, height: 28, borderRadius: 14, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}>
          <Icon name="ai_16_white" size={16} />
        </View>
        <T w="m" s={11} lh={16} c={colors.muted}>
          KHU AI
        </T>
      </Pressable>
    </View>
  );
}
