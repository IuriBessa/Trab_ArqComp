; ==============================================================================
; produto_escalar.asm  -  Produto escalar de dois vetores de 4 bytes (8 bits)
;
; Cada entrada de 32 bits e vista como [b3 b2 b1 b0] (4 valores de 8 bits).
; Resultado = b0A*b0B + b1A*b1B + b2A*b2B + b3A*b3B  (a ordem dos pares nao
; altera a soma, entao percorremos os indices de byte 0..3).
;
; Layout de memoria (o assembler insere o byte 0 = 0 automaticamente):
;   word 1 (bytes  4..7)  -> SAIDA   : produto escalar
;   word 2 (bytes  8..11) -> ENTRADA : vetor A (32 bits)
;   word 3 (bytes 12..15) -> ENTRADA : vetor B (32 bits)
;
; Registradores:
;   Z1 = acumulador (soma dos produtos)
;   X  = byte de A, depois o produto parcial
;   Y  = byte de B
;
; Sem lacos (totalmente desenrolado): ~33 instrucoes, sem risco de loop infinito.
; Usa as instrucoes de 1 ciclo: bextx/bexty (extrai byte) e mulxyh (X = X*Y).
; ==============================================================================

        goto main         ; bytes 1-2  (pula a area reservada das words)
        wb 0              ; byte 3     (padding p/ alinhar word1 no byte 4)
word1:  ww 0              ; bytes 4-7   (SAIDA)
word2:  ww 0              ; bytes 8-11  (ENTRADA A)
word3:  ww 0              ; bytes 12-15 (ENTRADA B)

main:   clrz1            ; acumulador = 0

        ; ---- byte 0 ----
        ldx  word2       ; X = A
        bextx 0          ; X = A[0]
        ldy  word3       ; Y = B
        bexty 0          ; Y = B[0]
        mulxyh           ; X = A[0] * B[0]
        addxz1           ; X = X + acc
        xtoz1            ; acc = X

        ; ---- byte 1 ----
        ldx  word2
        bextx 1
        ldy  word3
        bexty 1
        mulxyh
        addxz1
        xtoz1

        ; ---- byte 2 ----
        ldx  word2
        bextx 2
        ldy  word3
        bexty 2
        mulxyh
        addxz1
        xtoz1

        ; ---- byte 3 ----
        ldx  word2
        bextx 3
        ldy  word3
        bexty 3
        mulxyh
        addxz1
        xtoz1

        ; ---- escreve a saida ----
        z1tox            ; X = acumulador
        mov  word1       ; word1 = resultado
        halt
