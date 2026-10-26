import { router } from "expo-router";
import React, { useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ApiError } from "../api";
import { OptionSheet } from "../components/OptionSheet";
import { Chip, Icon, styles, T } from "../components/ui";
import { DEPARTMENTS } from "../departments";
import type { IconName } from "../icons";
import { emptyProfile, INTERESTS, type Profile } from "../profile";
import { useApp } from "../store";
import { colors, fonts } from "../theme";

type Sheet = null | "grade" | "dept" | "income";

/** Figma 'KHURATION · 나를 알려주세요' */
export default function Onboarding() {
  const { profile, register } = useApp();
  const insets = useSafeAreaInsets();
  const [p, setP] = useState<Profile>(profile ?? emptyProfile);
  const [sheet, setSheet] = useState<Sheet>(null);
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => setP((x) => ({ ...x, [k]: v }));

  const submit = async () => {
    const missing = [!p.name.trim() && "이름", !p.grade && "학년", !p.campus && "캠퍼스", !p.dept && "학과"].filter(Boolean);
    if (missing.length) return Alert.alert("입력이 필요해요", `${missing.join(", ")}을(를) 입력해 주세요.`);
    setBusy(true);
    try {
      await register({ ...p, name: p.name.trim() });
      router.replace("/(tabs)");
    } catch (e) {
      Alert.alert("등록하지 못했어요", e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const depts = DEPARTMENTS.filter((d) => !p.campus || d.campus === p.campus);

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingTop: insets.top + 24, paddingBottom: 24 }} keyboardShouldPersistTaps="handled">
        <T w="serif" s={23} lh={31}>
          맞춤 공지를 위해{"\n"}나를 알려주세요
        </T>
        <T s={13} lh={19} c={colors.sub} style={{ marginTop: 8 }}>
          입력한 정보는 지원 자격 확인과 공지 추천에만 쓰여요
        </T>

        <View style={[styles.row, { gap: 10, marginTop: 23, alignItems: "flex-start" }]}>
          <Field label="이름" style={{ flex: 1 }}>
            <TextInput value={p.name} onChangeText={(v) => set("name", v)} placeholder="이름 입력" placeholderTextColor={colors.muted} style={input} />
          </Field>
          <Field label="학년" style={{ flex: 1 }}>
            <Select text={p.grade ? `${p.grade}학년` : null} icon="down_grade" onPress={() => setSheet("grade")} />
          </Field>
        </View>

        <Field label="캠퍼스">
          <View style={[styles.row, { gap: 8 }]}>
            {(["seoul", "global"] as const).map((c) => {
              const on = p.campus === c;
              return (
                <Pressable
                  key={c}
                  onPress={() => {
                    set("campus", c);
                    if (p.dept && DEPARTMENTS.find((d) => d.dept === p.dept)?.campus !== c) setP((x) => ({ ...x, campus: c, dept: null, college: null }));
                  }}
                  style={[box, { flex: 1, alignItems: "center", backgroundColor: on ? colors.primary : colors.white, borderColor: on ? colors.primary : colors.border }]}
                >
                  <T w={on ? "b" : "m"} s={14} lh={20} c={on ? colors.white : colors.sub}>
                    {c === "seoul" ? "서울캠퍼스" : "국제캠퍼스"}
                  </T>
                </Pressable>
              );
            })}
          </View>
        </Field>

        <Field label="학과">
          <Select text={p.dept} icon="down_dept" onPress={() => setSheet("dept")} />
        </Field>

        <View style={[styles.row, { gap: 8, alignItems: "flex-start" }]}>
          <Field label="평균 학점" style={{ flex: 1 }}>
            <TextInput value={p.gpa} onChangeText={(v) => set("gpa", v)} placeholder="3.87" keyboardType="decimal-pad" placeholderTextColor={colors.muted} style={[input, { textAlign: "center", paddingHorizontal: 6 }]} />
          </Field>
          <Field label="직전 평점" style={{ flex: 1 }}>
            <TextInput value={p.lastGpa} onChangeText={(v) => set("lastGpa", v)} placeholder="4.02" keyboardType="decimal-pad" placeholderTextColor={colors.muted} style={[input, { textAlign: "center", paddingHorizontal: 6 }]} />
          </Field>
          <Field label="취득 학점" style={{ flex: 1 }}>
            <TextInput value={p.credits} onChangeText={(v) => set("credits", v)} placeholder="78" keyboardType="number-pad" placeholderTextColor={colors.muted} style={[input, { textAlign: "center", paddingHorizontal: 6 }]} />
          </Field>
          <Field label="소득 분위" style={{ flex: 1 }}>
            <Select text={p.income ? `${p.income}분위` : null} icon="down_income" center onPress={() => setSheet("income")} />
          </Field>
        </View>

        <View style={[styles.row, { justifyContent: "space-between", marginTop: 14 }]}>
          <T w="b" s={12} lh={17} c={colors.sub}>
            관심 분야
          </T>
          <T s={12} lh={17} c={colors.muted}>
            여러 개 선택 가능 · {p.interests.length}개 선택됨
          </T>
        </View>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 9 }}>
          {INTERESTS.map((it) => {
            const on = p.interests.includes(it.key);
            return (
              <Chip
                key={it.key}
                label={it.label}
                active={on}
                onPress={() => set("interests", on ? p.interests.filter((k) => k !== it.key) : [...p.interests, it.key])}
              />
            );
          })}
        </View>

        <View style={[styles.row, { justifyContent: "space-between", marginTop: 14 }]}>
          <T w="b" s={12} lh={17} c={colors.sub}>
            하고 싶은 활동
          </T>
          <View style={[styles.row, { gap: 4 }]}>
            <Icon name="ai_14_primary" size={14} />
            <T w="b" s={12} lh={17} c={colors.primary}>
              AI가 문장 그대로 이해해요
            </T>
          </View>
        </View>
        <TextInput
          value={p.intentText}
          onChangeText={(v) => set("intentText", v)}
          placeholder="예) 방학 때 AI 공모전 나가고 싶어"
          placeholderTextColor={colors.muted}
          multiline
          style={[input, { height: 72, marginTop: 7, paddingTop: 12, textAlignVertical: "top" }]}
        />
      </ScrollView>

      <View style={{ paddingHorizontal: 24, paddingTop: 8, paddingBottom: insets.bottom + 16 }}>
        <Pressable onPress={submit} disabled={busy} style={{ height: 52, borderRadius: 14, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}>
          {busy ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <T w="b" s={16} lh={24} c={colors.white}>
              완료
            </T>
          )}
        </Pressable>
      </View>

      <OptionSheet
        visible={sheet === "grade"}
        title="학년"
        value={p.grade}
        options={[1, 2, 3, 4, 5].map((g) => ({ label: `${g}학년`, value: g }))}
        onSelect={(v) => set("grade", v)}
        onClose={() => setSheet(null)}
      />
      <OptionSheet
        visible={sheet === "dept"}
        title="학과"
        value={p.dept}
        options={depts.map((d) => ({ label: d.dept, value: d.dept, sub: d.college }))}
        onSelect={(v) => {
          const d = DEPARTMENTS.find((x) => x.dept === v);
          setP((x) => ({ ...x, dept: v, college: d?.college ?? null, campus: x.campus ?? d?.campus ?? null }));
        }}
        onClose={() => setSheet(null)}
      />
      <OptionSheet
        visible={sheet === "income"}
        title="소득 분위"
        value={p.income}
        options={[...Array.from({ length: 10 }, (_, i) => ({ label: `${i + 1}분위`, value: i + 1 as number | null })), { label: "모름 / 입력 안 함", value: null }]}
        onSelect={(v) => set("income", v)}
        onClose={() => setSheet(null)}
      />
    </KeyboardAvoidingView>
  );
}

const box = { height: 44, borderRadius: 12, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.white, justifyContent: "center" as const };
const input = { ...box, paddingHorizontal: 14, fontFamily: fonts.regular, fontSize: 15, color: colors.text };

function Field({ label, children, style }: { label: string; children: React.ReactNode; style?: object }) {
  return (
    <View style={[{ marginTop: 14 }, style]}>
      <T w="b" s={12} lh={17} c={colors.sub} style={{ marginBottom: 7 }}>
        {label}
      </T>
      {children}
    </View>
  );
}

function Select({ text, icon, onPress, center }: { text: string | null; icon: IconName; onPress: () => void; center?: boolean }) {
  return (
    <Pressable
      onPress={onPress}
      style={[box, styles.row, { paddingHorizontal: center ? 6 : 14, justifyContent: center ? "center" : "space-between", gap: 2 }]}
    >
      <T s={15} lh={21} c={text ? colors.text : colors.muted} numberOfLines={1}>
        {text ?? "선택"}
      </T>
      <Icon name={icon} size={18} />
    </Pressable>
  );
}
