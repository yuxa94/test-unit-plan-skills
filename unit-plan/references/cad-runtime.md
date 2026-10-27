# CAD 실행 방법 (모든 서브 스킬 공통)

AutoCAD MCP(`autocad-mcp`, backend `file_ipc`)의 `system` → `execute_lisp`로 LISP를 보낸다. 2026-10-26에 AutoCAD LT 2026에서 확인한 사항을 기준으로 한다.

## 확인된 제약

| 현상 | 대응 |
|---|---|
| `drawing open`에 한글 경로를 주면 열린 것처럼 응답하지만 실제로는 열리지 않음 | 경로 확인은 항상 `DWGNAME`/`DWGPREFIX` 또는 Documents 목록으로. 입력 DWG는 ASCII 경로로 사본을 만든다 |
| 새로 연 문서에는 MCP 디스패처가 붙지 않음(LISP 네임스페이스가 문서별) | 활성 문서를 바꾸지 않는다. 작업 DWG는 `up-cad.lsp`로 다룬다 |
| 사용자가 저장하지 않은 문서를 여러 개 열어 둘 수 있음 | 그 문서들에 쓰지 않는다. 닫거나 저장하지 않는다 |
| `drawing create`(레거시)는 활성 도면을 지울 수 있음 | 사용 금지. `upc:new` 사용 |
| LISP 문자열 안의 한글은 그대로 전달됨(레이어명·문자 OK) | 결과 확인은 `upc:write-utf8`로 파일에 쓰고 읽는다(MCP 응답은 한글이 깨질 수 있음) |
| 큰 묶음 작업은 MCP 응답이 타임아웃될 수 있지만 AutoCAD 안에서는 계속 실행됨 | 타임아웃이면 재실행하지 말고 영수증 파일(.started/.done/.failed)과 결과를 확인 |

## 시작 준비

1. AutoCAD 명령줄에서 MCP 디스패처를 로드한다(세션마다 사용자가 직접): `(load "C:/Users/Planby Technologies/Desktop/2026/Autocad_mcp_test/autocad-mcp/lisp-code/mcp_dispatch.lsp")`. `system status`가 `ok`인지 확인한다.
2. 헬퍼를 로드한다. 설치 경로 기준:
   ```lisp
   (load "C:/Users/Planby Technologies/.claude/skills/unit-plan/scripts/up-cad.lsp")
   (load "C:/Users/Planby Technologies/.claude/skills/unit-plan/scripts/dump-block.lsp")
   ```
   두 파일은 ASCII 경로에 있어야 한다. 한글 경로는 `load`가 실패할 수 있다.
3. 작업 폴더도 ASCII 경로로 만든다(예: `C:/temp/<job>`). 입력 DWG가 한글 경로에 있으면 그 폴더로 사본을 만든다.
4. ObjectDBX ProgID는 `upc:dbx`가 자동으로 찾는다(AutoCAD 2026 = `ObjectDBX.AxDbDocument.26`). `dump-block.lsp`는 `.26`을 직접 쓰므로, 다른 버전이면 그 줄을 바꾼다.

## up-cad.lsp

```lisp
(load "C:/Users/Planby Technologies/.claude/skills/unit-plan/scripts/up-cad.lsp")
(upc:new "C:/jobs/84A/outputs/84A-v001.dwg" nil)            ; 새 작업 DWG (덮어쓰기 거부)
(upc:run "C:/jobs/84A/outputs/84A-v001.dwg"                 ; 대상 DWG
         "C:/jobs/84A/operations"                           ; 영수증 폴더(미리 생성)
         "walls-001"                                         ; 작업 ID: 영문/숫자/_/-
         '(lambda (doc / ms)
            (setq ms (vla-get-modelspace doc))
            (upc:layer doc "AA-WAXM-CONC" 7 nil)
            ;; ... model.json에서 계산한 형상 ...
            ))
```

- 대상 DWG가 편집기에 열려 있으면 그 문서 객체를 직접 쓰고(활성화하지 않음), 아니면 ObjectDBX로 열어 쓰고 같은 경로에 저장한다. 결과는 `"DONE dbx"` / `"DONE live"` / `"FAILED …"`.
- 같은 작업 ID의 영수증이 있으면 거부한다. 실패하면 원인을 확인하고 새 ID로 필요한 부분만 다시 한다.
- 도우미: `upc:pt`, `upc:layer`(없으면 생성), `upc:pline`(점 목록 → LWPOLYLINE), `upc:hatch`(외곽+섬 루프), `upc:set`(레이어 지정), `upc:write-utf8`.
- DBX로 쓴 도면은 화면 재생성 전이다. 확인은 (1) DBX 재읽기로 개수·레이어·핸들 대조, (2) 사용자가 DWG를 열어 육안 확인, 순서로 한다. 스크린샷이 필요하면 사용자가 해당 DWG를 열어 활성화한 뒤 `view get_screenshot`.
- 레이어는 할당 전에 같은 문서에 만들어야 한다(없는 레이어 지정 시 "키를 찾을 수 없습니다").

## 블록(부품) 삽입

라이브러리 DWG를 블록으로 가져올 때는 `(vla-insertblock ms (upc:pt x y) (findfile path) 1 1 1 rot)` 형태로, 경로는 `findfile` 결과(윈도우 경로)를 쓴다. 축척은 1. 반전은 X 축척 -1이 아니라 `mirror` 기록 후 `vla-mirror` 또는 축척 -1을 쓰되 model.json에 남긴다.

## 참고 도면 다루기 (`dump-block.lsp`)

| 함수 | 용도 |
|---|---|
| `(upd:dump src block out keep)` | 블록을 메모리 사본 원점에 넣고 펼쳐 LINE/PLINE/ARC/TEXT/INSERT(+bbox)/HATCH(+bbox)를 TSV로 덤프. `keep`=펼치지 않을 블록 패턴(예 `"~U-84A*"`) |
| `(upd:dump-ms dwg out)` | 작업 DWG 모형공간을 같은 형식으로 덤프(검증용) |
| `(upd:copy-parts doc src block layer-pat name-pat)` | 원본 세대 블록의 부품을 변환 그대로 작업 DWG에 복사 |
| `(upc:import doc src layers dimstyles textstyles blocks)` | 레이어·치수/문자 스타일·블록 정의 복사 |

모두 원본을 저장하지 않는다. 생성한 LISP는 실행 전에 괄호 균형을 검사한다. 닫는 괄호가 남으면 앞 작업만 실행되고 그 뒤 작업은 실행되지 않는다.

`run_reference_unit.py`가 만든 `ops/run_all.lsp`는 `upc:new`와 10개 단계를 차례로 로드하고, 결과 목록(`UPC_CREATED …`, `DONE dbx` × 10)을 돌려준다. 하나라도 `FAILED` 또는 `UPC_REJECT…`이면 그 영수증을 확인한다. 다시 실행하려면 config의 `op_suffix`와 `out_dwg`를 새 버전으로 바꾼다.

## Python 실행

Python 스크립트는 `python -I`(격리 모드)로 실행한다. 격리 모드에서는 `PYTHONIOENCODING`이 무시되므로, 스크립트가 한글을 출력하려면 `sys.stdout.reconfigure(encoding="utf-8")`이 필요하다(실행기·비교 스크립트에는 들어 있음). 필요한 라이브러리는 표준 라이브러리뿐이다. shapely·matplotlib는 쓰지 않는다.

## 읽기 전용 조사

`survey-dbx.lsp`의 `(up:analyze "<dwg>" "<name>")`는 블록을 펼쳐 `C:/temp/up_out/<name>.tsv`로 집계한다(출력 폴더 미리 생성). 참고 도면 분석용이며 쓰기는 하지 않는다.
