"""Write object-map.json and review.json for the 84A test run."""
import json, collections
JOB = r"C:\temp\cj84a"
m = json.load(open(JOB + r"\model.json", encoding="utf-8"))
rows = [l.rstrip("\n").split("\t") for l in open(JOB + r"\handles.tsv", encoding="utf-8")]

STEP = {"CONC": "wall", "WAL": "wall", "WAL_DRY": "wall", "A_HAT": "wall", "CEN_CON": "wall", "CEN_WALL": "wall",
        "DOOR": "door", "SINA-F-FRAME": "door", "WIN": "window", "INS": "insulation", "FIN": "finish", "바닥타일": "finish",
        "DIM": "dimension", "실명": "annotation", "AA-XXXX-UBR": "bathroom", "수전": "bathroom",
        "FUR": None, "FUR_가구": "kitchen_furniture", "FUR_가전": "kitchen_furniture", "F-FUR-설치": "kitchen_furniture",
        "ETC": "kitchen_furniture", "A-ELE8": "kitchen_furniture", "0": None}
objmap = collections.defaultdict(list)
for h, lay, typ, name in rows:
    step = STEP.get(lay)
    if lay == "FUR": step = "bathroom" if name.startswith("UBR") else "kitchen_furniture"
    if lay == "0": step = "window" if name.startswith("실외기창") else "kitchen_furniture"
    objmap[step or "unknown"].append({"handle": h, "layer": lay, "type": typ.replace("AcDb", ""), "block": name or None})
json.dump({"dwg": "outputs/cj84A-basic-v001.dwg", "by_step": objmap}, open(JOB + r"\object-map.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

cnt = {k: len(v) for k, v in objmap.items()}
review = {
  "job": "청주 월명 84A 기본형 — unit-plan 전체 시험 (2026-10-26)",
  "output": "outputs/cj84A-basic-v001.dwg",
  "verification_method": "ObjectDBX 재읽기 + 원본 U-84A(기본) 블록과 SVG 겹침 비교. AutoCAD 화면 육안 확인은 아직 안 함",
  "coverage": {
    "standards": {"status": "pass", "checks": ["원본에서 레이어 23, 치수스타일 MCDIM-50/HAUD-100, 문자스타일 HAUD01 복사"],
                  "unresolved": ["std-001 생성 LISP 괄호 1개 초과 → 작업은 DONE, 생성기 수정함"]},
    "zoning": {"status": "pass", "checks": ["실 13 + 고정(코어·PS) 5, 열린 경계 없음(코어 제외)", "가상경계 4개(사용자 승인)"],
               "unresolved": ["발코니2가 1.33㎡로 작게 잡힘 — 원본 바닥타일은 북측 6345~14685 범위(약 11㎡). 북측 다용도 공간 실명 확인 필요",
                              "1차 제안안의 남측 발코니 분할은 중심선 과다연장 오인(추출 오류) → 수정 후 19.5㎡ 연속"]},
    "wall": {"status": "pass", "handles": cnt.get("wall"), "checks": ["벽 34개(실측 오프셋 22, 레이어 기본값 12)", "RC 5 / 조적 12(+ANSI31) / 경량 13 루프", "창·문 15개 개구부 모두 벽에 매칭"],
             "unresolved": ["남측 발코니 외곽(y=0)이 원본은 벽 조각, 결과는 연속 RC 200", "기본값 두께 벽 12개(W5,W10…)는 실측 근거 없음"]},
    "door_window": {"status": "pass", "handles": cnt.get("door", 0) + cnt.get("window", 0),
                    "checks": ["문 8, 창 7 원본 객체 그대로 복사 — 원본 bbox와 일치"],
                    "unresolved": ["원본 재현 모드라 문 폭·개폐 규칙 로직은 이번에 검증 안 됨"]},
    "insulation": {"status": "pass", "handles": cnt.get("insulation"),
                   "checks": ["직접외기 T155 5루프, 간접외기·코어 T110 12루프", "창 위치에서 끊김(ins-002에서 수정)"],
                   "unresolved": ["원본은 거실·침실 발코니측 벽에 155(간접 규칙으론 110) — 프로젝트 기준 확인 필요",
                                  "코어측 110은 가정(proposed)", "결로방지 단열재 폭 미확인 → 미작도"]},
    "bathroom": {"status": "pass", "handles": cnt.get("bathroom"), "checks": ["UBR 공용 1500x2200, 부부 1600x2300, 수전·FD 원본 복사"]},
    "kitchen_furniture": {"status": "pass", "handles": cnt.get("kitchen_furniture"),
                          "checks": ["싱크·쿡탑·식탁·세탁기·피난구 심볼 원본 복사(쿡탑은 원본 삽입점 비정상 → 객체 복사로 위치 보존)"]},
    "finish": {"status": "pass", "handles": cnt.get("finish"),
               "checks": ["실별 마감 루프 13", "발코니1·2·피난구 바닥타일 _USER 300 격자"],
               "unresolved": ["마감 두께(석고보드 등) 미반영 → 안목이 원본보다 넓음(거실 4520 vs 원본 4420)"]},
    "dimension": {"status": "partial", "handles": cnt.get("dimension"),
                  "checks": ["MC 체인 합 일치(남 14630, 동 10335), 문자 재정의 없음", "실 안목 12개(dim-002에서 ㄱ자 실 측정 오류 수정)"],
                  "unresolved": ["원본 MC 치수는 창·벽 단위 상세 체인(NDIM40-in) — 이번 결과는 벽 중심선 체인만", "원본 MC 선(MC 레이어)과 중심선(CEN_*) 기준 차이"]},
    "annotation": {"status": "partial", "handles": cnt.get("annotation"), "checks": ["실명 14, HAUD01 h120"],
                   "unresolved": ["도곽·표제 미작도(profile.annotation.sheet 미정)", "실명 위치는 원본 좌표 사용(자동 배치 로직 미검증)"]},
  },
  "skill_fixes_made_during_run": [
    "unit-plan-zoning/scripts/zoning_from_centerlines.py 신규 + 중심선 과다연장 트림 + 동일선 틈 연결",
    "unit-plan/scripts/up-cad.lsp: upc:import 추가",
    "unit-plan/scripts/dump-block.lsp 신규: upd:dump / upd:dump-ms / upd:copy-parts",
  ],
  "entity_counts": cnt,
}
json.dump(review, open(JOB + r"\review.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(cnt)
