# model.json 계약 (서브 스킬 간 공유 데이터)

모든 서브 스킬은 `<job>/model.json`을 읽고 자기 섹션만 추가·수정한다. 좌표는 mm, 세대 로컬 좌표(원점 = 세대 MC 좌하단 권장). 각 객체에는 의미 ID를 붙이고, CAD에 그린 결과는 `object-map.json`에 `ID → handle[]`로 기록한다.

```jsonc
{
  "version": 1,
  "unit": { "type": "84A", "variant": "expanded", "envelope_id": "S0" },

  // unit-plan-zoning
  "spaces": [
    { "id": "S1", "name": "거실", "raw_name": "거 실", "polygon": [[0,0],[4200,0],[4200,5100],[0,5100]],
      "boundary_meaning": "wall_centerline", "kind": "room|balcony|wet|service|core|exterior",
      "heated": true }
  ],
  "edges": [
    // 공간 경계를 쪼갠 선분. 공유 경계는 한 번만.
    { "id": "E12", "a": [4200,0], "b": [4200,5100], "left": "S1", "right": "S2", "exterior": false }
  ],
  "fixed": [ { "id": "F1", "kind": "column|shaft|pd|core_wall", "polygon": [...] } ],

  // unit-plan-walls
  "walls": [
    { "id": "W7", "edges": ["E12"], "assembly": "DRY", "axis": [[4200,0],[4200,5100]],
      "core_mm": 100, "side_left": {"finish_mm": 10}, "side_right": {"finish_mm": 10},
      "outline": [[...]], "joins": [{"with":"W3","type":"T|L|X","at":[4200,0]}] }
  ],

  // unit-plan-doors / unit-plan-windows
  "openings": [
    { "id": "D3", "kind": "door|window", "wall": "W7", "from_room": "S1", "to_room": "S2",
      "center_offset_mm": 1200, "width_mm": 900, "rough_opening_mm": 900,
      "hinge": "start|end", "swing_into": "S2", "block": "침실 900", "tag": null }
  ],

  // unit-plan-insulation
  "insulation_runs": [
    { "id": "I2", "wall": "W1", "side": "left|right", "exposure": "exterior_direct", "thickness_mm": 120,
      "path": [[...]], "breaks": ["D1"], "dewproofing": [{"at":[...],"width_mm":450}] }
  ],

  // unit-plan-bathroom / unit-plan-kitchen-furniture
  "fixtures": [
    { "id": "B1-WC", "space": "S5", "kind": "toilet|basin|bath|shower|sink|cooktop|fridge|washer|boiler|panel|furniture",
      "block": "좌변기", "insert": [x,y], "rotation_deg": 90, "mirror": false, "anchor": "back_center", "optional": false }
  ],

  // unit-plan-finish
  "finish": { "lines": [ { "space": "S1", "offset_mm": 10 } ], "floor_patterns": [ { "space": "S5", "pattern": "_USER", "scale": 300 } ] },

  // unit-plan-dimensions
  "dimensions": [ { "id": "DM4", "chain": "mc_segment", "side": "south", "refs": ["W1","W7"], "style": "MCDIM-50" } ],

  // unit-plan-annotation
  "annotations": [ { "id": "T1", "kind": "room_name|level|note|tag", "space": "S1", "text": "거실", "at": [2100,2550] } ]
}
```

## 규칙

- 앞 단계의 ID는 바꾸지 않는다. 벽이 바뀌면 그 벽을 참조하는 opening / insulation / finish / dimension을 다시 계산해야 하므로 `unit-plan`이 해당 스킬을 재호출한다.
- 블록 삽입은 `block`, `insert`, `rotation_deg`, `mirror`, `anchor`(부품의 어느 점을 insert에 맞췄는지)를 모두 기록한다. 축척은 1 고정. 맞는 크기가 없으면 블록을 늘리지 않고 새 부품을 그린 뒤 `"authored": true`로 표시한다.
- 근거가 관찰값이면 해당 항목에 `"basis": "observed:P4"`처럼 출처를 남긴다.
