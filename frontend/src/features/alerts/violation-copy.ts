export function violationRuleLabel(ruleKeys: string[]): string {
  const labels: string[] = [];
  if (ruleKeys.some(key => key.startsWith("restricted_area_person"))) labels.push("Người trong phạm vi hạn chế");
  else if (ruleKeys.some(key => key.startsWith("zone_intrusion"))) labels.push("Xâm nhập vùng cấm");

  const missingHat = ruleKeys.includes("missing_ppe:hat");
  const missingVest = ruleKeys.includes("missing_ppe:vest");
  if (missingHat && missingVest) labels.push("Thiếu mũ bảo hộ và áo phản quang");
  else if (missingHat) labels.push("Thiếu mũ bảo hộ");
  else if (missingVest) labels.push("Thiếu áo phản quang");

  return labels.join(" · ") || "Vi phạm an toàn";
}

export function violationRuleItemLabel(ruleKey: string): string {
  if (ruleKey === "missing_ppe:hat") return "Thiếu mũ bảo hộ";
  if (ruleKey === "missing_ppe:vest") return "Thiếu áo phản quang";
  if (ruleKey.startsWith("zone_intrusion")) return "Xâm nhập vùng cấm";
  if (ruleKey.startsWith("restricted_area_person")) return "Người trong phạm vi hạn chế";
  return ruleKey;
}
