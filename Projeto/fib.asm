; ===========================================================================
; fib.asm  -  Fibonacci iterativo para o processador teste.py
;
; ENTRADA / SAIDA (mesmo layout de fat.asm):
;   word 0  -> byte de boot (goto inicio)
;   word 1  -> saida  : F(n)  escrito apenas no halt
;   word 2  -> op1    : n     (escreva antes de rodar)
;   word 3  -> temp   : nao usado neste programa
;
; REGISTRADORES DURANTE O LOOP (nenhum acesso a RAM):
;   Z1 = F(k-1)   termo anterior da janela deslizante
;   Z2 = F(k)     termo atual   da janela deslizante
;   H  = contador de iteracoes restantes (n-2 ate 0)
;   X  = acumulador principal (novo termo, teste de zero via jz)
;   Y  = buffer de F(k) durante o calculo de F(k+1)
;
; INVARIANTE DO LOOP:
;   Inicio: Z1 = F(1) = 1,  Z2 = F(2) = 1,  H = n-2
;   Cada iteracao avanca a janela em 1:
;     Y <- Z2           (salva F(k) antes de sujar Y)
;     X <- Z1+Z2        (usa addxy: X = X + Y, precisa X=Z1 e Y=Z2)
;     Z1 <- Y=F(k)      avanca janela
;     Z2 <- X=F(k+1)    avanca janela
;   Apos H iteracoes, Z2 = F(n).
;
; ACESSO A MEMORIA:
;   Somente 2x: ldx op1 (le n) e mov saida (escreve resultado).
;   Todo calculo intermediario e em registradores.
;
; INSTRUCOES EXPLORADAS:
;   ldxi           imediato direto (sem acesso a RAM)
;   clrx           X=0 sem RAM
;   xtoz1/z2       copia X para registrador extra Z1 ou Z2
;   ytoz1          copia Y para Z1
;   z1tox / z2toy  copia Z1->X e Z2->Y
;   addxy          X = X + Y (ALU direta, 1 ciclo, sem memoria)
;   xtoh / htox    usa H como deposito do contador (sem RAM)
;   decx           decremento em 1 ciclo
;   jz             desvio se X==0
; ===========================================================================

        goto    inicio
        wb      0
saida:  ww      0               ; word 1 -> resultado F(n)
op1:    ww      0               ; word 2 -> entrada n
temp:   ww      0               ; word 3 -> nao usado

; ---------------------------------------------------------------------------
; Ponto de entrada
; ---------------------------------------------------------------------------
inicio: ldx     op1             ; X = n
        jz      caso_zero       ; n == 0  ->  F(0) = 0

        decx                    ; X = n-1
        jz      caso_um         ; n == 1  ->  F(1) = 1

        decx                    ; X = n-2
        jz      caso_dois       ; n == 2  ->  F(2) = 1

        ; n >= 3:
        ; Inicializa janela em Z1=F(1)=1, Z2=F(2)=1
        ; (uma iteracao ja foi "consumida" ao verificar n>=3)
        ldxi    1
        xtoz1                   ; Z1 = 1 = F(1)
        xtoz2                   ; Z2 = 1 = F(2)

        ; contador = n-2 (ja calculado em X = n-2, nao zerado)
        ; Precisa de X = n-2 novamente; X ja tem n-2 de cima, mas
        ; ldxi 1 sobrescreveu X. Recarrega.
        ldx     op1             ; X = n
        decx                    ; X = n-1
        decx                    ; X = n-2
        xtoh                    ; H = n-2  (contador sem RAM)

; ---------------------------------------------------------------------------
; loop_h: avanca a janela (n-2) vezes usando H como contador em registrador
; ---------------------------------------------------------------------------
loop_h: htox                    ; X = H (contador)
        jz      escreve         ; H == 0  ->  Z2 e F(n)

        ; decrementa H sem memoria
        decx                    ; X = H-1
        xtoh                    ; H = H-1

        ; proximo Fibonacci: precisa X=F(k-1) e Y=F(k) para usar addxy
        z2toy                   ; Y = Z2 = F(k)      (salva F(k) em Y)
        z1tox                   ; X = Z1 = F(k-1)
        addxy                   ; X = F(k-1) + F(k) = F(k+1)

        ; desliza janela
        ytoz1                   ; Z1 = Y = F(k)
        xtoz2                   ; Z2 = X = F(k+1)

        goto    loop_h

; ---------------------------------------------------------------------------
; Escreve resultado
; ---------------------------------------------------------------------------
escreve: z2tox                  ; X = Z2 = F(n)
        mov     saida           ; mem[saida] = F(n)
        halt

; ---------------------------------------------------------------------------
; Casos base
; ---------------------------------------------------------------------------
caso_zero: clrx                 ; X = 0 = F(0)
        mov     saida
        halt

caso_um: ldxi   1               ; X = 1 = F(1)
        mov     saida
        halt

caso_dois: ldxi 1               ; X = 1 = F(2)
        mov     saida
        halt
