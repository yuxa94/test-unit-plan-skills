# 실행 순서와 의존 관계

```
standards ─┐
zoning ────┴─> walls ─> [예약] 주방 조리대 벽 ─> [예약] UBR + 욕실 문 ─> doors ─> windows
                                                                                   │
           annotation <─ dimensions <─ finish <─ kitchen·washer <─ insulation <────┘
```

| 단계 | 먼저 끝나야 하는 것 | 이 단계가 바뀌면 다시 실행할 것 |
|---|---|---|
| standards | — | 전부(레이어·스타일만이면 일괄 변경 가능) |
| zoning | — | 전부 |
| walls | zoning | 예약 이후 전부 |
| 주방 조리대 예약 | walls | doors, windows, kitchen |
| UBR + 욕실 문 | walls (개구부 없이 계산한 안목) | doors, windows, finish |
| doors | 예약 2개 | windows(같은 벽 경쟁), insulation, finish, dimensions |
| windows | doors | insulation, finish, dimensions, annotation(창호부호) |
| insulation | walls, 개구부 | finish, kitchen(안목 변화) |
| kitchen·washer | 개구부, 안목 | — |
| finish | walls, insulation | dimensions |
| dimensions | walls, finish | — |
| annotation | zoning | — |

## 왜 예약이 먼저인가

- **주방**: 조리대에는 개구부 없는 긴 벽이 필요하다. 예약 없이 문을 먼저 배치하면 팬트리 문이 그 벽을 잘랐다(청주 84A).
- **UBR**: 욕실 문은 UBR 문 위치에서 나온다. 문 규칙이 욕실 문을 먼저 정하면 UBR과 문 열림이 겹쳤다(청주 84A, 680×800).
- 예약된 구간과 욕실 문은 `taken`으로 문·창 규칙에 넘긴다. 안목은 벽·단열로만 정해지므로, 예약 단계는 개구부 없이 계산한 안목을 쓴다.

## 연쇄 변화의 예

조닝에서 주방 북쪽이 외기에서 발코니로 바뀌면 다음이 줄줄이 바뀐다. 단열 T155 → T110, 주방 안목 증가, 쿡탑·식탁 위치 이동(청주 84A v008). 그래서 조닝이나 벽을 바꾼 뒤에는 그 뒤 단계를 모두 다시 돈다.

## 질문 묶기

시작할 때 `unresolved` 항목을 스킬별로 모아 `AskUserQuestion` 한 번에 묻는다. 한 번에 최대 4개다. 각 질문의 첫 선택지는 원본·관찰 근거가 있는 권장안으로 두고, 근거를 설명에 적는다. 답이 없는 항목은 그 항목에 의존하는 요소만 보류하고 보고에 남긴다.

## 단계마다 하는 검증

1. model.json 갱신
2. `upc:run` 작성
3. 영수증 확인(`DONE dbx`)
4. DBX 재읽기(레이어별 개수, 블록 위치)
5. 원본이 있으면 비교표와 겹친 그림
