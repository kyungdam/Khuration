import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import React from "react";
import { Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { T } from "../components/ui";
import { icons } from "../icons";
import { useApp } from "../store";
import { colors } from "../theme";

/** Figma 'KHURATION · 시작' */
export default function Start() {
  const { ready, profile } = useApp();
  const insets = useSafeAreaInsets();
  return (
    // Figma는 원형(radial) 그라데이션. RN 기본 기능으로는 세로 그라데이션으로 근사
    <LinearGradient colors={["#6a0f2a", "#7e1534", "#570b22"]} locations={[0, 0.28, 1]} style={{ flex: 1 }}>
      <StatusBar style="light" />
      <View style={{ flex: 1, alignItems: "center", paddingTop: insets.top + 96 }}>
        <Image source={icons.lion} style={{ width: 246, height: 229 }} contentFit="cover" />
        <T w="serif" s={46} lh={66} c={colors.gold}>
          KHURATION
        </T>
        <T w="m" s={17} lh={25} c={colors.cream} style={{ marginTop: 6 }}>
          당신만을 위한 학교생활 메이트
        </T>
        <T s={13} lh={19} c={colors.creamSub} style={{ marginTop: 8 }}>
          흩어진 교내 공지를 모아, 나에게 맞는 것만 먼저
        </T>
      </View>
      <Pressable
        disabled={!ready}
        onPress={() => router.replace(profile ? "/(tabs)" : "/onboarding")}
        style={{
          marginHorizontal: 24,
          marginBottom: insets.bottom + 44,
          height: 56,
          borderRadius: 28,
          backgroundColor: colors.cream,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <T w="b" s={17} lh={25} c={colors.primaryDark}>
          START
        </T>
      </Pressable>
    </LinearGradient>
  );
}
