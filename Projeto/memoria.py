from array import array

memory = array("L", [0]) * (1024*1024//4) #1 MByte

def read_word(ender):
    ender = ender & 0b111111111111111111
    return memory[ender]
    
def write_word(ender, val):
    ender = ender & 0b111111111111111111
    val = val & 0xFFFFFFFF
    memory[ender] = val
    
def read_byte(ender):
    ender = ender & 0b11111111111111111111
    end_word = ender >> 2
    
    val_word = memory[end_word]
    
    end_byte = ender & 0b11
    val_byte = val_word >> (end_byte << 3)
    val_byte = val_byte & 0xFF
    
    return val_byte
    
def write_byte(ender, val):
    val = val & 0xFF
    
    ender = ender & 0b11111111111111111111
    end_word = ender >> 2
    val_word = memory[end_word]
    
    end_byte = ender & 0b11
    
    mask = ~(0xFF << (end_byte << 3))
    val_word = val_word & mask
    
    val = val << (end_byte << 3)
    
    val_word = val_word | val
    
    memory[end_word] = val_word