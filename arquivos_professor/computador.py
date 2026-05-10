import memory
import clock
import ufc2x as cpu

#===========================================================
#1:  SOMA A X O VALOR NO END. 215
#3:  IF X = 0 GOTO 20
#5:  GRAVE O VALOR DO REG. X NO END. 220
#7:  HALT
#20: SOMA A X O VALOR NO END. 200
#22: GOTO 5
memory.write_byte(1, 2) #SOMA A X
memory.write_byte(2, 215) #O VALOR NO END. 215
memory.write_byte(3, 11) #IF X = 0 GOTO
memory.write_byte(4, 20) #20
memory.write_byte(5, 6) #GRAVE O VALOR DO REG. X
memory.write_byte(6, 220) #NO END. 220
memory.write_byte(7, 255) #HALT
memory.write_byte(20, 2) #SOMA A X
memory.write_byte(21, 200) #O VALOR NO END. 200
memory.write_byte(22, 9) #GOTO
memory.write_byte(23, 5) #5
#============================================================

#============================================================
#1:  GOTO 50
#3:  SOMA A X O VALOR NO END. 215
#50: SOMA A X O VALOR NO END. 200
#52: SOMA A X O VALOR NO END. 210
#54: GRAVE O VALOR DO REG. X NO END. 220
#56: PARE
#memory.write_byte(1, 9) #GOTO
#memory.write_byte(2, 50) #50
#memory.write_byte(3, 2) #SOMA A X
#memory.write_byte(4, 215) #O VALOR NO END. 215
#memory.write_byte(50, 2) #SOMA A X
#memory.write_byte(51, 200) #O VALOR NO END. 200
#memory.write_byte(52, 2) #SOMA A X
#memory.write_byte(53, 210) #O VALOR NO END. 210
#memory.write_byte(54, 6) #GRAVE O VALOR DO REG. X
#memory.write_byte(55, 220) #NO END. 220
#memory.write_byte(56, 255) #PARE
#=============================================================

memory.write_word(200, 4200)
memory.write_word(210, 732)
memory.write_word(215, 0)

clock.start([cpu])

print(memory.read_word(220))