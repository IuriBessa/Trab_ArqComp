; ==============================================================================
; produto_escalar.asm  (otimizado com hardware)
;=======================================================

        goto main
        wb 0
word1:  ww 0
word2:  ww 0
word3:  ww 0

main:   ldx  word2       ; X = A
        ldy  word3       ; Y = B
        dotxy            ; X = A[0]*B[0] + ... + A[3]*B[3]
        mov  word1
        halt
