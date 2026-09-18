; ==============================================================================
; ordena_bytes.asm  (otimizado com hardware)
; ==============================================================================

        goto main
        wb 0
word1:  ww 0
word2:  ww 0
word3:  ww 0

main:   ldx  word2       ; X = N
        bsortx           ; X = bytes de N ordenados (menor no MSB)
        mov  word1
        halt
