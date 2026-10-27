---
name: unit-plan-standards
description: 단위세대 평면 작도에 쓸 레이어 체계(역할→레이어 이름·색·선종류), 문자 스타일, 치수 스타일, 해치 패턴을 프로젝트별로 정하고 작업 DWG에 만든다. unit-plan의 0단계. 다른 unit-plan-* 스킬은 레이어 이름을 직접 쓰지 않고 이 스킬이 만든 역할 표를 쓴다.
---

# 단위세대 표준 (레이어·스타일·해치)

## 왜 따로 두나

조사한 6개 프로젝트는 레이어 **역할**은 같지만 **이름**이 다르다(`AA-WAXM-CONC` vs `A-CON` vs `CONC`). 한 프로젝트 안에서도 섞인다. 서브 스킬은 `wall.concrete` 같은 역할만 알고, 실제 이름은 이 스킬이 정한 `standards.layer_map`에서 찾는다.

## 사용자가 정할 것 (`profile.standards`)

| 항목 | 선택지 | 비고 |
|---|---|---|
| `layer_scheme` | `aa_code` / `short` / `custom` | 표준 기본표는 [layer-roles](references/layer-roles.md) |
| `layer_map` | 역할별 덮어쓰기 | 회사·발주처 표준이 있으면 그것을 우선 |
| `text_style` | SHX 또는 TTF, 폭계수 | 대상 PC에 실제로 있는 글꼴만. 관찰: `kosdichs.shx` 누락 사례 |
| `template_dwg` | 기존 프로젝트 DWG/DWT | 있으면 레이어·스타일을 거기서 복사 |
| 치수 스타일 | MC용 / 안목용 | 관찰 이름은 [layer-roles](references/layer-roles.md#치수-스타일) |

## 절차

1. 프로젝트 표준 문서나 템플릿이 있는지 묻는다. 있으면 ObjectDBX로 읽어 역할 표에 매핑한다(이름으로 추정한 매핑은 `proposed`로 두고 사용자 확인).
2. 없으면 `layer_scheme` 기본표에서 시작하고, 사용자가 바꾼 것만 `layer_map`에 남긴다.
3. `upc:run` 작업 ID `std-001`로 작업 DWG에 레이어(색·선종류·선가중치), 문자 스타일, 치수 스타일을 만든다. 선종류는 `acad.lin`/`acadiso.lin`에서 로드하고, 로드 실패는 기록한다.
4. `model.json`은 건드리지 않는다. 결과 역할 표를 `profile.json`의 `standards.layer_map`(status 포함)에 저장한다.

## 다른 스킬에 주는 것

- `role → layer` 표 (전 역할 목록은 [layer-roles](references/layer-roles.md))
- `material → hatch {pattern, scale, angle}` 표
- 문자 높이 기준: 도면 축척 1/50에서 실명 120~150, 주기 100~125, 치수문자는 치수스타일이 결정

## 구현 상태

- `upc:import`(`unit-plan/scripts/up-cad.lsp`): 참고 도면(템플릿)에서 config `layers.import` 레이어, 치수스타일, 문자스타일, 블록 정의(UBR 본체·패널, 주방 블록)를 작업 DWG로 복사한다. 결과는 `std-*.report.txt`에 남는다.
- 현재 실행기는 참고 도면의 레이어 이름을 그대로 쓴다(`CONC`, `WAL_DRY`, `FIN`…). 역할 → 레이어 매핑(`layer-roles.md`) 적용은 새 조닝 방식(B)에서 한다.

## 확인

DBX 재읽기로 레이어 수·이름·색, 문자/치수 스타일 존재를 확인하고 `review.json`의 `standards`에 기록한다. 대상 PC에 글꼴이 없어 대체된 경우 그 사실을 적는다.
