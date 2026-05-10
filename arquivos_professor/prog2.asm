     goto main
     wb 0
     
res  ww 0
a    ww 127
b    ww 85
um   ww 1
temp ww 0

main mov x, temp
     sub x, temp
     add x, b
mult jz  x, fim
     sub x, b
     add x, a
     add x, res
     mov x, res
     sub x, res
     add x, b
     sub x, um
     mov x, b
     goto mult
     
fim  halt

