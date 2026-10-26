import type { Tags } from "./api";

export const INTERESTS: { key: string; label: string }[] = [
  { key: "dev_it", label: "개발·IT" },
  { key: "ai_data", label: "AI·데이터" },
  { key: "design", label: "디자인" },
  { key: "scholarship", label: "장학금" },
  { key: "startup", label: "창업" },
  { key: "language_abroad", label: "어학·해외" },
  { key: "internship", label: "현장실습" },
];

export const TOPIC_LABEL: Record<string, string> = {
  dev_it: "개발·IT",
  ai_data: "AI·데이터",
  design: "디자인",
  scholarship: "장학",
  startup: "창업",
  language_abroad: "어학·해외",
  internship: "현장실습",
  contest: "공모전",
  academic: "학사",
};

export const CAMPUS_LABEL = { seoul: "서울캠퍼스", global: "국제캠퍼스" } as const;

/** 앱 기기에만 저장되는 정보. 서버로는 profileToTags() 결과만 간다. */
export interface Profile {
  name: string;
  grade: number | null;
  campus: "seoul" | "global" | null;
  college: string | null;
  dept: string | null;
  gpa: string;
  lastGpa: string;
  credits: string;
  income: number | null;
  interests: string[];
  intentText: string;
}

export const emptyProfile: Profile = {
  name: "",
  grade: null,
  campus: null,
  college: null,
  dept: null,
  gpa: "",
  lastGpa: "",
  credits: "",
  income: null,
  interests: [],
  intentText: "",
};

const num = (s: string) => {
  const v = parseFloat(s.replace(",", "."));
  return Number.isFinite(v) ? v : null;
};

/** 정확한 학점은 구간으로 내린다: 3.87 → 3.5, 78학점 → 70 */
export function profileToTags(p: Profile): Tags {
  const t: Tags = { interests: p.interests };
  if (p.campus) t.campus = p.campus;
  if (p.college) t.college = p.college;
  if (p.dept) t.dept = p.dept;
  if (p.grade) t.grade = p.grade;
  const g = num(p.gpa);
  if (g !== null && g >= 0 && g <= 4.5) t.gpa_floor = Math.floor(g * 2) / 2;
  const lg = num(p.lastGpa);
  if (lg !== null && lg >= 0 && lg <= 4.5) t.last_gpa_floor = Math.floor(lg * 2) / 2;
  const c = num(p.credits);
  if (c !== null && c >= 0 && c <= 200) t.credits_floor = Math.floor(c / 10) * 10;
  if (p.income) t.income_band = p.income;
  return t;
}

export function profileLine(p: Profile | null) {
  if (!p) return "";
  return [p.campus ? CAMPUS_LABEL[p.campus] : null, [p.dept, p.grade ? `${p.grade}학년` : null].filter(Boolean).join(" ")]
    .filter(Boolean)
    .join(" · ");
}
