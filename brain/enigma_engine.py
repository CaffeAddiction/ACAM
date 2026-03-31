# brain/enigma_engine.py
import string

class Enigma:
    def __init__(self, rotors, reflector, ring_settings, initial_positions, plugboard=""):
        # TARİHİ VE KUSURSUZ PERMÜTASYONLAR (M3 Wehrmacht)
        self.rotor_defs = {
            'I':   'EKMFLGDQVZNTOWYHXUSPAIBRCJ',
            'II':  'AJDKSIRUXBLHWTMCQGZNPYFVOE',
            'III': 'BDFHJLCPRTXVZNYEIGWAKMUSQO' # <- DÜZELTİLDİ
        }
        self.reflector_defs = {'B': 'YRUHQSLDPXNGOKMIEBFZCWVJAT'}
        
        self.rotors = [self.rotor_defs[r] for r in rotors]
        self.reflector = self.reflector_defs[reflector]
        self.ring_settings = ring_settings
        self.positions = list(initial_positions)
        self.plugboard = self.create_plugboard(plugboard)

    def create_plugboard(self, mapping):
        pb = list(range(26))
        if not mapping: return pb
        pairs = mapping.upper().split()
        for pair in pairs:
            a, b = ord(pair[0])-65, ord(pair[1])-65
            pb[a], pb[b] = b, a
        return pb

    def rotate(self):
        # Basit rotor dönüşü (Hızlı test için)
        self.positions[2] = (self.positions[2] + 1) % 26
        if self.positions[2] == 0:
            self.positions[1] = (self.positions[1] + 1) % 26
            if self.positions[1] == 0:
                self.positions[0] = (self.positions[0] + 1) % 26

    def encrypt_char(self, c):
        if not c.isalpha(): return c
        self.rotate()
        
        x = ord(c.upper()) - 65
        x = self.plugboard[x]
        
        # 1. İleri Geçiş (R3 -> R2 -> R1)
        for i in range(2, -1, -1):
            offset = (self.positions[i] - self.ring_settings[i]) % 26
            x = (ord(self.rotors[i][(x + offset) % 26]) - 65 - offset) % 26
            
        # 2. Reflector (B)
        x = ord(self.reflector[x % 26]) - 65
        
        # 3. Geri Dönüş (R1 -> R2 -> R3)
        for i in range(3):
            offset = (self.positions[i] - self.ring_settings[i]) % 26
            # Wiring içindeki harfin yerini bul (Geriye doğru iz sür)
            target = chr(((x + offset) % 26) + 65)
            idx = (self.rotors[i].index(target) - offset) % 26
            x = idx
            
        return chr(self.plugboard[x] + 65)

    def crypt(self, text):
        return "".join(self.encrypt_char(c) for c in text)

def crack_enigma(ciphertext):
    """
    Rotor pozisyonlarını (26x26x26) tarayarak en iyi Quadgram skorunu bulur.
    """
    from classical_ciphers import fitness_score
    best_score = -1e10
    best_pos = (0, 0, 0)
    
    # Gerçek hayatta tüm kombinasyonlar taranır, test için sınırlı tarama yapıyoruz
    for r1 in range(26):
        for r2 in range(26):
            for r3 in range(26):
                e = Enigma(['I', 'II', 'III'], 'B', [0, 0, 0], [r1, r2, r3])
                decrypted = e.crypt(ciphertext)
                score = fitness_score(decrypted)
                if score > best_score:
                    best_score, best_pos = score, (r1, r2, r3)
    
    final_enigma = Enigma(['I', 'II', 'III'], 'B', [0, 0, 0], best_pos)
    return {"text": final_enigma.crypt(ciphertext), "pos": best_pos, "score": best_score}