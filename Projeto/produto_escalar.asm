; ==============================================================================
; produto_escalar.asm  (otimizado com hardware)
;
;   Produto escalar de dois vetores de 4 bytes (word2 = A, word3 = B) -> word1.
;
;   Usa o opcode 'dotxy' = MAC bytewise em hardware (4 multiplicadores de 8 bits
;   + somador) que calcula sum_k A[k]*B[k] em 1 ciclo.
;
;   word 1 = SAIDA | word 2 = A | word 3 = B
; ==============================================================================

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
