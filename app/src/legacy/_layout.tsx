// 예전 Expo 화면용 레이아웃 (보관용, 지금은 쓰지 않음). 현재 앱은 src/app/index.tsx 의 WebView 하나뿐이다.
import { Hahmlet_700Bold } from "@expo-google-fonts/hahmlet";
import { NotoSansKR_400Regular, NotoSansKR_500Medium, NotoSansKR_700Bold } from "@expo-google-fonts/noto-sans-kr";
import { useFonts } from "expo-font";
import * as Notifications from "expo-notifications";
import { router, Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import React, { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AppProvider } from "../store";
import { colors } from "../theme";

export default function RootLayout() {
  const [loaded] = useFonts({ Hahmlet_700Bold, NotoSansKR_400Regular, NotoSansKR_500Medium, NotoSansKR_700Bold });

  // 알림을 누르면 해당 공지로 이동 (딥링크)
  useEffect(() => {
    const sub = Notifications.addNotificationResponseReceivedListener((r) => {
      const id = (r.notification.request.content.data as { notice_id?: number } | undefined)?.notice_id;
      if (id) router.push(`/notice/${id}`);
    });
    return () => sub.remove();
  }, []);

  if (!loaded) return null;
  return (
    <SafeAreaProvider>
      <AppProvider>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
          <Stack.Screen name="index" options={{ contentStyle: { backgroundColor: colors.primaryDark } }} />
          <Stack.Screen name="ai" options={{ animation: "slide_from_bottom" }} />
        </Stack>
      </AppProvider>
    </SafeAreaProvider>
  );
}
