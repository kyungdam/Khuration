import { Image } from "expo-image";
import React from "react";
import { Pressable, type StyleProp, StyleSheet, Text, type TextProps, type TextStyle, View, type ViewStyle } from "react-native";

import { icons, type IconName } from "../icons";
import { colors, fonts } from "../theme";

/** Figma 원본 아이콘 (SVG 그대로) */
export function Icon({ name, size, w, h, style }: { name: IconName; size?: number; w?: number; h?: number; style?: ViewStyle }) {
  return <Image source={icons[name]} style={[{ width: w ?? size ?? 24, height: h ?? size ?? 24 }, style as object]} contentFit="contain" />;
}

type Weight = "r" | "m" | "b" | "serif";
const FAMILY: Record<Weight, string> = { r: fonts.regular, m: fonts.medium, b: fonts.bold, serif: fonts.serif };

/** 텍스트: 굵기(w) · 크기(s) · 색(c) · 줄높이(lh) */
export function T({
  w = "r",
  s = 14,
  c = colors.text,
  lh,
  style,
  ...rest
}: TextProps & { w?: Weight; s?: number; c?: string; lh?: number; style?: StyleProp<TextStyle> }) {
  return (
    <Text
      {...rest}
      style={[{ fontFamily: FAMILY[w], fontSize: s, color: c, lineHeight: lh ?? Math.round(s * 1.42), includeFontPadding: false }, style]}
    />
  );
}

/** D-day 배지 (작은 pill) */
export function DdayPill({ d, size = "s", variant }: { d: number | null; size?: "s" | "m"; variant?: "filled" | "tint" | "outline" | "white" }) {
  if (d === null) return null;
  const v = variant ?? (d <= 7 ? "filled" : "tint");
  const bg = v === "filled" ? colors.primary : v === "tint" ? colors.tint : colors.white;
  const fg = v === "filled" ? colors.white : colors.primary;
  const h = size === "m" ? 26 : 22;
  return (
    <View
      style={{
        height: h,
        borderRadius: h / 2,
        paddingHorizontal: size === "m" ? 10 : 8,
        backgroundColor: bg,
        justifyContent: "center",
        borderWidth: v === "outline" ? 1 : 0,
        borderColor: colors.outlineSoft,
      }}
    >
      <T w="b" s={size === "m" ? 13 : 12} c={fg}>
        {d === 0 ? "D-DAY" : `D-${d}`}
      </T>
    </View>
  );
}

/** 카테고리 태그 (사각 pill) */
export function CategoryTag({ label }: { label: string }) {
  return (
    <View style={{ backgroundColor: colors.tint, borderRadius: 6, height: 22, paddingHorizontal: 8, justifyContent: "center" }}>
      <T w="b" s={11} c={colors.primary} lh={16}>
        {label}
      </T>
    </View>
  );
}

/** 선택 칩 (관심 분야, 카테고리 필터) */
export function Chip({ label, active, onPress, height = 44 }: { label: string; active: boolean; onPress: () => void; height?: number }) {
  return (
    <Pressable
      onPress={onPress}
      style={{
        height,
        borderRadius: 22,
        paddingHorizontal: 15,
        justifyContent: "center",
        borderWidth: 1,
        borderColor: active ? colors.primary : colors.border,
        backgroundColor: active ? colors.primary : colors.white,
      }}
    >
      <T w={active ? "b" : "m"} s={14} lh={20} c={active ? colors.white : colors.sub}>
        {label}
      </T>
    </Pressable>
  );
}

/** 토글 (Figma: 44x26, knob 20) */
export function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <Pressable
      onPress={() => onChange(!value)}
      hitSlop={8}
      style={{
        width: 44,
        height: 26,
        borderRadius: 13,
        backgroundColor: value ? colors.primary : colors.border,
        padding: 3,
        alignItems: value ? "flex-end" : "flex-start",
      }}
    >
      <View style={{ width: 20, height: 20, borderRadius: 10, backgroundColor: colors.white }} />
    </Pressable>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={[styles.card, { margin: 24, padding: 18, gap: 10 }]}>
      <T w="b" s={15}>
        불러오지 못했어요
      </T>
      <T s={13} c={colors.sub}>
        {message}
      </T>
      {onRetry ? (
        <Pressable onPress={onRetry} style={styles.outlineBtn}>
          <T w="b" s={14} c={colors.primary}>
            다시 시도
          </T>
        </Pressable>
      ) : null}
    </View>
  );
}

export const styles = StyleSheet.create({
  card: { backgroundColor: colors.white, borderWidth: 1, borderColor: colors.cardBorder, borderRadius: 16 },
  outlineBtn: {
    height: 44,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.white,
  },
  row: { flexDirection: "row", alignItems: "center" },
});

const WEEK = ["일", "월", "화", "수", "목", "금", "토"];
/** "2026-10-29" → { md: "10.29", wd: "목" } */
export function fmtDate(iso: string | null) {
  if (!iso) return { md: "", wd: "", full: "", kor: "" };
  const [y, m, d] = iso.split("-").map(Number);
  const wd = WEEK[new Date(y, m - 1, d).getDay()];
  const md = `${String(m).padStart(2, "0")}.${String(d).padStart(2, "0")}`;
  return { md, wd, full: `${y}.${md}(${wd})`, kor: `${m}월 ${d}일 (${wd})` };
}
