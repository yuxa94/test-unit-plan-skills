---
name: unit-plan-kitchen-furniture
description: 단위세대 주방(일자형·ㄱ자형 조리대, 싱크·쿡탑, 냉장고 자리, 식탁)과 세탁기를 배치한다. 조리대 벽을 문·창보다 먼저 예약하고, 프로파일의 배치 기준(쿡탑=창 쪽/싱크=거실 쪽, ㄱ자 코너 여유, 냉장고 위치)으로 원본 블록 방향을 맞춰 놓으며, 세탁기는 외벽·수전 기준으로 둔다. 가전·설비 심볼·가구 배치 절차도 포함.
---

# 주방·가전·설비·가구

## 사용자가 정할 것 (`profile.kitchen_furniture`)

| 키 | 뜻 | 청주 확정값 |
|---|---|---|
| `room` | 주방 실 | 주방/식당 |
| `layout` | `I`(일자) / `L`(ㄱ자) | 84A I, 84B L |
| `depth` | 조리대 깊이 | 650 |
| `arrangement` (I형) | `cooktop_window`(쿡탑=창 쪽 끝, 싱크=`living` 쪽 끝) / `sink_window`(싱크=창 쪽, 쿡탑은 `gap` 띄움) | cooktop_window, living [거실] |
| `gap` | 싱크–쿡탑 최소 간격 | 600 |
| `corner_offset` (L형) | 코너(깊이×깊이) 비운 뒤 싱크·쿡탑까지 거리 | 400 |
| `l_sink_leg` (L형) | `secondary`(싱크=꺾이는 벽, 쿡탑=긴 벽) / `primary` | secondary |
| `fridge_position` | `outside`(조리대 밖, 미작도) / `counter_far_end` / `pantry` | outside |
| `sink`, `cooktop`, `table` | 블록 이름(원본 인스턴스로 방향 측정) | 싱크, 쿡탑, 식탁-1300x800 |
| `washer.room` / `block` | 세탁기 실·블록 | 84A 발코니2, 84B 발코니3 / 세탁기-850 |
| `washer.priority` | `exterior_first`(외벽 → 수전 거리) / `water_first` | exterior_first |
| `washer.water_points` | 수전·배수 좌표(설비 입력) | 원본 수전·FD 중심 |
| 설비·가구 | 보일러·분전반·월패드, 가구 수준(없음/점선/전체) | 미정 |

## 규칙 (`scripts/place_kitchen.py`)

1. **`reserve_counter(model, cfg)` — 문·창보다 먼저 실행**
   - 주방의 가장 긴 내벽 구간을 예약한다. 150mm 이내 단차가 있는 벽은 한 구간으로 묶는다.
   - 예약 구간은 문·창 규칙의 `taken`으로 넘긴다. 예약하지 않으면 팬트리 문이 조리대 벽을 차지한다.
2. **`place_kitchen(model, cfg, lib, clear_loops, openings, …)`**
   - **I형**: 예약 벽 전체가 조리대다. `arrangement`에 따라 싱크·쿡탑 끝을 정하고, 각각 끝에서 100 띄운다. 창이 없거나 두 끝이 겹치면 보고한다.
   - **L형**:
     - 첫 번째 벽 = 예약 벽(쿡탑).
     - 두 번째 벽 = 첫 번째 벽 끝에서 실제 벽으로 꺾이는 쪽(싱크). 가상경계·개구부는 제외하고, 안목면 허용오차는 150mm다.
     - 코너 depth×depth는 비우고 `corner_offset` 띄운다. 꺾이는 벽이 짧으면 I형으로 되돌리고 보고한다.
   - **블록 방향**: 원본 인스턴스에서 가장 가까운 벽면으로 "벽 쪽 면"을 측정해 회전을 정한다. 블록은 늘리지 않는다. 블록이 없는 세대는 같은 프로젝트의 다른 세대 덤프(`lib_dumps`)에서 빌린다.
   - **냉장고**: `fridge_position`을 따른다.
   - **식탁**: 모든 조리대 앞 900 통로를 뺀 최대 사각형의 중앙에 두고, 긴 변을 조리대와 나란히 한다.
3. **`place_washer(model, wcfg, lib, clear_loops, …)`**
   - 세탁기가 안목에 들어가는 모든 회전·위치 중, 블록 등 쪽 면이 벽에 닿는 후보만 남긴다.
   - 순위: 외벽(등 쪽 벽 너머 400mm가 세대 밖) → 수전·배수 거리 → 코너(벽에 닿는 면 수). `water_first`면 앞의 두 기준 순서를 바꾼다.

## 설비·가구 (규칙 미구현 — 절차만)

- 가전·설비 심볼은 사용자가 지정한 실에 둔다. 지정이 없으면 제안 위치를 표로 보여준다(관례: 보일러=다용도실·발코니, 분전반·월패드=현관 근처 벽).
- 옵션·미설치 가구는 `furniture.option`(HIDDEN) 레이어에 그린다.
- 간섭 검사 대상은 문 원호, 창 앞, 욕실 기구, 다른 가구다.

## 확인

- 배치 객체가 해당 실 안목 안에 있음, 문 원호와 겹침 없음, 싱크·쿡탑이 조리대 안에 있음.
- `review.json.kitchen_furniture`: 배치 목록, 근거(`basis`), 미배치·미정 항목(냉장고 등).

검증 이력과 근거: `unit-plan/references/validation-log.md`.
