// 앱 화면은 web/index.html(HTML)이고, 여기서는 그걸 띄우는 WebView 하나만 쓴다.
// expo-notifications는 Expo Go(SDK 58, Android)에서 불러오기만 해도 오류가 나서 쓰지 않는다 (알림은 HTML 안 종 아이콘).
// 예전 Expo 화면(네이티브 UI)은 2026-10-28 팀 결정으로 삭제했다. 필요하면 git 기록에서 꺼낼 수 있다.
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import React from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: "#FAF7F5" } }} />
    </SafeAreaProvider>
  );
}
