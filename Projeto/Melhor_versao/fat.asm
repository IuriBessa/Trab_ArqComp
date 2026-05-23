        goto    inicio
        wb      0
saida:  ww      0               ; word 1: resultado (fica 0 até o fim)
op1:    ww      0               ; word 2: entrada n
temp:   ww      0               ; word 3: multiplicando temporário (fat usa só 1 entrada)
inicio: ldx     op1
        jz      fim_zero        ; n == 0 → saida = 1
        xtoz1                   ; Z1 = n (contador externo)
        xtoz2                   ; Z2 = produto = n
        decx
        jz      fim             ; n == 1 → produto já é n
fat_loop: z1tox
        decx
        jz      fim             ; contador chegou em 1 → produto pronto
        xtoz1                   ; contador--
        z2tox
        mov     temp            ; temp = produto atual
        clrx
        z1toy                   ; Y = contador (iterações internas)
inner:  jzy     fim_inner
        add     temp            ; X += produto
        decy
        goto    inner
fim_inner: xtoz2                ; Z2 = novo produto
        goto    fat_loop
fim:    z2tox
        mov     saida           ; escreve saida APENAS no fim
        halt
fim_zero: ldxi  1
        mov     saida
        halt
