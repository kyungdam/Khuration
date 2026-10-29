// 폰 캘린더에 공지 마감일을 종일 일정으로 넣는다 (알림 설정에서 고른 'N일 전'마다 알림, 기본 7·3·1일 전).
// SDK 58의 새 Calendar API는 Expo Go에서 안 되므로, Expo Go에 들어 있는 legacy API를 쓴다.
import * as Calendar from "expo-calendar/legacy";
import { Platform } from "react-native";

const DEFAULT_ALARM_DAYS = [7, 3, 1];

/** 넣은 알림의 'N일 전' 목록을 돌려준다 (당일 0과 잘못된 값은 뺀다) */
export async function addDeadlineToPhoneCalendar(
  title: string,
  date: string,
  url: string,
  alarmDays: number[] = DEFAULT_ALARM_DAYS,
): Promise<number[]> {
  const { status } = await Calendar.requestCalendarPermissionsAsync();
  if (status !== "granted") throw new Error("캘린더 권한을 허용해야 폰 캘린더에 넣을 수 있어요");

  let calendarId: string | undefined;
  if (Platform.OS === "ios") {
    calendarId = (await Calendar.getDefaultCalendarAsync()).id;
  } else {
    const cals = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
    calendarId = (cals.find((c) => c.allowsModifications && c.isPrimary) ?? cals.find((c) => c.allowsModifications))?.id;
  }
  if (!calendarId) throw new Error("쓸 수 있는 캘린더가 없어요 (구글 계정 캘린더를 확인해 주세요)");

  const days = [...new Set(alarmDays.filter((d) => Number.isInteger(d) && d > 0 && d <= 30))].sort((a, b) => b - a);
  const [y, m, d] = date.split("-").map(Number);
  await Calendar.createEventAsync(calendarId, {
    title: `[마감] ${title}`,
    startDate: new Date(y, m - 1, d),
    endDate: new Date(y, m - 1, d + 1),
    allDay: true,
    notes: url || undefined,
    // relativeOffset: 일정 시작(마감일 0시) 기준 분, 음수면 그만큼 앞에 울린다
    alarms: days.map((n) => ({ relativeOffset: -60 * 24 * n })),
  });
  return days;
}
