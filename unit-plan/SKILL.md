---
name: unit-plan
description: 단위세대 평면도를 AutoCAD로 작도하는 작업을 관리한다. 프로젝트 조건(프로파일)을 서브 스킬별로 묶어 사용자에게 확정받고, 표준 → 조닝 → 벽 → 예약(주방·UBR) → 문·창 → 단열 → 주방·가구 → 마감 → 치수 → 주석 순으로 unit-plan-* 서브 스킬 규칙을 실행하며, 작업 폴더·model.json·CAD 작업 영수증·원본 비교를 관리한다. "단위세대 평면 그려줘", "84A 평면 작도", "조닝으로 세대평면 만들기", 참고 세대로 규칙 검증, 세대평면 수정 요청에 사용.
---

# 단위세대 평면 작도 — 관리 스킬

이 스킬은 형상을 직접 계산하지 않는다. 어떤 값을 사용자에게 물을지, 어떤 순서로 서브 스킬 규칙을 돌릴지, 결과를 어떻게 검증할지를 관리한다.

## 서브 스킬

| 단계 | 스킬 | 맡는 것 | 규칙 스크립트 |
|---|---|---|---|
| 0 | `unit-plan-standards` | 레이어·문자·치수·해치 표준, 템플릿 가져오기 | `upc:import` |
| 1 | `unit-plan-zoning` | 실 경계·실명 → 공간 모델 | `zoning_from_centerlines.py` |
| 2 | `unit-plan-walls` | 벽 구성·두께·접합·해치·중심선 | `run_reference_unit.build_walls`, `rectunion.py` |
| 3 | `unit-plan-kitchen-furniture` | 주방 조리대 벽 **예약** | `reserve_counter` |
| 3 | `unit-plan-bathroom` | UBR 배치 + 욕실 문 | `place_ubr` |
| 4 | `unit-plan-doors` | 나머지 문 | `place_doors` |
| 4 | `unit-plan-windows` | 창 | `place_windows` |
| 5 | `unit-plan-insulation` | 단열(외기직접·간접·코어) | `run_reference_unit.insulation` |
| 6 | `unit-plan-kitchen-furniture` | 싱크·쿡탑·식탁·세탁기 | `place_kitchen`, `place_washer` |
| 7 | `unit-plan-finish` | 마감선·바닥타일 | `run_reference_unit.finish_loops` |
| 8 | `unit-plan-dimensions` | MC 체인·실 안목 치수 | `mc_chains`, `chord` |
| 9 | `unit-plan-annotation` | 실명·주기·도곽 | — |

순서와 재실행 규칙은 [pipeline](references/pipeline.md)에 있다.

## 두 가지 작업 방식

`<skills>`는 설치 위치(`~/.claude/skills`)다. 예시로 드는 `jobs/…` 파일(설정·덤프·결과 DWG)은 설치 폴더에 복사되지 않고, 패키지 원본 `C:/Users/Planby Technologies/Desktop/2026/Autocad_mcp_test/unit-plan-skills/jobs/`에 있다.

### A. 참고 세대 기반 (검증된 경로)

기존 세대 블록이 있는 도면에서 시작한다.

1. **추출**: 세대 블록을 덤프하고(`scripts/dump-block.lsp`의 `upd:dump`), 실명을 세대 좌표로 옮긴다.
2. **조닝**: `unit-plan-zoning`으로 조닝을 만들고, 겹쳐 그린 그림을 보여 사용자 승인을 받는다.
3. **프로파일 제안**: 원본에서 창 방위·폭, 문 연결, UBR 짝, 주방 블록을 뽑아 제안한다. 예: `jobs/cj84b-20261026/derive_profile.py`.
4. **확정**: 제안값을 `AskUserQuestion`으로 묶어 묻고 확정한다.
5. **설정 파일**: `config.json`을 쓴다. 예: `jobs/cj84b-20261026/config_v005.json`. 키 설명은 `scripts/run_reference_unit.py` 맨 위 주석에 있다.
6. **계산**: `python -I <skills>/unit-plan/scripts/run_reference_unit.py config.json` → `model.json`, `ops/*.lsp`, `ops/run_all.lsp`.
7. **CAD 실행**: AutoCAD MCP에서 `up-cad.lsp`와 `dump-block.lsp`를 로드한 뒤 `run_all.lsp`를 로드한다. 각 단계 결과가 `DONE dbx`인지 확인한다.
8. **비교**: `upd:dump-ms`로 다시 읽고, `python -I <skills>/unit-plan/scripts/compare_reference.py config.json` → `comparison.md`. 겹친 그림으로 눈으로도 확인한다.

### B. 새 조닝에서 작도

닫힌 폴리라인 + 실명 조닝(또는 표·스케치)에서 시작한다.

1. [profile.template.json](references/profile.template.json)을 복사해 채운다.
2. 미확정 값은 서브 스킬별로 묶어 묻는다.
3. A와 같은 규칙 스크립트를 쓴다. 다만 벽 두께는 자동 실측 대신 프로파일 값으로 주고(`walls.overrides` 또는 assembly), 블록 방향은 회사 블록 라이브러리에서 측정한다.
4. 조닝 해석 절차는 `unit-plan-zoning`을 따른다.

## 지켜야 할 것

- **값의 상태 구분**: 프로파일 값마다 `status`를 단다(user_confirmed / project_confirmed / observed / proposed / unresolved). 관찰값([survey](references/survey.md), 원본 측정)은 선택지로만 보여주고 기본값으로 삼지 않는다. `unresolved` 값에 의존하는 요소는 그리지 않고 보고한다.
- **CAD 작업 방식**: [cad-runtime](references/cad-runtime.md)을 따른다.
  - 사용자가 열어 둔 문서에는 쓰지 않는다.
  - 작업 DWG는 `upc:new`로 만들고 `upc:run`(ObjectDBX, 영수증)으로 쓴다.
  - 같은 작업 ID를 다시 실행하지 말고 새 ID를 쓴다.
- **버전 관리**: `outputs/<세대>-v001.dwg`, `v002`… 로 올리고 이전 버전은 지우지 않는다.
- **규칙을 바꾼 뒤**: 이미 검증한 세대를 다시 계산해 결과가 바뀌지 않았는지 확인한다(회귀 검사). 예: `jobs/cj84a-20261026/regress84a.py`.

## 수정 요청

바뀌는 요소를 가진 단계부터 다시 실행하고, 그 뒤 단계 중 의존하는 것만 다시 돈다. 예를 들어 벽 위치가 바뀌면 벽 → 예약 → 문·창 → 단열 → 주방 → 마감 → 치수 순이다. 사용자가 CAD에서 손으로 바꾼 객체는 object-map과 비교해 보존하고, 충돌하면 위치와 선택지를 제시한다.

## 완료 보고

다음을 구분해서 쓴다.
- 생성 파일 경로
- 단계별 영수증
- DBX 재읽기 결과
- 원본 비교표(있으면)
- 사용자가 화면에서 확인해야 할 항목
- 미해결 목록

근거 없는 "완료"는 쓰지 않는다. 지금까지의 검증 결과는 [validation-log](references/validation-log.md)에 있다.
