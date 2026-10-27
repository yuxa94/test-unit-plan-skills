;;; Read-only unit-plan sheet analysis via ObjectDBX (block-expanded).
;;; Output: C:/temp/up_out/<name>.tsv  rows: KIND \t layer \t key \t count
(vl-load-com)

(defun up:add (key n alist / p)
  (if (setq p (assoc key alist))
    (subst (cons key (+ (cdr p) n)) p alist)
    (cons (cons key n) alist)))

(defun up:clean (s)
  (if (= (type s) 'STR) (vl-string-translate "\t\r\n" "   " s) ""))

(defun up:rtos (x) (rtos x 2 2))

;; records for one entity; key = (kind layer rest)
(defun up:ent (blocks e res / on lay v)
  (setq on (vla-get-objectname e) lay (vla-get-layer e))
  (cond
    ((= on "AcDbAttributeDefinition") res)
    ((= on "AcDbBlockReference")
     (setq v (vl-catch-all-apply 'vla-get-effectivename (list e)))
     (if (vl-catch-all-error-p v) (setq v (vla-get-name e)))
     (setq res (up:add (list "B" lay v) 1 res))
     (foreach s (up:blk blocks (vla-get-name e))
       (setq res (up:add (list (car (car s)) (if (= (cadr (car s)) "0") lay (cadr (car s))) (caddr (car s))) (cdr s) res)))
     res)
    (t
     (setq res (up:add (list "E" lay (substr on 5)) 1 res))
     (cond
       ((= on "AcDbHatch")
        (setq res (up:add (list "H" lay (strcat (vla-get-patternname e) " s=" (up:rtos (vla-get-patternscale e)) " a=" (up:rtos (* 57.2958 (vla-get-patternangle e))))) 1 res)))
       ((wcmatch on "AcDb*Dimension")
        (setq res (up:add (list "D" lay (strcat (vla-get-stylename e) " " (substr on 5))) 1 res)))
       ((member on '("AcDbText" "AcDbMText"))
        (setq v (vl-catch-all-apply 'vla-get-textstring (list e)))
        (if (not (vl-catch-all-error-p v))
          (setq res (up:add (list "T" lay (strcat (up:clean v) " |h=" (up:rtos (vla-get-height e)) " |st=" (vla-get-stylename e))) 1 res))))
       ((member on '("AcDbPolyline" "AcDbLine" "AcDbArc" "AcDbCircle"))
        (setq res (up:add (list "LT" lay (vla-get-linetype e)) 1 res))))
     res)))

(defun up:blk (blocks bname / memo res b)
  (if (setq memo (assoc bname *up-memo*))
    (cdr memo)
    (progn
      (setq res '())
      (setq *up-memo* (cons (cons bname nil) *up-memo*))
      (if (not (vl-catch-all-error-p (setq b (vl-catch-all-apply 'vla-item (list blocks bname)))))
        (vlax-for e b (setq res (up:ent blocks e res))))
      (setq *up-memo* (subst (cons bname res) (assoc bname *up-memo*) *up-memo*))
      res)))

(defun up:analyze (path name / dbx ok blocks res f ms)
  (setq dbx (vla-getinterfaceobject (vlax-get-acad-object) "ObjectDBX.AxDbDocument.26"))
  (setq ok (vl-catch-all-apply 'vla-open (list dbx path :vlax-true)))
  (if (vl-catch-all-error-p ok)
    (progn (vlax-release-object dbx) (strcat name " ERR " (vl-catch-all-error-message ok)))
    (progn
      (setq *up-memo* '() res '() blocks (vla-get-blocks dbx) ms 0)
      (vlax-for e (vla-get-modelspace dbx) (setq ms (1+ ms)) (setq res (up:ent blocks e res)))
      (setq f (open (strcat "C:/temp/up_out/" name ".tsv") "w"))
      (write-line (strcat "MS\t\t\t" (itoa ms)) f)
      (vlax-for b blocks
        (if (= (vla-get-isxref b) :vlax-true)
          (write-line (strcat "X\t\t" (vla-get-name b) " => " (vla-get-path b) "\t0") f)))
      (vlax-for l (vla-get-layers dbx)
        (write-line (strcat "L\t" (vla-get-name l) "\tc=" (itoa (vla-get-color l)) " lt=" (vla-get-linetype l)
                            " lw=" (itoa (vla-get-lineweight l)) (if (= (vla-get-layeron l) :vlax-true) "" " OFF")
                            (if (= (vla-get-freeze l) :vlax-true) " FROZEN" "") "\t0") f))
      (vlax-for d (vla-get-dimstyles dbx) (write-line (strcat "DS\t\t" (vla-get-name d) "\t0") f))
      (foreach c res
        (write-line (strcat (car (car c)) "\t" (cadr (car c)) "\t" (caddr (car c)) "\t" (itoa (cdr c))) f))
      (close f)
      (vlax-release-object dbx)
      (setq *up-memo* nil)
      (strcat name " ms=" (itoa ms) " keys=" (itoa (length res))))))
