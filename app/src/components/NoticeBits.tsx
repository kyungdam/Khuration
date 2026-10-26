import React from "react";
import { View } from "react-native";

import type { FeedItem } from "../api";
import type { Profile } from "../profile";
import { TOPIC_LABEL } from "../profile";
import { colors } from "../theme";
import { fmtDate, T } from "./ui";

/** 카드 하단 한 줄: "화학공학과 대상 지원 가능 · AI·데이터" */
export function highlightLine(it: FeedItem, profile: Profile | null) {
  const topics = it.topics.filter((t) => profile?.interests.includes(t)).map((t) => TOPIC_LABEL[t]);
  if (it.status === "check") {
    const c = it.reasons.find((r) => r.status === "check");
    return { text: `확인 필요 · ${c?.requirement ?? "지원 자격"}`, warn: true };
  }
  const m = it.reasons.find((r) => r.status === "match" && r.field !== "all");
  const head = m ? `${m.requirement.replace(/ 대상$/, "")} 지원 가능` : "누구나 지원 가능";
  return { text: [head, ...topics.slice(0, 2)].join(" · "), warn: false };
}

/** 홈 1순위 카드 '추천 이유' 문장 */
export function reasonText(it: FeedItem, profile: Profile | null) {
  const topics = it.topics.filter((t) => profile?.interests.includes(t)).map((t) => `‘${TOPIC_LABEL[t]}’`);
  const parts: string[] = [];
  if (topics.length) parts.push(`관심 분야 ${topics.join(", ")}`);
  if (profile?.intentText.trim()) parts.push(`희망 활동 ‘${profile.intentText.trim()}’`);
  if (parts.length) return `${parts.join(", ")}와 일치해요`;
  const m = it.reasons.find((r) => r.status === "match");
  return `${m?.requirement ?? "지원 조건"}을 충족해요`;
}

/** 마감 임박 카드 왼쪽 56px 날짜 박스 */
export function DateBox({ d, date, size = 56 }: { d: number | null; date: string | null; size?: number }) {
  const v = d === null ? "outline" : d <= 5 ? "filled" : d <= 14 ? "tint" : "outline";
  const { md, wd } = fmtDate(date);
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size === 56 ? 14 : 12,
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: v === "filled" ? colors.primary : v === "tint" ? colors.tint : colors.white,
        borderWidth: v === "outline" ? 1.5 : 0,
        borderColor: colors.outlineSoft,
      }}
    >
      <T w="b" s={size === 56 ? 16 : 13} lh={size === 56 ? 24 : 19} c={v === "filled" ? colors.white : colors.primary}>
        {d === null ? "-" : d === 0 ? "D-DAY" : `D-${d}`}
      </T>
      {size === 56 ? (
        <T s={11} lh={16} c={v === "filled" ? colors.onPrimarySub : colors.onTintSub}>
          {md} {wd}
        </T>
      ) : null}
    </View>
  );
}
