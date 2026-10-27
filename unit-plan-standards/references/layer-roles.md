# 역할 → 레이어 표

`aa_code`와 `short`는 조사한 프로젝트에서 가장 많이 쓰인 이름으로 만든 기본안(`proposed`)이다. 색은 ACI 번호. 마지막 열은 실제 관찰된 이름(P1~P6, 자세한 내용은 `unit-plan/references/survey.md`).

| 역할 | aa_code | short | 색 | 선종류 | 관찰된 이름 |
|---|---|---|---|---|---|
| `wall.concrete` | AA-WAXM-CONC | A-CON | 7 | CONTINUOUS | AA-WAXM-CONC, A-CON, A-WALL, CONC, WAL, AA-XXXX-CONC |
| `wall.masonry` | AA-WAXM-BRCK | A-WALB | 7 | CONTINUOUS | AA-WAXM-BRCK, A-WALB |
| `wall.drywall` | AA-WAXM-DRYW | A-GIP | 7 | CONTINUOUS | AA-WAXM-DRYW, AA-WAXM-GYPB, WAL_DRY, A-GIP, 인테리어 경량벽체 |
| `wall.hatch` | AA-XXXX-PATT | A-HAT | 8 | CONTINUOUS | AA-XXXX-PATT, A-HAT, A_HAT, AA-XXXX-조적해치 |
| `grid.mc` | AA-XXXX-MC | A-MC | 1 | CENTER | A-MC, MC, mc, AA-XXXX-MC, CEN_WALL |
| `grid.center` | AA-XXXX-CNTL | A-CEN | 1 | CENTER | A-CEN, AA-XXXX-CNTL, CEN_CON |
| `insulation` | AA-XXXX-INSL | A-INS | 4 | CONTINUOUS | AA-XXXX-INSL, AA-XXXX-INS, A-INS, INS |
| `insulation.dewproof` | AA-WAXS-DEWP | A-INS-결로 | 4 | CONTINUOUS | 0_결로방지단열재 (W 450), 결로방지재-벽, AA-WAXS-DEWPROOFING, 2-결로방지 |
| `finish.line` | AA-XXXX-FINL | A-FIN | 8 | CONTINUOUS | AA-XXXX-FINL, AA-WAXS-FINL, A-FIN, FIN |
| `door` | AA-DWXM-DOOR | A-DOOR | 3 | CONTINUOUS | AA-DWXM-DOOR, A-DOOR, DOOR, SINA-F-DOOR |
| `door.frame` | AA-DWXM-DOOR | A-DOOR | 3 | CONTINUOUS | SINA-F-FRAME, I-F-DOOR FRAME |
| `window` | AA-DWXM-WIND | A-WIN | 4 | CONTINUOUS | AA-DWXM-WIND, A-WIND1, A-WIN, WIN |
| `window.tag` | AA-DWXM-SYMB | A-창호부호 | 2 | CONTINUOUS | A-창호부호, A04-TEXT-창호, WINSYM-1 |
| `sanitary` | AA-FFXM-SANI | F-TOILET | 6 | CONTINUOUS | AA-FFXM-SANI, F-TOILET, TOIL, 위생기구, 건축-위생(기구) |
| `bath.ubr` | AA-FFXM-UBR | A-UBR | 6 | CONTINUOUS | UBR, LH-UBR, UBR내부자재, AA-XXXX-UBR |
| `kitchen` | AA-FFXM-KICH | F-KIT | 6 | CONTINUOUS | AA-FFXM-KICH, F-KIT |
| `furniture` | AA-FFXM-FURN | FUR | 8 | CONTINUOUS | AA-FFXM-FURN, FUR, FUR_가구, 설치가구 |
| `furniture.option` | AA-XXXX-FUR-HID | FUR-HID | 8 | HIDDEN | AA-XXXX-FUR-HID, AA-XXXX-FUR-NOMO, 미설치가구, AA-FFXM-FUR-OPTION |
| `appliance` | AA-FFXM-APPL | FUR_가전 | 8 | CONTINUOUS | FUR_가전 |
| `utility` | AA-XXXX-SYMB | A-SYM | 2 | CONTINUOUS | 수전, AA-XXXX-SYMB, SYM, 설비-FD |
| `floor.pattern` | AA-FLXK-PATT | A-TILE | 8 | CONTINUOUS | AA-FLXK-PATT, AA-FLXK-PAT1, A-TILE, 바닥타일 |
| `stair_rail` | AA-SSXM-STRS | A-난간 | 3 | CONTINUOUS | AA-SSXM-STRS, AA-SSXS-HRAL, STAIR, A-난간 |
| `dim` | AA-XXXX-DIMS | DIM | 1 | CONTINUOUS | AA-XXXX-DIMS, DIM, 치수선 |
| `room.name` | AA-MKXS | 실명 | 2 | CONTINUOUS | AA-MKXS, XX-MKXS, 실명, A12-문자-실명 |
| `level` | AA-XXXX-ELEV | A-레벨 | 2 | CONTINUOUS | A-레벨, A13-심볼-레벨, AA-XXXX-ELEV |
| `note` | AA-XXXX-NOTE | A-TEXT | 2 | CONTINUOUS | AA-XXXX-NOTE, AA-XXXX-TEXT, A-ANNO-TEXT, TEXT-2 |
| `sheet` | AA-BORD-FORM | X-SHEET | 7 | CONTINUOUS | AA-BORD-FORM, AA-BORD-TEXT, X-SHEET, XR-FORM |
| `nonplot` | DEFPOINTS | DEFPOINTS | 8 | CONTINUOUS | defpoints, Defpoint, DEFPOINT, Def-PrintX (작도 보조) |

## 재료 → 해치 (관찰 기반 기본안, 모두 `proposed`)

| 재료 | 패턴 | 축척 | 각도 | 근거 |
|---|---|---|---|---|
| 철근콘크리트 단면 | AR-CONC | 0.5 | 0 | P3 `AA-XXXX-PATT` |
| 조적 | _USER (평행선) | 60 | 45 | P3, P6 |
| 단열재(해치형) | DASH | 10 | 0 | P4 `INS`, P6 `AA-XXXX-PAT3` |
| 압출법 단열재 | ANSI37 | 2 | 0 | P5 |
| 결로방지 단열재 | ANSI31 | 15~25 | 0/90 | P1, P3 단열평면 |
| 욕실/발코니 방수 표시 | CROSS | 6~8 | 0 | P1, P3, P6 단열평면 |
| 바닥 타일 | _USER (격자) | 300 | 0+90 | P4, P6 |

`_USER` 패턴은 `vla-addhatch`에서 패턴타입 `acHatchPatternTypeUserDefined`, 간격 = PatternSpace, 격자는 `PatternDouble`.

## 치수 스타일

| 용도 | 관찰 이름 | 비고 |
|---|---|---|
| MC 치수 | MCDIM-50, MCDIM_40, SDIM-40-MC | 도면 축척 1/50·1/40 |
| 안목(내부) 치수 | HAUD-안목치수, HAUD-100, DIM-50, DIM_40 | |
| 외부 치수 | HAUD-외부(50), 외부100-win, 외부80-WIN | |

스타일 이름의 숫자를 축척으로 믿지 말고, 실제 DIMSCALE·문자높이·화살표를 읽어서 정한다(A31 사례: 이름 SDIM-40인데 ScaleFactor 30).
