        goto    inicio
        wb      0
saida:  ww      0               ; word 1: resultado
op1:    ww      0               ; word 2: entrada n
a:      ww      0               ; fib(k-2)
b:      ww      1               ; fib(k-1)
cnt:    ww      0               ; contador
inicio: ldx     op1             ; X = n
        jz      fib_zero        ; n==0 → saida=0
        mov     cnt             ; cnt = n
        ; checar se n==1
        decx
        jz      fib_um          ; n-1==0 → saida=1
        ; inicializar a=0, b=1
        clrx
        mov     a               ; a = 0
        clrx
        incx
        mov     b               ; b = 1
loop:   ldx     cnt
        decx                    ; X = cnt-1
        jz      fim_loop        ; cnt==1 → fim (b é a resposta)
        mov     cnt             ; cnt = cnt-1
        ; c = a + b
        ldx     b
        add     a               ; X = a + b
        ; a = b
        ldy     b               ; Y = b
        movy    a               ; a = Y
        ; b = c (X ainda tem a+b)
        mov     b               ; b = X (c)
        goto    loop
fim_loop: ldx   b
        mov     saida           ; saida = b
        halt
fib_zero: clrx
        mov     saida           ; saida = 0
        halt
fib_um: clrx
        incx
        mov     saida           ; saida = 1
fim:    halt
