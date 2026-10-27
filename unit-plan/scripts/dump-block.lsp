;;; Read-only: insert a block definition at the origin of an in-memory ObjectDBX copy,
;;; explode it recursively, and dump the geometry to a UTF-8 TSV. The source DWG is never saved.
;;; Rows: TYPE \t LAYER \t data...   (coordinates in the block's own definition space)
(vl-load-com)

(defun upd:fmt (n) (rtos n 2 1))

(defun upd:bbox (e / a b)
  (if (vl-catch-all-error-p (vl-catch-all-apply 'vla-getboundingbox (list e 'a 'b)))
    "\t\t\t\t"
    (progn (setq a (vlax-safearray->list a) b (vlax-safearray->list b))
      (strcat "\t" (upd:fmt (car a)) "\t" (upd:fmt (cadr a)) "\t" (upd:fmt (car b)) "\t" (upd:fmt (cadr b))))))

(defun upd:row (e / on lay c out i n)
  (setq on (vla-get-objectname e) lay (vla-get-layer e))
  (cond
    ((= on "AcDbLine")
     (strcat "LINE\t" lay "\t" (upd:fmt (car (vlax-get e 'StartPoint))) "\t" (upd:fmt (cadr (vlax-get e 'StartPoint)))
             "\t" (upd:fmt (car (vlax-get e 'EndPoint))) "\t" (upd:fmt (cadr (vlax-get e 'EndPoint)))))
    ((= on "AcDbPolyline")
     (setq c (vlax-get e 'Coordinates) out "")
     (while c (setq out (strcat out (upd:fmt (car c)) "," (upd:fmt (cadr c)) ";") c (cddr c)))
     (strcat "PLINE\t" lay "\t" (if (= (vla-get-closed e) :vlax-true) "closed" "open") "\t" out))
    ((= on "AcDbArc")
     (strcat "ARC\t" lay "\t" (upd:fmt (car (vlax-get e 'Center))) "\t" (upd:fmt (cadr (vlax-get e 'Center)))
             "\t" (upd:fmt (vla-get-radius e)) "\t" (upd:fmt (* 57.29578 (vla-get-startangle e))) "\t" (upd:fmt (* 57.29578 (vla-get-endangle e)))))
    ((= on "AcDbCircle")
     (strcat "CIRCLE\t" lay "\t" (upd:fmt (car (vlax-get e 'Center))) "\t" (upd:fmt (cadr (vlax-get e 'Center))) "\t" (upd:fmt (vla-get-radius e))))
    ((member on '("AcDbText" "AcDbMText"))
     (strcat "TEXT\t" lay "\t" (vl-string-translate "\t\r\n" "   " (vla-get-textstring e))
             "\t" (upd:fmt (car (vlax-get e 'InsertionPoint))) "\t" (upd:fmt (cadr (vlax-get e 'InsertionPoint))) "\t" (upd:fmt (vla-get-height e))))
    ((= on "AcDbBlockReference")
     (strcat "INSERT\t" lay "\t" (vla-get-effectivename e) "\t" (upd:fmt (car (vlax-get e 'InsertionPoint))) "\t" (upd:fmt (cadr (vlax-get e 'InsertionPoint)))
             "\t" (upd:fmt (* 57.29578 (vla-get-rotation e))) "\t" (upd:fmt (vla-get-xscalefactor e)) "\t" (upd:fmt (vla-get-yscalefactor e))
             (upd:bbox e)))
    ((wcmatch on "*Dimension")
     (strcat "DIM\t" lay "\t" (upd:fmt (vla-get-measurement e))))
    ((= on "AcDbHatch")
     (strcat "HATCH\t" lay "\t" (vla-get-patternname e) "\t" (upd:fmt (vla-get-area e)) (upd:bbox e)))
    (t (strcat "OTHER\t" lay "\t" on))))

;; keep: list of block names (wcmatch patterns) that must NOT be exploded (doors, windows, fixtures)
(defun upd:explode-all (obj depth keep / res sub nm)
  (setq nm (if (= (vla-get-objectname obj) "AcDbBlockReference") (vla-get-effectivename obj) ""))
  (if (and (= (vla-get-objectname obj) "AcDbBlockReference") (< depth 6)
           (not (and keep (wcmatch nm keep))))
    (progn
      (setq sub (vl-catch-all-apply 'vlax-invoke (list obj 'Explode)))
      (if (vl-catch-all-error-p sub)
        (list obj)
        (progn
          (vla-delete obj)
          (apply 'append (mapcar '(lambda (s) (upd:explode-all s (1+ depth) keep)) sub)))))
    (list obj)))

;; Dump the model space of a (job) DWG without exploding, same row format. Read-only.
(defun upd:dump-ms (src out / d rows f)
  (setq d (vla-getinterfaceobject (vlax-get-acad-object) "ObjectDBX.AxDbDocument.26"))
  (vla-open d src :vlax-true)
  (vlax-for e (vla-get-modelspace d)
    (setq r (vl-catch-all-apply 'upd:row (list e)))
    (if (not (vl-catch-all-error-p r)) (setq rows (cons r rows))))
  (vlax-release-object d)
  (setq f (open out "w" "utf8"))
  (foreach r (reverse rows) (write-line r f))
  (close f)
  (length rows))

;; Copy parts (nested block references) of a reference unit block into DOC unchanged.
;; The reference unit is inserted at the origin of an in-memory copy and exploded one level,
;; so copied parts keep their exact local transforms (no rotation/mirror reconstruction).
;; layer-pat / name-pat: wcmatch patterns. Returns list of "handle|name|layer".
(defun upd:copy-parts (doc src block layer-pat name-pat / s ms ref ents sel out)
  (setq s (vla-getinterfaceobject (vlax-get-acad-object) "ObjectDBX.AxDbDocument.26"))
  (vla-open s src :vlax-true)
  (setq ms (vla-get-modelspace s))
  (setq ref (vla-insertblock ms (vlax-3d-point 0 0 0) block 1 1 1 0))
  (setq ents (vlax-invoke ref 'Explode))
  (foreach e ents
    (if (and (= (vla-get-objectname e) "AcDbBlockReference")
             (wcmatch (vla-get-layer e) layer-pat)
             (wcmatch (vla-get-effectivename e) name-pat))
      (setq sel (cons e sel))))
  (if sel
    (foreach c (vlax-safearray->list (vlax-variant-value (vla-copyobjects s (upc:objarray sel) (vla-get-modelspace doc))))
      (setq out (cons (strcat (vla-get-handle c) "|" (vla-get-effectivename c) "|" (vla-get-layer c)) out))))
  (vlax-release-object s)
  (reverse out))

;; keep-depth0 = t keeps nested inserts whose names match KEEP as INSERT rows
(defun upd:dump (src block out keep / d ms ref ents rows)
  (setq d (vla-getinterfaceobject (vlax-get-acad-object) "ObjectDBX.AxDbDocument.26"))
  (vla-open d src :vlax-true)
  (setq ms (vla-get-modelspace d))
  (setq ref (vla-insertblock ms (vlax-3d-point 0 0 0) block 1 1 1 0))
  (setq ents (upd:explode-all ref 0 keep))
  (setq rows (mapcar '(lambda (e) (vl-catch-all-apply 'upd:row (list e))) ents))
  (setq rows (vl-remove-if 'vl-catch-all-error-p rows))
  (setq f (open out "w" "utf8"))
  (foreach r rows (write-line r f))
  (close f)
  (vlax-release-object d)
  (length rows))
