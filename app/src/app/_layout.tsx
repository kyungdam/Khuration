// 앱 화면은 web/index.html(HTML)이고, 여기서는 그걸 띄우는 WebView 하나만 쓴다.
// expo-notifications 등은 Expo Go(SDK 58, Android)에서 불러오기만 해도 오류가 나서 넣지 않는다.
// 예전 Expo 화면은 src/legacy/ 로 옮겨 보관 중 (라우트 아님).
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
