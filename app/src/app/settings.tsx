import { router } from "expo-router";
import React, { useEffect, useState } from "react";
import { Alert, Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "../api";
import { Card, Icon, styles, T } from "../components/ui";
import { API_BASE_URL } from "../config";
import { profileLine } from "../profile";
import { previewReminder } from "../push";
import { useApp } from "../store";
import { colors } from "../theme";

/** 설정 + 시연 도구 (Figma 화면 없음, 같은 토큰으로 구성) */
export default function Settings() {
  const { profile, token, call, reset } = useApp();
  const insets = useSafeAreaInsets();
  const [mode, setMode] = useState<string>("확인 중");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    api.health().then((h) => setMode(h.mode)).catch(() => setMode("연결 안 됨"));
  }, []);

  const run = async (label: string, fn: () => Promise<string | void>) => {
    try {
      const msg = await fn();
      Alert.alert(label, msg || "완료했어요");
    } catch (e) {
      Alert.alert(label, e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.bg }} contentContainerStyle={{ paddingHorizontal: 24, paddingTop: insets.top + 14, paddingBottom: insets.bottom + 24 }}>
      <Pressable onPress={() => router.back()} hitSlop={10} style={{ marginLeft: -2 }}>
        <Icon name="back" size={24} />
      </Pressable>
      <T w="serif" s={24} lh={35} style={{ marginTop: 14 }}>
        설정
      </T>

      <Card style={{ padding: 17, marginTop: 16, gap: 4 }}>
        <T w="b" s={15}>
          {profile?.name}
        </T>
        <T s={13} c={colors.sub}>
          {profileLine(profile)}
        </T>
        <T s={12} c={colors.muted} style={{ marginTop: 6 }}>
          이름·정확한 학점·하고 싶은 활동 문장은 이 기기에만 저장돼요. 서버에는 학점 구간 같은 익명 조건만 보내요.
        </T>
      </Card>
      <Row label="내 정보 수정" onPress={() => router.push("/onboarding")} />
      <Row
        label="내 데이터 모두 삭제"
        danger
        onPress={() =>
          Alert.alert("모두 삭제할까요?", "서버의 익명 조건과 이 기기의 저장 정보가 지워져요.", [
            { text: "취소", style: "cancel" },
            {
              text: "삭제",
              style: "destructive",
              onPress: async () => {
                await api.deleteDevice().catch(() => {});
                await reset();
                router.replace("/");
              },
            },
          ])
        }
      />

      <T w="b" s={16} style={{ marginTop: 28 }}>
        시연 도구
      </T>
      <T s={12} c={colors.muted} style={{ marginTop: 4 }}>
        서버 모드: {mode} · {API_BASE_URL}
      </T>
      {mode === "demo" ? (
        <>
          <T s={12} c={colors.muted}>
            가상 시계: +{offset}일
          </T>
          <View style={[styles.row, { gap: 8, marginTop: 10, flexWrap: "wrap" }]}>
            {[1, 3, 7].map((d) => (
              <Small
                key={d}
                label={`+${d}일`}
                onPress={() =>
                  run("시계 앞당기기", async () => {
                    const r = await api.demo.advance(d);
                    setOffset(r.offset_days);
                    return `가상 시계 +${r.offset_days}일. 홈을 당겨서 새로고침하면 D-day가 줄어요.`;
                  })
                }
              />
            ))}
            <Small
              label="시계 초기화"
              onPress={() =>
                run("시계 초기화", async () => {
                  await api.demo.reset();
                  setOffset(0);
                })
              }
            />
            <Small label="시드 다시 넣기" onPress={() => run("시드", async () => `공지 ${(await api.demo.reseed()).loaded}건을 다시 넣었어요.`)} />
          </View>
          <Row
            label="원격 푸시 보내기 (D-3)"
            onPress={() =>
              run("원격 푸시", async () => {
                const r = await call(() => api.demo.firePush("d3"));
                return r.sent ? "보냈어요. 잠시 뒤 알림이 와요." : `보내지 않았어요: ${r.reason ?? ""}${token?.startsWith("local-") ? "\n(Expo Go에서는 원격 푸시 토큰이 없어 로컬 알림 미리보기를 쓰세요)" : ""}`;
              })
            }
          />
          <Row
            label="로컬 알림 미리보기 (5초 뒤)"
            onPress={() =>
              run("로컬 알림", async () => {
                const feed = await call(() => api.feed(false));
                const n = [...feed].filter((f) => f.d_day !== null).sort((a, b) => (a.d_day ?? 0) - (b.d_day ?? 0))[0];
                if (!n) return "보낼 공지가 없어요";
                const ok = await previewReminder(n.id, n.title);
                return ok ? "5초 뒤 알림이 와요. 앱을 내려 두고 기다려 보세요." : "알림 권한이 없어요";
              })
            }
          />
        </>
      ) : null}
    </ScrollView>
  );
}

function Row({ label, onPress, danger }: { label: string; onPress: () => void; danger?: boolean }) {
  return (
    <Pressable onPress={onPress}>
      <Card style={[styles.row, { height: 56, paddingHorizontal: 17, marginTop: 10, justifyContent: "space-between" }]}>
        <T w="b" s={15} c={danger ? colors.primary : colors.text}>
          {label}
        </T>
        <Icon name="right_18" size={18} />
      </Card>
    </Pressable>
  );
}

function Small({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ height: 40, borderRadius: 20, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.white, paddingHorizontal: 14, justifyContent: "center" }}>
      <T w="m" s={13} c={colors.sub}>
        {label}
      </T>
    </Pressable>
  );
}
