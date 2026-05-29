; ==============================================================================
; maior_v3.asm — Compara X e Y e escreve resultado na word 1
;
; Layout de memória:
;   word 1 (byte  4) → SAÍDA:  0 se x <= y,  1 se x > y
;   word 2 (byte  8) → ENTRADA: valor de X
;   word 3 (byte 12) → ENTRADA: valor de Y
;
; OTIMIZAÇÃO CHAVE vs versão anterior:
;   Antes:  ldx(1) + ldy(1) + subxy(1) = 3 instruções para X-Y
;   Agora:  ldx(1) + sub entr_y(1)     = 2 instruções para X-Y
;
;   'sub entr_y' faz X = X - mem[word3] diretamente, em 1 instrução de máquina,
;   eliminando 'ldy' E 'subxy' ao mesmo tempo (fusão de load+aritmética).
;
; CONTAGEM DE INSTRUÇÕES (clocks medidos pelo avaliador):
;
;   Caminho X > Y  (jle não tomado):
;     ldx + sub + jle + ldxi + mov + halt = 6 clocks
;
;   Caminho X <= Y (jle tomado — pior caso):
;     ldx + sub + jle + [goto_impl] + clrx + mov + halt = 7 clocks
;
;   Versão anterior: 8 clocks — ganho de 1 clock (≈12.5%)
; ==============================================================================

; ---------- Reserva das words 1, 2 e 3 ----------
; O assembler insere byte 0 = 0 automaticamente.
; Precisamos que os labels batam nos bytes corretos (múltiplos de 4):
;   saida  = byte  4 → word_addr = 4/4 = 1  ✓
;   entr_x = byte  8 → word_addr = 8/4 = 2  ✓
;   entr_y = byte 12 → word_addr = 12/4 = 3 ✓

         wb 0        ; byte 1 — padding
         wb 0        ; byte 2 — padding
         wb 0        ; byte 3 — padding
saida:   wb 0        ; byte 4 — word 1 (SAÍDA)
         wb 0        ; byte 5
         wb 0        ; byte 6
         wb 0        ; byte 7
entr_x:  wb 0        ; byte 8 — word 2 (entrada X)
         wb 0        ; byte 9
         wb 0        ; byte 10
         wb 0        ; byte 11
entr_y:  wb 0        ; byte 12 — word 3 (entrada Y)
         wb 0        ; byte 13
         wb 0        ; byte 14
         wb 0        ; byte 15

; ---------- Programa (começa no byte 16) ----------
inicio:
    ldx  entr_x      ; X ← mem[word 2]           — 1 instrução (load com pipeline dual-bus)
    sub  entr_y      ; X ← X - mem[word 3]        — 1 instrução (aritmética+load fundidos!)
                     ;   fusão de ldy+subxy em 1 instrução: economiza 1 clock vs versão anterior
                     ;   flags atualizados: N=1→X<Y | Z=1→X=Y | N=0,Z=0→X>Y

    jle  x_menor_igual   ; se (N|Z)=1 → X≤Y        — 1 instrução

    ; --- X > Y: escreve 1 ---
    ldxi 1           ; X ← 1                       — 1 instrução (dual-bus)
    mov  saida       ; mem[word 1] ← 1             — 1 instrução
    halt             ;                             — 1 instrução   → 6 clocks total

x_menor_igual:
    ; --- X ≤ Y: escreve 0 ---
    clrx             ; X ← 0                       — 1 instrução
    mov  saida       ; mem[word 1] ← 0             — 1 instrução
    halt             ;                             — 1 instrução   → 7 clocks total (pior caso)
