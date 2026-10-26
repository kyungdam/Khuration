// 앱 화면은 HTML(web/index.html)로 바뀌었다. 이 화면은 그 HTML을 띄우는 껍데기(WebView)다.
// - HTML은 백엔드가 /web/ 으로 내려준다 → 서버 주소는 src/config.ts(app/.env) 한 곳에서만 바꾼다.
// - 공지 원문·신청 링크는 HTML이 postMessage로 넘기면 기기 브라우저로 연다.
// - "캘린더에 저장"은 HTML이 addCalendar를 보내면 폰 캘린더에도 넣고, 결과를 window.KhuNative로 돌려준다.
// 예전 Expo 화면(onboarding, (tabs) 등)은 팀 결정 전까지 지우지 않고 남겨 둔다.
import * as WebBrowser from "expo-web-browser";
import React, { useRef, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { WebView, type WebViewMessageEvent } from "react-native-webview";

import { API_BASE_URL } from "../config";
import { addDeadlineToPhoneCalendar } from "../nativeCalendar";

const BASE = API_BASE_URL.replace(/\/$/, "");
const WEB_URL = `${BASE}/web/`;
const BG = "#FAF7F5";
const BRAND = "#8A1538";

const openExternal = (url: string) => {
  if (/^https?:\/\//.test(url)) WebBrowser.openBrowserAsync(url).catch(() => undefined);
};

export default function WebShell() {
  const ref = useRef<WebView>(null);
  const [error, setError] = useState<string | null>(null);
  const [key, setKey] = useState(0);

  const reply = (payload: object) => {
    ref.current?.injectJavaScript(`window.KhuNative && window.KhuNative(${JSON.stringify(payload)}); true;`);
  };

  const onMessage = async (e: WebViewMessageEvent) => {
    let m: { type?: string; url?: string; id?: string; title?: string; date?: string };
    try {
      m = JSON.parse(e.nativeEvent.data);
    } catch {
      return; // HTML이 보낸 메시지가 JSON이 아니면 무시
    }
    if (m.type === "openUrl" && m.url) openExternal(m.url);
    if (m.type === "addCalendar" && m.id && m.title && m.date) {
      try {
        await addDeadlineToPhoneCalendar(m.title, m.date, m.url ?? "");
        reply({ type: "calendarResult", id: m.id, ok: true, message: "폰 캘린더에도 추가했어요 (마감 3일 전 알림)" });
      } catch (err) {
        reply({ type: "calendarResult", id: m.id, ok: false, message: err instanceof Error ? err.message : "폰 캘린더에 추가하지 못했어요" });
      }
    }
  };

  if (error) {
    return (
      <SafeAreaView style={[styles.fill, styles.center]}>
        <Text style={styles.title}>서버에 연결할 수 없어요</Text>
        <Text style={styles.body}>
          PC에서 백엔드가 켜져 있는지, 폰과 PC가 같은 와이파이·핫스팟인지 확인해 주세요.
        </Text>
        <Text style={styles.url}>{WEB_URL}</Text>
        <Text style={styles.small}>{error}</Text>
        <Pressable
          style={styles.btn}
          onPress={() => {
            setError(null);
            setKey((k) => k + 1);
          }}
        >
          <Text style={styles.btnText}>다시 시도</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.fill} edges={["top", "bottom"]}>
      <WebView
        key={key}
        ref={ref}
        source={{ uri: WEB_URL }}
        style={styles.fill}
        javaScriptEnabled
        domStorageEnabled
        cacheEnabled
        setSupportMultipleWindows={false}
        startInLoadingState
        renderLoading={() => (
          <View style={[StyleSheet.absoluteFill, styles.center]}>
            <ActivityIndicator color={BRAND} />
          </View>
        )}
        onMessage={onMessage}
        onShouldStartLoadWithRequest={(req) => {
          // 앱 화면(서버 주소) 안의 이동만 WebView에서, 나머지 링크는 기기 브라우저로
          if (req.url.startsWith(BASE) || req.url.startsWith("about:")) return true;
          openExternal(req.url);
          return false;
        }}
        onError={(e) => setError(e.nativeEvent.description || "연결 실패")}
        onHttpError={(e) => {
          if (e.nativeEvent.url.startsWith(WEB_URL)) setError(`HTTP ${e.nativeEvent.statusCode}`);
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, backgroundColor: BG },
  center: { alignItems: "center", justifyContent: "center", padding: 24 },
  title: { fontSize: 18, fontWeight: "700", color: "#231519" },
  body: { marginTop: 8, fontSize: 14, lineHeight: 20, color: "#5E4E53", textAlign: "center" },
  url: { marginTop: 12, fontSize: 13, color: BRAND },
  small: { marginTop: 4, fontSize: 12, color: "#786A6E" },
  btn: { marginTop: 20, height: 48, paddingHorizontal: 24, borderRadius: 24, backgroundColor: BRAND, justifyContent: "center" },
  btnText: { color: "#fff", fontSize: 15, fontWeight: "700" },
});
