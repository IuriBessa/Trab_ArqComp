; ==============================================================================
; ordena_bytes.asm
;
;   Recebe um valor de 32 bits (word 2) visto como 4 bytes [b3 b2 b1 b0] e
;   retorna (word 1) o valor com os 4 bytes ordenados de forma crescente,
;   com o MENOR byte no mais significativo e o MAIOR no menos significativo.
;
;   ex.: 3648413612 = [217,118,95,172] -> ordenado [95,118,172,217]
;        = 1601613017
;
; Layout de memoria (o assembler insere o byte 0 = 0 automaticamente):
;   word 1 (bytes  4..7)  -> SAIDA
;   word 2 (bytes  8..11) -> ENTRADA
;   word 3 (bytes 12..15) -> (nao usado)
;   word 4..7             -> v0..v3 (os 4 bytes a ordenar)
;   word 8               -> tmp (troca)
;
; Sem lacos: extrai 4 bytes, ordena com uma rede de 5 comparadores e
; reempacota. Custo constante (~74 clocks), sem risco de timeout/loop.
; ==============================================================================

        goto main         ; bytes 1-2
        wb 0              ; byte 3
word1:  ww 0              ; word 1  SAIDA
word2:  ww 0              ; word 2  ENTRADA
word3:  ww 0              ; word 3  (livre)
v0:     ww 0              ; word 4
v1:     ww 0              ; word 5
v2:     ww 0              ; word 6
v3:     ww 0              ; word 7
tmp:    ww 0              ; word 8

main:
        ; --- extrai os 4 bytes ---
        ldx  word2
        bextx 0
        mov  v0
        ldx  word2
        bextx 1
        mov  v1
        ldx  word2
        bextx 2
        mov  v2
        ldx  word2
        bextx 3
        mov  v3

        ; --- rede de ordenacao crescente: (0,1)(2,3)(0,2)(1,3)(1,2) ---
        ; comparador (0,1)
        ldx  v0
        sub  v1
        jle  c1
        ldx  v0
        mov  tmp
        ldx  v1
        mov  v0
        ldx  tmp
        mov  v1
c1:     ; comparador (2,3)
        ldx  v2
        sub  v3
        jle  c2
        ldx  v2
        mov  tmp
        ldx  v3
        mov  v2
        ldx  tmp
        mov  v3
c2:     ; comparador (0,2)
        ldx  v0
        sub  v2
        jle  c3
        ldx  v0
        mov  tmp
        ldx  v2
        mov  v0
        ldx  tmp
        mov  v2
c3:     ; comparador (1,3)
        ldx  v1
        sub  v3
        jle  c4
        ldx  v1
        mov  tmp
        ldx  v3
        mov  v1
        ldx  tmp
        mov  v3
c4:     ; comparador (1,2)
        ldx  v1
        sub  v2
        jle  c5
        ldx  v1
        mov  tmp
        ldx  v2
        mov  v1
        ldx  tmp
        mov  v2
c5:
        ; --- reempacota: MSB = v0 (menor) ... LSB = v3 (maior) ---
        clrx
        ldy  v0
        bpackx
        ldy  v1
        bpackx
        ldy  v2
        bpackx
        ldy  v3
        bpackx
        mov  word1
        halt
