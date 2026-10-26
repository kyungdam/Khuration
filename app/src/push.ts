import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

const TOKEN_KEY = "device_token";

/**
 * 서버에 등록할 기기 토큰.
 * - EAS 프로젝트가 있고 실기기면 Expo 푸시 토큰 (원격 푸시 가능)
 * - 아니면 무작위 로컬 ID (Expo Go 안드로이드 등). 이때 원격 푸시는 안 되고 로컬 알림만 된다.
 */
export async function getDeviceToken(): Promise<string> {
  const saved = await AsyncStorage.getItem(TOKEN_KEY);
  try {
    const projectId =
      (Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined)?.eas?.projectId ??
      Constants.easConfig?.projectId;
    if (Device.isDevice && projectId && (await ensureNotificationPermission())) {
      const t = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
      await AsyncStorage.setItem(TOKEN_KEY, t);
      return t;
    }
  } catch {
    // Expo Go 안드로이드는 원격 푸시 토큰을 받을 수 없다 → 로컬 ID로 대체
  }
  if (saved) return saved;
  const id = `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  await AsyncStorage.setItem(TOKEN_KEY, id);
  return id;
}

export async function ensureNotificationPermission(): Promise<boolean> {
  const cur = await Notifications.getPermissionsAsync();
  if (cur.granted) return true;
  const req = await Notifications.requestPermissionsAsync();
  return req.granted;
}

/** 마감 3일 전·1일 전 오전 9시 로컬 알림. 반환값은 취소용 ID 목록. */
export async function scheduleDeadlineReminders(
  noticeId: number,
  title: string,
  deadlineDate: string | null,
): Promise<string[]> {
  if (!deadlineDate || !(await ensureNotificationPermission())) return [];
  const [y, m, d] = deadlineDate.split("-").map(Number);
  const ids: string[] = [];
  for (const before of [3, 1]) {
    const when = new Date(y, m - 1, d - before, 9, 0, 0);
    if (when.getTime() <= Date.now()) continue;
    ids.push(
      await Notifications.scheduleNotificationAsync({
        content: { title: `마감 D-${before}`, body: title, data: { notice_id: noticeId } },
        trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: when },
      }),
    );
  }
  return ids;
}

export async function cancelReminders(ids: string[]) {
  await Promise.all(ids.map((id) => Notifications.cancelScheduledNotificationAsync(id).catch(() => {})));
}

/** 시연용: 5초 뒤 D-3 알림 */
export async function previewReminder(noticeId: number, title: string) {
  if (!(await ensureNotificationPermission())) return false;
  await Notifications.scheduleNotificationAsync({
    content: { title: "마감 D-3", body: title, data: { notice_id: noticeId } },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL, seconds: 5 },
  });
  return true;
}
