(upc:run "C:/temp/cj84a/outputs/cj84A-basic-v008.dwg" "C:/temp/cj84a/operations_v008" "bath-701" (quote (lambda (doc / ms o) (setq ms (vla-get-modelspace doc)) (setq o (vla-insertblock ms (upc:pt 1652.0 4148.0) "UBR 공용욕실 1500x2200" -1 1 1 0.000000)) (upc:set o "FUR")
 (setq o (vla-insertblock ms (upc:pt 11478.0 7917.0) "UBR 부부욕실 1600x2300" -1 1 1 0.000000)) (upc:set o "FUR")
 (setq o (vla-insertblock ms (upc:pt 152.0 4148.0) "A$C84b07bde" 1 1 1 0.000000)) (upc:set o "AA-XXXX-UBR")
 (setq o (vla-insertblock ms (upc:pt 10890.5 5569.5) "A$C4e4a4905" 1 1 1 0.000000)) (upc:set o "AA-XXXX-UBR"))))
