; ==============================================================================
; mul.asm — Multiplicação X * Y para o processador ufc2x_dual
;
; LAYOUT DE MEMÓRIA:
;   byte  0        → reservado (preâmbulo do dispatch)
;   bytes 1-2      → goto inicio  (salta sobre os dados)
;   byte  3        → padding para alinhar word 1 ao byte 4
;   bytes 4-7      → word 1: SAÍDA  (avaliador lê resultado aqui)
;   bytes 8-11     → word 2: ENTRADA X (multiplicando)
;   bytes 12-15    → word 3: ENTRADA Y (multiplicador)
;   bytes 16+      → CÓDIGO
;
; ALGORITMO — soma acumulada com contador decrescente:
;   Z1 = Y_entrada   (contador)
;   X  = X_entrada   (multiplicando — fixo no loop)
;   Y  = 0           (acumulador)
;   if Z1 == 0: pula direto para escrita  (trata Y=0 → resultado 0)
;   loop:
;       Y += X       (addyx — 1 ciclo)
;       Z1--         (decz1 — 1 ciclo)
;       if Z1 == 0: sai do loop
;       goto loop
;   mem[saida] = Y
;   halt
;
; CUSTO TOTAL: 2 + 6 + 6 + (N-1)*6 + 4 + 3 = 6N + 9 ciclos
;   goto(2) + ldz1(6) + ldx(6) + clry(1) + jzz1(2) = 17 ciclos de setup
;   por iter (menos última): addyx(1)+decz1(1)+jzz1(2)+goto(2) = 6 ciclos
;   última iter: addyx(1)+decz1(1)+jzz1(2) = 4 ciclos
;   escreve: movy(2)+halt(1) = 3 ciclos (+ 2 do goto inicial)
; ==============================================================================

; ── SALTA SOBRE OS DADOS ──────────────────────────────────────────────────────
    goto  inicio    ; bytes 1-2: desvia para o código
    wb 0            ; byte 3: padding para word 1 começar no byte 4

; ── WORDS RESERVADAS ──────────────────────────────────────────────────────────
saida:  ww 0        ; word 1 → bytes  4-7   (avaliador lê resultado aqui)
entx:   ww 0        ; word 2 → bytes  8-11  (avaliador escreve X)
enty:   ww 0        ; word 3 → bytes 12-15  (avaliador escreve Y)

; ── CÓDIGO (byte 16) ──────────────────────────────────────────────────────────
inicio:
    ldz1  enty      ; Z1 = Y_entrada  (contador)      — 6 ciclos (load duplo)
    ldx   entx      ; X  = X_entrada  (fixo no loop)  — 6 ciclos (load duplo)
    clry            ; Y  = 0          (acumulador)     — 1 ciclo
    jzz1  escreve   ; if Y_entrada==0 → resultado é 0 — 2 ciclos

loop:
    addyx           ; Y = Y + X                        — 1 ciclo ★
    decz1           ; Z1 = Z1 - 1                      — 1 ciclo
    jzz1  escreve   ; if Z1 == 0 → fim do loop         — 2 ciclos
    goto  loop      ;                                   — 2 ciclos

escreve:
    movy  saida     ; mem[word1] = Y  (grava resultado) — 2 ciclos ★
    halt
