        goto    inicio
        wb      0
saida:  ww      0               ; word 1: resultado
op1:    ww      0               ; word 2: entrada n
temp:   ww      0               ; variável temporária
cnt:    ww      0               ; contador do fatorial
inicio: ldx     op1             ; X = n
        jle     fat_zero        ; n<=0 → 1
        mov     cnt             ; cnt = n
        clrx
        incx
        mov     saida           ; saida = 1
fat_loop: ldx   cnt             ; X = cnt
        jle     fim             ; cnt<=0 → fim
        ldx     saida
        mov     temp            ; temp = saida
        clrx                    ; X = 0 (acumulador)
        ldy     cnt             ; Y = cnt  ← última op ALU seta Z baseado em cnt
inner:  jzy     fim_inner       ; se Y==0, saiu
        add     temp            ; X += temp
        decy
        goto    inner
fim_inner: mov  saida           ; saida = X (novo resultado)
        ldx     cnt
        decx
        mov     cnt
        goto    fat_loop
fat_zero: clrx
        incx
        mov     saida           ; 0! = 1
fim:    halt
