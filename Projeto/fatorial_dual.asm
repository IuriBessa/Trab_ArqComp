; ==============================================================================
; fatorial.asm  -  Calcula X! para o processador ufc2x_dual
;
; Layout:
;   word1 (bytes 4..7)  : saida (resultado X!)
;   word2 (bytes 8..11) : entrada (valor de X)
;
; Registradores:
;   Z1   = contador externo (input -> 0)
;   X    = resultado acumulado (preservado entre iteracoes do outer)
;   word3= copia do resultado p/ usar como multiplicando na multiplicacao atual
;   Y    = contador interno (= Z1 - 1) p/ adicionar word3 a X
; ==============================================================================

         goto main         ; bytes 1-2  (pula a area reservada de words 1 e 2)
         wb 0              ; byte 3
word1:   ww 0              ; bytes 4-7   (saida)
word2:   ww 0              ; bytes 8-11  (entrada)
word3:   ww 0              ; bytes 12-15 (multiplicando temporario)

main:    ldx  word2        ; X = entrada
         xtoz1             ; Z1 = entrada (contador externo)
         ldxi 1            ; X = 1 (resultado acumulado)

outer:   jzz1 done         ; se Z1 == 0, fim
         mov  word3        ; word3 = X (copia do resultado = multiplicando)
         z1toy             ; Y = Z1
         decy              ; Y = Z1 - 1 (X ja conta como "1 * resultado")
inner:   jzy  inner_done   ; somou tudo?
         add  word3        ; X = X + word3
         decy
         goto inner
inner_done:
         decz1             ; Z1 = Z1 - 1
         goto outer

done:    mov  word1        ; word1 = X = resultado final
         halt
