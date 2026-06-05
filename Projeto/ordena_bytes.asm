; ==============================================================================
; ordena_bytes.asm  (otimizado com hardware)
;
;   Valor de 32 bits (word 2) visto como 4 bytes -> retorna (word 1) os bytes
;   ordenados de forma crescente (menor no MSB).  ex.: 3648413612 -> 1601613017
;
;   Usa o opcode 'bsortx' = rede de ordenacao combinacional de 4 bytes em 1 ciclo
;   (5 comparadores compare-and-swap em hardware, min/max sem branch).
;
;   word 1 = SAIDA | word 2 = ENTRADA
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
