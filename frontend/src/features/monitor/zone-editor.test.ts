import {describe, expect, it} from "vitest";
import type {MonitoringZone} from "../../types";
import {createZoneDraft, zoneGeometryConflict} from "./zone-editor";

const zone = (zoneId: string, left: number, right: number, order = 0): MonitoringZone => ({
  zone_id: zoneId,
  display_name: zoneId,
  machine_state: "stopped",
  enabled: true,
  order,
  points: [{x: left, y: 0.1}, {x: right, y: 0.1}, {x: right, y: 0.8}, {x: left, y: 0.8}],
});

describe("multi-zone editor domain", () => {
  it("creates another stopped draft without a zone-count constant", () => {
    const zones = Array.from({length: 20}, (_, index) => zone(`zone_${index + 1}`, index / 25, index / 25 + 0.02, index));
    expect(createZoneDraft(zones)).toMatchObject({
      zone_id: "zone_21", display_name: "Vùng 21", points: [], machine_state: "stopped", order: 20,
    });
  });

  it("rejects overlap, touching edges and containment", () => {
    expect(zoneGeometryConflict([zone("a", 0.1, 0.4), zone("b", 0.3, 0.6, 1)])).toEqual(["a", "b"]);
    expect(zoneGeometryConflict([zone("a", 0.1, 0.4), zone("b", 0.4, 0.7, 1)])).toEqual(["a", "b"]);
    const contained = zone("b", 0.2, 0.3, 1);
    contained.points = contained.points.map(point => ({...point, y: point.y === 0.1 ? 0.2 : 0.3}));
    expect(zoneGeometryConflict([zone("a", 0.1, 0.8), contained])).toEqual(["a", "b"]);
  });
});
