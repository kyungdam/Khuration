// 서버 주소는 여기 한 곳에서만 바꾼다.
// 폰(Expo Go) → PC 서버: localhost 불가. PC의 IPv4 주소를 쓴다 (PowerShell: ipconfig).
// app/.env 파일에 EXPO_PUBLIC_API_BASE_URL=http://192.168.x.x:8000 을 넣으면 그 값이 우선.
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.0.12:8000";
