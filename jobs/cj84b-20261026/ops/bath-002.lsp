(upc:run "C:/temp/cj84b/outputs/cj84B-basic-v002.dwg" "C:/temp/cj84b/operations" "bath-002" (quote (lambda (doc / ms o hs h old) (setq ms (vla-get-modelspace doc)) (setq o (vla-insertblock ms (upc:pt 1652.0 4142.0) "UBR 공용욕실 1500x2200" -1 1 1 0.000000)) (upc:set o "FUR")
 (setq o (vla-insertblock ms (upc:pt 11528.0 7943.0) "UBR 부부욕실 1600x2300" -1 1 1 0.000000)) (upc:set o "FUR")
 (setq o (vla-insertblock ms (upc:pt 152.0 4142.0) "A$C84b07bde" 1 1 1 0.000000)) (upc:set o "AA-XXXX-UBR")
 (setq o (vla-insertblock ms (upc:pt 10940.5 5595.5) "A$C91691f5a" 1 1 1 0.000000)) (upc:set o "AA-XXXX-UBR"))))
