# unit-plan-skills

단위세대 평면도를 AutoCAD(LT 포함)에서 작도하는 Claude Code 스킬 묶음이다. 관리 스킬 1개와 요소별 서브 스킬 11개로 이루어져 있고, 서브 스킬은 각자 규칙 스크립트를 가진다. 2026-10-26~27에 기존 단일 스킬 `unit-plan-agent/unit-plan-cad`를 대체하려고 만들었다. 기존 폴더는 수정하지 않았다.

## 구성

| 스킬 | 역할 | 규칙 스크립트 |
|---|---|---|
| `unit-plan` | 관리: 프로파일 확정, 순서, CAD 실행, 비교·보고 | `run_reference_unit.py`, `compare_reference.py`, `up-cad.lsp`, `dump-block.lsp`, `rectunion.py`, `upgeom.py` |
| `unit-plan-standards` | 레이어·문자·치수 스타일·해치, 템플릿 가져오기 | (`upc:import`) |
| `unit-plan-zoning` | 실 경계·실명 → 공간 모델 | `zoning_from_centerlines.py` |
| `unit-plan-walls` | 벽 구성·두께(자동 실측)·접합·해치 | (`run_reference_unit.build_walls`) |
| `unit-plan-doors` | 문: 복도·홀 우선, 실 모서리/가운데 위치, 동률 기준 | `place_doors.py` |
| `unit-plan-windows` | 창: 실별 방위·폭 | `place_windows.py` |
| `unit-plan-insulation` | 단열: 외기직접·간접·코어 판정 | (`run_reference_unit.insulation`) |
| `unit-plan-bathroom` | UBR 실제 외곽선 배치 + 욕실 문 | `place_bathroom.py` |
| `unit-plan-kitchen-furniture` | 조리대 예약, I·L형 주방, 세탁기 | `place_kitchen.py` |
| `unit-plan-finish` | 마감선·바닥타일 | (`run_reference_unit.finish_loops`) |
| `unit-plan-dimensions` | MC 체인·실 안목 치수 | (`run_reference_unit.mc_chains`) |
| `unit-plan-annotation` | 실명 (주기·도곽은 미구현) | — |

공통 문서는 `unit-plan/references/`에 있다.

| 문서 | 내용 |
|---|---|
| `pipeline.md` | 실행 순서. 예약(주방·UBR)을 문·창보다 먼저 한다 |
| `profile.template.json` | 사용자가 정할 값 전체 |
| `model-contract.md` | model.json 구조 |
| `cad-runtime.md` | AutoCAD LT·MCP 제약과 ObjectDBX 작성 방법 |
| `survey.md` + `evidence/` | HAUD 6개 프로젝트 단위세대 조사 |
| `validation-log.md` | 청주 84A·84B 검증 이력과 각 규칙의 근거 |

## 설치

12개 스킬 폴더를 `~/.claude/skills/`에 같은 부모 아래로 복사한다. 서브 스킬과 스크립트가 서로를 상대 경로로 찾기 때문이다. `jobs/`는 설치하지 않는다.

```powershell
$src = "C:\Users\Planby Technologies\Desktop\2026\Autocad_mcp_test\unit-plan-skills"
$dst = "$env:USERPROFILE\.claude\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
Get-ChildItem $src -Directory -Filter "unit-plan*" | ForEach-Object {
  robocopy $_.FullName (Join-Path $dst $_.Name) /MIR /XD __pycache__ /NFL /NDL /NJH /NJS | Out-Null }
```

이 폴더(`unit-plan-skills`)가 원본이다. 규칙을 고친 뒤에는 위 명령으로 다시 설치한다.

필요한 것:
- AutoCAD 또는 AutoCAD LT 2024 이상(Visual LISP ActiveX·ObjectDBX). 검증은 LT 2026에서 했다.
- `autocad-mcp` 서버(`file_ipc` 백엔드). 세션마다 AutoCAD에서 `mcp_dispatch.lsp`를 로드해야 한다.
- Python 3.10 이상. 표준 라이브러리만 쓴다.

## 빠른 시작 (참고 세대 기반)

```bash
python -I ~/.claude/skills/unit-plan/scripts/run_reference_unit.py C:/temp/<job>/config.json
```

AutoCAD MCP `execute_lisp`로 다음을 실행한다.

```lisp
(load "C:/Users/Planby Technologies/.claude/skills/unit-plan/scripts/up-cad.lsp")
(load "C:/Users/Planby Technologies/.claude/skills/unit-plan/scripts/dump-block.lsp")
(load "C:/temp/<job>/ops/run_all.lsp")
(upd:dump-ms "C:/temp/<job>/outputs/<unit>-v001.dwg" "C:/temp/<job>/job_ms.tsv")
```

비교:

```bash
python -I ~/.claude/skills/unit-plan/scripts/compare_reference.py C:/temp/<job>/config.json
```

`config.json` 예시는 `jobs/cj84b-20261026/config_v005.json`이다. 덤프·조닝·프로파일 제안 순서는 `unit-plan/SKILL.md`의 "방식 A"를 따른다.

## 검증 결과 (청주 월명, 규칙 배치 vs 원본)

| | 84A 기본형 (v010) | 84B 기본형 (v005) |
|---|---|---|
| 문 같은 벽 | 8/8, 중심 차 ≤ 135mm | 8/8, 중심 차 ≤ 155mm |
| 창 같은 벽·같은 폭 | 7/7 | 7/7 |
| UBR | ≤ 53mm | ≤ 63mm |
| 주방 | I형, 싱크 +160 / 쿡탑 +690 | L형, 싱크 (+40, +80) / 쿡탑 (-50, +10) |
| 세탁기 | (-260, -50) | (-70, -55) |

84B는 84A용으로 만든 규칙을 그대로 쓰고, 프로파일만 84B 원본 값으로 바꿔 돌렸다. 이력은 `unit-plan/references/validation-log.md`에 있다.

## 한계 (미구현)

- 습식 욕실 기구 배치, ㄷ자 주방, 냉장고 자리, 설비 심볼·가구
- 결로방지 단열재, 마감 두께, 방수 표시
- 개구부·외부 상세 치수 체인, 주기·도곽, 창호부호
- 비직교 벽
- 화면 육안 확인: ObjectDBX로 쓴 도면은 사용자가 AutoCAD에서 열어 확인해야 한다

## 폴더

```
unit-plan-skills/
  README.md
  unit-plan/            관리 스킬 + 공용 scripts/, references/
  unit-plan-*/          서브 스킬 (SKILL.md, scripts/, references/)
  jobs/                 검증 작업 (설치 대상 아님)
    cj84a-20261026/     청주 84A v001~v010
    cj84b-20261026/     청주 84B v001~v005
```
