        goto    inicio
        wb      0
saida:  ww      0               ; word 1: resultado
op1:    ww      0               ; word 2: entradacntinicio: ldx     op1
        jz      fib_zero        ; n==0 → saida=0 (default)
        decx                    ; X = n-1
        jz      fib_um          ; n==1 → saida=1
        xtoz2                   ; Z2 = n-1 (contador)
        clrx
        xtoz1                   ; Z1 = a = 0
        ldyi    1               ; Y = b = 1
loop:   z2tox                   ; X = cnt
        jz      fim_loop        ; cnt == 0 → fim (b = fib(n))
        decx
        jz      last_single     ; cnt era 1 → 1 passo simples e fim
        dec x
        xtoz2                   ; cnt -= 2
        ; passo duplo: (a, b) → (a+b, a+2b)
        z1tox
        addxy
        xtoz1                   ; Z1 = a+b (novo a)
        addyx                   ; Y = Y+X = a+2b (novo b)
        goto    loop
last_single: z1tox              ; passo simples: (a, b) → (b, a+b)
        addxy
        ytoz1                   ; Z1 = b (novo a)
        ytox                    ; Y = X = a+b (novo b)
fim_loop: xtoy                  ; X = Y = fib(n)
        mov     saida
        halt
fib_zero: halt                  ; saida=0 default
fib_um: ldxi    1
        mov     saida
        halt
    incx
        mov     saida           ; saida = 1
fim:    halt
         ; saida = 1
fim:    halt
