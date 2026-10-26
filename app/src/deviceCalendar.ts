import * as Calendar from "expo-calendar";
import { Platform } from "react-native";

/** 기기 기본 캘린더에 마감일 종일 일정 추가 (3일 전 알림 포함) */
export async function addDeadlineToCalendar(title: string, deadlineDate: string, url: string) {
  const { status } = await Calendar.requestCalendarPermissionsAsync();
  if (status !== "granted") throw new Error("캘린더 권한이 없어요");
  let calendarId: string | undefined;
  if (Platform.OS === "ios") {
    calendarId = (await Calendar.getDefaultCalendarAsync()).id;
  } else {
    const cals = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
    calendarId = (cals.find((c) => c.allowsModifications && c.isPrimary) ?? cals.find((c) => c.allowsModifications))?.id;
  }
  if (!calendarId) throw new Error("쓸 수 있는 캘린더가 없어요 (구글 계정 캘린더를 확인하세요)");
  const [y, m, d] = deadlineDate.split("-").map(Number);
  const start = new Date(y, m - 1, d);
  await Calendar.createEventAsync(calendarId, {
    title: `[마감] ${title}`,
    startDate: start,
    endDate: new Date(y, m - 1, d + 1),
    allDay: true,
    notes: url,
    alarms: [{ relativeOffset: -60 * 24 * 3 }],
  });
}
