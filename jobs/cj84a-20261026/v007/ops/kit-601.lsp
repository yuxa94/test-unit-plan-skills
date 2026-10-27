(upc:run "C:/temp/cj84a/outputs/cj84A-basic-v007.dwg" "C:/temp/cj84a/operations_v007" "kit-601" (quote (lambda (doc / ms o) (setq ms (vla-get-modelspace doc)) (upc:set (upc:pline ms '((6465.0 5285.0) (7115.0 5285.0) (7115.0 8415.0) (6465.0 8415.0)) t) "FUR")
 (setq o (vla-insertblock ms (upc:pt 6483.3 5385.0) "싱크" 1 1 1 0.000000)) (upc:set o "FUR")
 (setq o (vla-insertblock ms (upc:pt 196060.4 469026.0) "쿡탑" -1 1 1 1.570796)) (upc:set o "FUR")
 (setq o (vla-insertblock ms (upc:pt 8645.0 6252.5) "식탁-1300x800" 1 1 1 0.000000)) (upc:set o "FUR_가구"))))
