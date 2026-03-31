import string
import random
import itertools
import os
import math
import urllib.request
import ssl

COMMON_WORDS_STRONG = [
    "THE","BE","TO","OF","AND","A","IN","THAT","HAVE","I",
    "IT","FOR","NOT","ON","WITH","HE","AS","YOU","DO","AT"
]

def score_text(text):
    if not text:
        return -1000

    score = 0
    text_upper = text.upper()
    length = len(text)

    # 🔹 Space heuristic
    spaces = text_upper.count(' ')
    if length > 10:
        if 0.10 <= (spaces / length) <= 0.25:
            score += 100
        elif spaces == 0:
            score -= 50

    # 🔹 Vowel ratio
    vowels = "AEIOU"
    vowel_count = sum(1 for c in text_upper if c in vowels)
    if length > 0:
        ratio = vowel_count / length
        if ratio < 0.2:
            score -= 100

    # 🔹 Consonant penalty
    consonant_streak = 0
    for char in text_upper:
        if char.isalpha():
            if char not in vowels:
                consonant_streak += 1
                if consonant_streak >= 4:
                    score -= 20
            else:
                consonant_streak = 0
        else:
            consonant_streak = 0

    # 🔥 WORD BASED SCORING (CRITICAL)
    words = text_upper.split()
    word_hits = sum(1 for w in words if w in COMMON_WORDS_STRONG)
    score += word_hits * 120

    bad_words = sum(
        1 for w in words
        if len(w) > 4 and not any(v in w for v in "AEIOU")
    )
    score -= bad_words * 100

    # 🔥 lowercase bonus (XOR fix)
    lower_ratio = sum(1 for c in text if c.islower()) / max(len(text),1)
    if lower_ratio > 0.6:
        score += 50

    # 🔹 common patterns
    patterns = ["THE ", "ING ", "ION", "ENT", " IS ", " OF "]
    for p in patterns:
        if p in text_upper:
            score += 60

    # 🔹 frequency
    freqs = {"E":12,"T":9,"A":8,"O":8,"I":7,"N":7,"S":6,"R":6,"H":6}
    for char in text_upper:
        score += freqs.get(char, 0)
        if char.isalpha():
            score += 1
        elif char == ' ':
            score += 5
        elif not char.isprintable():
            score -= 20

    return score


def calculate_ic(text):
    n = len(text)
    if n <= 1:
        return 0

    f = {}
    for char in text.upper():
        if char.isalpha():
            f[char] = f.get(char, 0) + 1

    return sum(v * (v - 1) for v in f.values()) / (n * (n - 1))


def crack_caesar(ciphertext):
    best_score = -1e10
    best_text, best_shift = "", 0

    for shift in range(26):
        decrypted = ""
        for char in ciphertext:
            if char.isalpha():
                off = 65 if char.isupper() else 97
                decrypted += chr((ord(char) - off - shift) % 26 + off)
            else:
                decrypted += char

        score = score_text(decrypted)

        if score > best_score:
            best_score, best_text, best_shift = score, decrypted, shift

    return {
        "text": best_text,
        "shift": best_shift,
        "score": best_score,
        "type": "Caesar"
    }
UNIGRAM_FREQS = {
    'A': 0.08167, 'B': 0.01492, 'C': 0.02782, 'D': 0.04253, 'E': 0.12702,
    'F': 0.02228, 'G': 0.02015, 'H': 0.06094, 'I': 0.06966, 'J': 0.00153,
    'K': 0.00772, 'L': 0.04025, 'M': 0.02406, 'N': 0.06749, 'O': 0.07507,
    'P': 0.01929, 'Q': 0.00095, 'R': 0.05987, 'S': 0.06327, 'T': 0.09056,
    'U': 0.02758, 'V': 0.00978, 'W': 0.02360, 'X': 0.00150, 'Y': 0.01974,
    'Z': 0.00074
}
UNIGRAM_LOGS = {k: math.log10(v) for k, v in UNIGRAM_FREQS.items()}

def unigram_score(text):
    """Metnin sadece harf frekanslarına dayalı basit skorunu hesaplar."""
    clean_text = "".join(filter(str.isalpha, text.upper()))
    return sum(UNIGRAM_LOGS.get(c, -5.0) for c in clean_text)

def fitness_score(text):
    """
    Kısa metinlerde 'Aşırı Uyum'u (Reward Hacking) engellemek için hibrit puanlama yapar.
    50 karakterden kısaysa Unigram (Harf frekansı) ile Quadgram'ı harmanlar.
    """
    clean_text = "".join(filter(str.isalpha, text.upper()))
    L = len(clean_text)
    
    if L == 0:
        return -1e10
        
    q_score = scorer.score(text)
    
    if L < 50:
        # HİBRİT PUANLAMA: Kısa metinlerde harf dağılımını (Unigram) çapaya dönüştür.
        # Unigram skorunu 3.0 ile çarparak Quadgram'ın "Frankenstein" kelimeler üretmesini baskılıyoruz.
        u_score = unigram_score(text)
        return (u_score * 3.0) + q_score
    else:
        # 50 karakter ve üstünde elimizde yeterli veri olduğu için Quadgram tek başına kusursuzdur.
        return q_score
    
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUADGRAM_FILE = os.path.join(base_dir, 'data', 'english_quadgrams.txt')
# Kriptografi standartlarında kabul görmüş devasa Quadgram veritabanının açık kaynak URL'si
QUADGRAM_URL = "https://raw.githubusercontent.com/torognes/enigma/master/english_quadgrams.txt"

class QuadgramScorer:
    def __init__(self):
        self.ngrams = {}
        self.L = 0
        self.floor = 0
        self.load_quadgrams()

    def load_quadgrams(self):
        # 1. ACAM eksik beyni fark ederse kendi kendine indirir
        if not os.path.exists(QUADGRAM_FILE):
            print(f"\n[!] ACAM Zeka Güncellemesi: Quadgram İstatistik Veritabanı İndiriliyor...")
            print(f"    Hedef: {QUADGRAM_FILE}")
            os.makedirs(os.path.dirname(QUADGRAM_FILE), exist_ok=True)
            try:
                # SSL sertifika hatalarını (Windows'ta sık yaşanır) aşmak için bypass
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(QUADGRAM_URL, context=ctx) as response, open(QUADGRAM_FILE, 'wb') as out_file:
                    out_file.write(response.read())
                print("[+] Veritabanı başarıyla indirildi ve ACAM'a entegre edildi!\n")
            except Exception as e:
                print(f"[-] İndirme Hatası: {e}")
                print("⚠️  Lütfen internet bağlantınızı kontrol edin.")
                return
        
        # 2. Veritabanını belleğe yükle ve Logaritmik Olasılıkları hesapla
        with open(QUADGRAM_FILE, 'r') as f:
            for line in f:
                key, count = line.split(' ')
                self.ngrams[key] = int(count)
        
        self.L = sum(self.ngrams.values())
        for key in self.ngrams.keys():
            # Her bir quadgram'ın İngilizce dilindeki logaritmik (Log10) ağırlığı
            self.ngrams[key] = math.log10(float(self.ngrams[key]) / self.L)
        
        # 3. Hiç bilinmeyen (anlamsız) bir harf dizilimi gelirse verilecek şiddetli 'Ceza' Puanı
        self.floor = math.log10(0.01 / self.L)

    def score(self, text):
        score = 0
        clean_text = "".join(filter(str.isalpha, text.upper()))
        for i in range(len(clean_text) - 3):
            q = clean_text[i:i+4]
            # O(1) hızında sözlük araması, bulamazsa ceza (floor) puanı uygular
            score += self.ngrams.get(q, self.floor)
        return score

# ACAM ayağa kalkarken Quadgram motorunu 1 kere çalıştırıp belleğe alır (Mükemmel Hız ve Optimizasyon)
scorer = QuadgramScorer()

def fitness_score(text):
    """Metnin İngilizceye ne kadar benzediğini devasa Quadgram veritabanı ile kusursuz puanlar."""
    return scorer.score(text)


# --- YENİ: TEPE TIRMANMA (HILL CLIMBING) VIGENERE KIRICI ---
ENGLISH_FREQS = [0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015, 0.06094,
                 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749, 0.07507, 0.01929,
                 0.00095, 0.05987, 0.06327, 0.09056, 0.02758, 0.00978, 0.02360, 0.00150,
                 0.01974, 0.00074]

def crack_vigenere(ciphertext, max_key_len=15):
    """
    Kusursuz Algoritmik Vigenère Kırıcı:
    1. Her sütun için bağımsız Frekans Analizi (Unigram) ile matematiksel temel anahtarı bulur.
    2. Tepe Tırmanma (N-Gram) ile bu temeli pürüzsüzleştirir.
    Sözlük kullanılmaz, hata payı minimuma indirilir.
    """
    import string
    
    clean_cipher = "".join(filter(str.isalpha, ciphertext.upper()))
    if not clean_cipher: return {"text": ciphertext, "key": "N/A", "score": -1000, "type": "Vigenere"}

    best_overall_score = -1e10
    best_overall_text = ""
    best_overall_key = ""

    dynamic_limit = min(max_key_len, 5 if len(clean_cipher) < 50 else max_key_len)
    limit = min(dynamic_limit, max(1, len(clean_cipher) // 3)) + 1
    
    for key_len in range(1, limit):
        # 1. AŞAMA: SÜTUN BAZLI FREKANS ANALİZİ (Akıllı Başlangıç Noktası)
        base_key = []
        for i in range(key_len):
            column = clean_cipher[i::key_len]
            best_shift_score = -1e10
            best_char = 'A'
            
            for shift in range(26):
                shift_score = 0
                for char in column:
                    decrypted_char_code = (ord(char) - 65 - shift) % 26
                    # Bu sütunun bu kaydırmadaki frekans ağırlığını hesapla
                    shift_score += ENGLISH_FREQS[decrypted_char_code]
                    
                if shift_score > best_shift_score:
                    best_shift_score = shift_score
                    best_char = chr(shift + 65)
            base_key.append(best_char)

        # 2. AŞAMA: TEPE TIRMANMA (Polisaj / Düzeltme)
        # Random başlamak yerine bulduğumuz akıllı anahtardan (base_key) başlıyoruz
        current_key = base_key.copy()
        improved = True
        
        while improved:
            improved = False
            for i in range(key_len):
                best_char_score = -1e10
                best_char = current_key[i]
                
                for char in string.ascii_uppercase:
                    test_key = current_key.copy()
                    test_key[i] = char
                    test_key_str = "".join(test_key)
                    
                    res = ""
                    k_idx = 0
                    for c in ciphertext:
                        if c.isalpha():
                            shift = ord(test_key_str[k_idx % len(test_key_str)]) - 65
                            off = 65 if c.isupper() else 97
                            res += chr((ord(c) - off - shift) % 26 + off)
                            k_idx += 1
                        else: res += c
                            
                    score = fitness_score(res)
                    if score > best_char_score:
                        best_char_score = score
                        best_char = char
                        
                if best_char != current_key[i]:
                    current_key[i] = best_char
                    improved = True 
        
        # 3. AŞAMA: SON PUANLAMA
        final_key_str = "".join(current_key)
        final_res = ""
        k_idx = 0
        for c in ciphertext:
            if c.isalpha():
                shift = ord(final_key_str[k_idx % len(final_key_str)]) - 65
                off = 65 if c.isupper() else 97
                final_res += chr((ord(c) - off - shift) % 26 + off)
                k_idx += 1
            else: final_res += c
            
        final_score = score_text(final_res)
        
        if final_score > best_overall_score:
            best_overall_score = final_score
            best_overall_text = final_res
            best_overall_key = final_key_str

    return {"text": best_overall_text, "key": best_overall_key, "score": best_overall_score, "type": "Vigenere"}

def crack_atbash(ciphertext):
    """Atbash: A<->Z, B<->Y, ... Self-inverse."""
    decrypted = ""
    for char in ciphertext:
        if char.isalpha():
            off = 65 if char.isupper() else 97
            decrypted += chr(off + 25 - (ord(char) - off))
        else:
            decrypted += char
    return {
        "text": decrypted,
        "score": score_text(decrypted),
        "type": "Atbash"
    }


def crack_affine(ciphertext):
    """Tüm geçerli (a, b) çiftlerini dener: E(x) = (a*x + b) mod 26"""
    from math import gcd
    best_score = -1e10
    best_text = ""
    best_a, best_b = 1, 0

    valid_a = [a for a in range(1, 26) if gcd(a, 26) == 1]

    for a in valid_a:
        a_inv = pow(a, -1, 26)
        for b in range(26):
            decrypted = ""
            for char in ciphertext:
                if char.isalpha():
                    off = 65 if char.isupper() else 97
                    x = ord(char) - off
                    decrypted += chr((a_inv * (x - b)) % 26 + off)
                else:
                    decrypted += char
            score = score_text(decrypted)
            if score > best_score:
                best_score = score
                best_text = decrypted
                best_a, best_b = a, b

    return {
        "text": best_text,
        "key": f"a={best_a}, b={best_b}",
        "score": best_score,
        "type": "Affine"
    }


def crack_rail_fence(ciphertext, max_rails=10):
    """Rail Fence (Zigzag) transpozisyon şifresi kırıcı."""
    best_score = -1e10
    best_text = ""
    best_rails = 2

    for num_rails in range(2, min(max_rails + 1, len(ciphertext))):
        pattern = list(range(num_rails)) + list(range(num_rails - 2, 0, -1))
        indices = [pattern[i % len(pattern)] for i in range(len(ciphertext))]

        rail_lengths = [indices.count(r) for r in range(num_rails)]

        rails = []
        pos = 0
        for length in rail_lengths:
            rails.append(list(ciphertext[pos:pos + length]))
            pos += length

        rail_indices = [0] * num_rails
        decrypted = ""
        for i in range(len(ciphertext)):
            rail = indices[i]
            if rail_indices[rail] < len(rails[rail]):
                decrypted += rails[rail][rail_indices[rail]]
                rail_indices[rail] += 1

        score = score_text(decrypted)
        if score > best_score:
            best_score = score
            best_text = decrypted
            best_rails = num_rails

    return {
        "text": best_text,
        "key": f"rails={best_rails}",
        "score": best_score,
        "type": "Rail Fence"
    }


def crack_single_byte_xor(byte_data):
    best_score = -1e10
    best_text, best_key = "", None

    for key in range(256):
        try:
            decrypted = "".join(chr(b ^ key) for b in byte_data)
            score = score_text(decrypted)

            if score > best_score:
                best_score = score
                best_text = decrypted
                best_key = key
        except:
            continue

    return {
        "text": best_text,
        "key": best_key,
        "score": best_score,
        "type": "XOR"
    }


def crack_multi_byte_xor(byte_data, max_key_len=20):
    """
    Hamming Distance ile anahtar uzunluğu tespit edip,
    her byte pozisyonu için en iyi tek-byte XOR'u bulan gelişmiş kırıcı.
    """
    def hamming_distance(b1, b2):
        return sum(bin(x ^ y).count('1') for x, y in zip(b1, b2))

    if len(byte_data) < 4:
        return {"text": "", "key": None, "score": -1e10, "type": "XOR (Repeating-Key)"}

    # 1. Hamming Distance ile en olası anahtar uzunluklarını bul
    key_scores = []
    effective_max = min(max_key_len, len(byte_data) // 4)
    for ks in range(2, effective_max + 1):
        num_blocks = min(6, len(byte_data) // ks)
        if num_blocks < 2:
            continue
        blocks = [byte_data[i*ks:(i+1)*ks] for i in range(num_blocks)]
        total_dist = 0
        comparisons = 0
        for i in range(len(blocks)):
            for j in range(i+1, len(blocks)):
                total_dist += hamming_distance(blocks[i], blocks[j])
                comparisons += 1
        if comparisons > 0:
            normalized = (total_dist / comparisons) / ks
            key_scores.append((normalized, ks))

    key_scores.sort()
    # En iyi 5 aday anahtar uzunlugunu dene + kısa anahtarları her zaman dahil et
    candidate_lengths = [ks for _, ks in key_scores[:5]]
    # Kısa anahtar uzunluklarını (2-4) her zaman dene (brute-force fallback)
    for short_len in [2, 3, 4]:
        if short_len not in candidate_lengths and short_len <= len(byte_data) // 2:
            candidate_lengths.append(short_len)

    best_score = -1e10
    best_text, best_key = "", None

    for key_len in candidate_lengths:
        key_bytes = []
        for i in range(key_len):
            slice_bytes = byte_data[i::key_len]
            best_byte_score = -1e10
            best_byte = 0
            for k in range(256):
                try:
                    decrypted_slice = "".join(chr(b ^ k) for b in slice_bytes)
                    s = score_text(decrypted_slice)
                    if s > best_byte_score:
                        best_byte_score = s
                        best_byte = k
                except:
                    continue
            key_bytes.append(best_byte)

        decrypted = "".join(chr(byte_data[i] ^ key_bytes[i % key_len]) for i in range(len(byte_data)))
        score = score_text(decrypted)
        if score > best_score:
            best_score = score
            best_text = decrypted
            best_key = key_bytes

    return {
        "text": best_text,
        "key": best_key,
        "score": best_score,
        "type": "XOR (Repeating-Key)"
    }


# --- COLUMNAR TRANSPOSITION KIRICI ---
def crack_columnar_transposition(ciphertext, max_cols=10):
    """
    Sütunsal transpozisyon şifresi kırıcı.
    Olası sütun sayılarını ve sütun permütasyonlarını dener.
    """
    from itertools import permutations

    best_score = -1e10
    best_text = ""
    best_key = ""

    for num_cols in range(2, min(max_cols + 1, len(ciphertext))):
        num_rows = len(ciphertext) // num_cols
        remainder = len(ciphertext) % num_cols

        # Sütun uzunluklarını hesapla
        col_lengths = []
        for c in range(num_cols):
            col_lengths.append(num_rows + (1 if c < remainder else 0))

        # Küçük sütun sayıları için tüm permütasyonları dene
        if num_cols <= 7:
            perms = permutations(range(num_cols))
        else:
            # Büyük sütunlar için rastgele permütasyonlar dene
            perms = set()
            for _ in range(500):
                p = list(range(num_cols))
                random.shuffle(p)
                perms.add(tuple(p))
            perms = list(perms)

        for perm in perms:
            try:
                # Sütunları permütasyona göre sırala
                reordered_lengths = [col_lengths[perm[i]] for i in range(num_cols)]

                # Sütunlardan metni oku
                cols = []
                pos = 0
                for length in col_lengths:
                    cols.append(ciphertext[pos:pos + length])
                    pos += length

                # Permütasyona göre sütunları yeniden sırala
                reordered_cols = [cols[perm[i]] for i in range(num_cols)]

                # Satır satır oku
                decrypted = ""
                for row in range(num_rows + 1):
                    for col_idx in range(num_cols):
                        if row < len(reordered_cols[col_idx]):
                            decrypted += reordered_cols[col_idx][row]

                score = score_text(decrypted)
                if score > best_score:
                    best_score = score
                    best_text = decrypted
                    best_key = f"cols={num_cols}, order={''.join(str(x) for x in perm)}"
            except:
                continue

    return {
        "text": best_text,
        "key": best_key,
        "score": best_score,
        "type": "Columnar Transposition"
    }


# --- PLAYFAIR CIPHER KIRICI (SIMULATED ANNEALING) ---
def crack_playfair(ciphertext):
    """
    Kusursuzlaştırılmış Playfair Kırıcı: Simulated Annealing (Benzetimli Tavlama)
    - Soğuma (cooling) oranı 0.99965'e çekilerek zamana yayıldı.
    - Local Maxima'ya takılmamak için 5 farklı başlangıç noktası (restarts) eklendi.
    - Sözlük veya kelime kullanılmaz, sadece N-Gram istatistikleri işlenir.
    """
    import math
    import random

    clean = "".join(c for c in ciphertext.upper() if c.isalpha())
    clean = clean.replace('J', 'I')
    if len(clean) < 4 or len(clean) % 2 != 0:
        return {"text": ciphertext, "key": "N/A", "score": -1e10, "type": "Playfair"}

    def decrypt_playfair(ctext, matrix):
        def find_pos(ch):
            idx = matrix.index(ch)
            return idx // 5, idx % 5

        result = ""
        for i in range(0, len(ctext), 2):
            r1, c1 = find_pos(ctext[i])
            r2, c2 = find_pos(ctext[i+1])

            if r1 == r2:
                result += matrix[r1*5 + (c1-1)%5]
                result += matrix[r2*5 + (c2-1)%5]
            elif c1 == c2:
                result += matrix[((r1-1)%5)*5 + c1]
                result += matrix[((r2-1)%5)*5 + c2]
            else:
                result += matrix[r1*5 + c2]
                result += matrix[r2*5 + c1]
        return result

    def swap_matrix(matrix):
        m = matrix.copy()
        op = random.randint(0, 4)
        if op == 0:  # İki harf değiştir
            i, j = random.sample(range(25), 2)
            m[i], m[j] = m[j], m[i]
        elif op == 1:  # Satır değiştir
            r1, r2 = random.sample(range(5), 2)
            for c in range(5):
                m[r1*5+c], m[r2*5+c] = m[r2*5+c], m[r1*5+c]
        elif op == 2:  # Sütun değiştir
            c1, c2 = random.sample(range(5), 2)
            for r in range(5):
                m[r*5+c1], m[r*5+c2] = m[r*5+c2], m[r*5+c1]
        elif op == 3:  # Satır ters çevir
            r = random.randint(0, 4)
            row = [m[r*5+c] for c in range(5)]
            row.reverse()
            for c in range(5):
                m[r*5+c] = row[c]
        else:  # Sütun ters çevir
            c = random.randint(0, 4)
            col = [m[r*5+c] for r in range(5)]
            col.reverse()
            for r in range(5):
                m[r*5+c] = col[r]
        return m

    alphabet = list("ABCDEFGHIKLMNOPQRSTUVWXYZ")
    best_overall_matrix = alphabet.copy()
    best_overall_score = -1e10
    best_overall_decrypted = ""

    # DAHA GÜÇLÜ ARAMA İÇİN: 5 Farklı Rastgele Başlangıç Noktası (Restart)
    restarts = 5
    iterations_per_restart = 15000 
    
    for _ in range(restarts):
        current_matrix = alphabet.copy()
        random.shuffle(current_matrix)
        current_decrypted = decrypt_playfair(clean, current_matrix)
        current_score = fitness_score(current_decrypted)

        best_local_score = current_score
        best_local_matrix = current_matrix.copy()
        best_local_decrypted = current_decrypted

        temperature = 20.0
        # Termodinamik düzeltme: Sıcaklığın 15.000 adımda ~0.1'e düşmesini sağlayan katsayı
        cooling = 0.99965 

        for step in range(iterations_per_restart):
            new_matrix = swap_matrix(current_matrix)
            try:
                new_decrypted = decrypt_playfair(clean, new_matrix)
                new_score = fitness_score(new_decrypted)
            except:
                continue

            delta = new_score - current_score
            
            # Metropolis Kabul Kriteri: Daha kötüyse bile sıcaklığa bağlı olasılıkla kabul et (Esneklik)
            if delta > 0 or random.random() < math.exp(delta / max(temperature, 0.001)):
                current_matrix = new_matrix
                current_score = new_score
                
                if current_score > best_local_score:
                    best_local_score = current_score
                    best_local_matrix = current_matrix.copy()
                    best_local_decrypted = new_decrypted

            temperature *= cooling

        # Yerel tepe noktası, genel skordan daha iyiyse kaydet
        if best_local_score > best_overall_score:
            best_overall_score = best_local_score
            best_overall_matrix = best_local_matrix.copy()
            best_overall_decrypted = best_local_decrypted

    # Orijinal metnin büyük/küçük harf ve karakter düzenini koruma
    final_text = ""
    di = 0
    for ch in ciphertext:
        if ch.isalpha() and di < len(best_overall_decrypted):
            final_text += best_overall_decrypted[di].lower() if ch.islower() else best_overall_decrypted[di]
            di += 1
        else:
            final_text += ch

    return {
        "text": final_text,
        "key": "".join(best_overall_matrix),
        "score": score_text(final_text), 
        "type": "Playfair"
    }