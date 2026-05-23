        goto    inicio
        wb      0
saida:  ww      0               ; word 1: resultado (0 ou 1)
op1:    ww      0               ; word 2: x
op2:    ww      0               ; word 3: y
inicio: ldx     op2             ; X = y
        sub     op1             ; X = y - x
        jn      maior_sim       ; y-x < 0  ⇒  x > y → saida = 1
        clrx                    ; senão saida = 0
        goto    fim
maior_sim: ldxi 1
fim:    mov     saida
        halt
