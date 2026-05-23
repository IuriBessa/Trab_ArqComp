        goto    inicio
        wb      0
saida:  ww      0               ; word 1: resultado (0 ou 1)
op1:    ww      0               ; word 2: x
op2:    ww      0               ; word 3: y
inicio: ldx     op1             ; X = x
        sub     op2             ; X = x - y
        jle     nao_maior       ; x-y <= 0 → x<=y
        clrx
        incx
        mov     saida           ; saida = 1
        halt
nao_maior: clrx
        mov     saida           ; saida = 0
fim:    halt
