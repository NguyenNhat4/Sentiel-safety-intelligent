import {describe, expect, it} from "vitest";
import {violationRuleLabel, violationRuleItemLabel} from "./violation-copy";

describe("violation copy", () => {
  it("names each missing PPE item", () => {
    expect(violationRuleLabel(["missing_ppe:hat"])).toBe("Thiếu mũ bảo hộ");
    expect(violationRuleLabel(["missing_ppe:vest"])).toBe("Thiếu áo phản quang");
    expect(violationRuleLabel(["missing_ppe:hat", "missing_ppe:vest"]))
      .toBe("Thiếu mũ bảo hộ và áo phản quang");
  });

  it("translates persisted audit rule keys", () => {
    expect(violationRuleItemLabel("missing_ppe:hat")).toBe("Thiếu mũ bảo hộ");
    expect(violationRuleItemLabel("missing_ppe:vest")).toBe("Thiếu áo phản quang");
  });

  it("uses the restricted-area product wording", () => {
    expect(violationRuleLabel(["zone_intrusion:zone_01"])).toBe("Xâm nhập vùng cấm");
    expect(violationRuleItemLabel("zone_intrusion:zone_01")).toBe("Xâm nhập vùng cấm");
  });
});
