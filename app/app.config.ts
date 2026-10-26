import type { ConfigContext, ExpoConfig } from "expo/config";

// app.json(템플릿 생성분)을 기본으로 두고 필요한 설정만 덧붙인다
export default ({ config }: ConfigContext): ExpoConfig => {
  const base = (config.plugins ?? []).filter(
    (p) => !["expo-notifications", "expo-calendar"].includes(Array.isArray(p) ? p[0] : p),
  );
  return {
    ...config,
    name: "Khuration",
    slug: config.slug ?? "khuration",
    scheme: "khuration",
    userInterfaceStyle: "light",
    plugins: [
      ...base,
      "expo-notifications",
      ["expo-calendar", { calendarPermission: "공지 마감일을 캘린더에 저장하기 위해 필요합니다." }],
    ],
  };
};
