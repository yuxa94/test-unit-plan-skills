;;; unit-plan CAD helper (AutoCAD / AutoCAD LT 2024+ with Visual LISP ActiveX).
;;; The job DWG is written WITHOUT switching the active document:
;;;   - if the job DWG is open in the editor, its document object is used in place;
;;;   - otherwise it is opened through ObjectDBX, edited, and saved back.
;;; Receipts (.started/.done/.failed) live in the job operations directory.
(vl-load-com)

(setq upc:*dbx-progid* nil)

(defun upc:norm (p) (strcase (vl-string-translate "\\" "/" p)))

(defun upc:dbx (/ v o)
  (if upc:*dbx-progid*
    (vla-getinterfaceobject (vlax-get-acad-object) upc:*dbx-progid*)
    (progn
      (foreach v '("26" "25" "24" "23" "22" "21" "20")
        (if (and (not o)
                 (not (vl-catch-all-error-p
                        (setq o (vl-catch-all-apply 'vla-getinterfaceobject
                                  (list (vlax-get-acad-object) (strcat "ObjectDBX.AxDbDocument." v)))))))
          (setq upc:*dbx-progid* (strcat "ObjectDBX.AxDbDocument." v))
          (if (vl-catch-all-error-p o) (setq o nil))))
      (if (not o) (error "ObjectDBX not available"))
      o)))

(defun upc:find-open (path / found)
  (vlax-for d (vla-get-documents (vlax-get-acad-object))
    (if (= (upc:norm (vla-get-fullname d)) (upc:norm path)) (setq found d)))
  found)

(defun upc:write-utf8 (path lines / f)
  (setq f (open path "w" "utf8"))
  (if (not f) (error (strcat "Cannot write " path)))
  (foreach l lines (write-line l f))
  (close f) path)

;; Create a new job DWG. Refuses to overwrite. Optional template DWG is copied first.
(defun upc:new (path template / d)
  (cond
    ((findfile path) (strcat "UPC_REJECT_EXISTS " path))
    (t
     (setq d (upc:dbx))
     (if (and template (findfile template)) (vla-open d (findfile template)))
     (vla-saveas d path)
     (vlax-release-object d)
     (strcat "UPC_CREATED " path))))

;; Run (thunk doc) against the job DWG and save it. Returns "DONE ..." or "FAILED ...".
(defun upc:run (path job op thunk / base doc mode r status)
  (setq base (strcat (vl-string-right-trim "/\\" job) "/" op))
  (cond
    ((or (= op "") (wcmatch op "*[~A-Za-z0-9_-]*")) "UPC_REJECT_OPERATION_ID")
    ((not (vl-file-directory-p job)) "UPC_REJECT_JOB_DIRECTORY")
    ((not (findfile path)) "UPC_REJECT_MISSING_DWG")
    ((or (findfile (strcat base ".started")) (findfile (strcat base ".done")) (findfile (strcat base ".failed")))
     "UPC_REJECT_EXISTING_RECEIPT_INSPECT_FIRST")
    (t
     (upc:write-utf8 (strcat base ".started") (list path))
     (if (setq doc (upc:find-open path))
       (setq mode "live")
       (progn (setq mode "dbx" doc (upc:dbx)) (vla-open doc path)))
     (setq r (vl-catch-all-apply thunk (list doc)))
     (setq status
       (if (vl-catch-all-error-p r)
         (strcat "FAILED " (vl-catch-all-error-message r))
         (progn
           (setq r (vl-catch-all-apply 'vla-saveas (list doc path)))
           (if (vl-catch-all-error-p r) (strcat "FAILED save: " (vl-catch-all-error-message r)) "DONE"))))
     (if (= mode "dbx") (vlax-release-object doc))
     (upc:write-utf8 (strcat base (if (= status "DONE") ".done" ".failed")) (list status mode))
     (strcat status " " mode))))

;;; ---- small geometry helpers used by every sub-skill ----
(defun upc:pt (x y) (vlax-3d-point x y 0.0))

(defun upc:layer (doc name color ltype / lay)
  (setq lay (vl-catch-all-apply 'vla-item (list (vla-get-layers doc) name)))
  (if (vl-catch-all-error-p lay) (setq lay (vla-add (vla-get-layers doc) name)))
  (if color (vla-put-color lay color))
  (if (and ltype (not (vl-catch-all-error-p (vl-catch-all-apply 'vla-item (list (vla-get-linetypes doc) ltype)))))
    (vla-put-linetype lay ltype))
  lay)

(defun upc:pline (ms pts closed / arr)
  ;; pts: list of (x y)
  (setq arr (vlax-make-safearray vlax-vbDouble (cons 0 (1- (* 2 (length pts))))))
  (vlax-safearray-fill arr (apply 'append pts))
  (setq arr (vla-addlightweightpolyline ms (vlax-make-variant arr)))
  (if closed (vla-put-closed arr :vlax-true))
  arr)

(defun upc:hatch (ms pattern scale angle-deg outer-objs inner-loops / h sa)
  ;; outer-objs: list of closed boundary objects; inner-loops: list of lists of objects (islands)
  (setq h (vla-addhatch ms acHatchPatternTypePreDefined pattern :vlax-true))
  (setq sa (vlax-make-safearray vlax-vbObject (cons 0 (1- (length outer-objs)))))
  (vlax-safearray-fill sa outer-objs)
  (vla-appendouterloop h sa)
  (foreach il inner-loops
    (setq sa (vlax-make-safearray vlax-vbObject (cons 0 (1- (length il)))))
    (vlax-safearray-fill sa il)
    (vla-appendinnerloop h sa))
  (vla-put-patternscale h scale)
  (vla-put-patternangle h (* pi (/ angle-deg 180.0)))
  (vla-evaluate h)
  h)

(defun upc:set (obj layer)
  (vla-put-layer obj layer) obj)

(defun upc:objarray (objs / sa)
  (setq sa (vlax-make-safearray vlax-vbObject (cons 0 (1- (length objs)))))
  (vlax-safearray-fill sa objs)
  sa)

;; Copy standards from a reference DWG into DOC (used by unit-plan-standards).
;; layers / dimstyles / textstyles: lists of names; blocks: block names (definitions come
;; with a temporary reference that is deleted afterwards). Missing names are reported.
(defun upc:import (doc src layers dimstyles textstyles blocks / s report grab ms tmp copied)
  (setq s (upc:dbx) report '())
  (vla-open s (findfile src) :vlax-true)
  (defun grab (coll names owner kind / objs o)
    (setq objs '())
    (foreach n names
      (setq o (vl-catch-all-apply 'vla-item (list coll n)))
      (if (vl-catch-all-error-p o)
        (setq report (cons (strcat "missing " kind ": " n) report))
        (setq objs (cons o objs))))
    (if objs (vla-copyobjects s (upc:objarray objs) owner))
    (length objs))
  (setq report (cons (strcat "textstyles " (itoa (grab (vla-get-textstyles s) textstyles (vla-get-textstyles doc) "textstyle"))) report))
  (setq report (cons (strcat "layers " (itoa (grab (vla-get-layers s) layers (vla-get-layers doc) "layer"))) report))
  (setq report (cons (strcat "dimstyles " (itoa (grab (vla-get-dimstyles s) dimstyles (vla-get-dimstyles doc) "dimstyle"))) report))
  (setq ms (vla-get-modelspace s) tmp '())
  (foreach b blocks
    (if (vl-catch-all-error-p (vl-catch-all-apply 'vla-item (list (vla-get-blocks s) b)))
      (setq report (cons (strcat "missing block: " b) report))
      (setq tmp (cons (vla-insertblock ms (upc:pt 0 0) b 1 1 1 0) tmp))))
  (if tmp
    (progn
      (setq copied (vlax-safearray->list (vlax-variant-value (vla-copyobjects s (upc:objarray tmp) (vla-get-modelspace doc)))))
      (foreach o copied (vla-delete o))
      (setq report (cons (strcat "blocks " (itoa (length copied))) report))))
  (vlax-release-object s)          ; source is never saved
  (reverse report))

(princ)
