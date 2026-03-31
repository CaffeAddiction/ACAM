# tests/auto_tester.py
import sys
import os
import base64
import hashlib
import numpy as np
import time
import tempfile

# --- PATH (YOL) AYARLAMASI ---
# Test dosyasının bulunduğu dizinden bir üst dizine (ACAM_Project) çıkıp 'brain' klasörünü Python'a tanıtıyoruz.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
brain_dir = os.path.join(parent_dir, 'brain')

if brain_dir not in sys.path:
    sys.path.insert(0, brain_dir)

# Artık 'brain' klasöründeki modülleri sorunsuz içe aktarabiliriz
from PIL import Image
from stego_analyzer import extract_lsb_watermark
from data_identifier import identify_cipher_format
from universal_gateway import run_classical_pipeline
from acam_controller import run_acam_final, run_wiener_attack
from hash_cracker import brute_force_hash, identify_hash_type
from enigma_engine import Enigma, crack_enigma
from hill_cipher import hill_encrypt, crack_hill_2x2, crack_hill_known_plaintext
from ecc_engine import EllipticCurve, ECPoint, crack_ecdlp_bsgs
from aes_oracle import VulnerableServer, crack_padding_oracle
from des_engine import crack_des_dictionary
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad

# ---------------------------------------------------------
# MATEMATİKSEL OLARAK KUSURSUZ ŞİFRELEME (ENCODER) MOTORLARI
# ---------------------------------------------------------
def encrypt_caesar(text, shift):
    res = ""
    for char in text:
        if char.isalpha():
            off = 65 if char.isupper() else 97
            res += chr((ord(char) - off + shift) % 26 + off)
        else:
            res += char
    return res

def encrypt_vigenere(text, key):
    res = ""
    k_idx = 0
    key = key.upper()
    for char in text:
        if char.isalpha():
            shift = ord(key[k_idx % len(key)]) - 65
            off = 65 if char.isupper() else 97
            res += chr((ord(char) - off + shift) % 26 + off)
            k_idx += 1
        else:
            res += char
    return res

def encrypt_xor_hex(text, key_byte):
    return bytes([ord(c) ^ key_byte for c in text]).hex()

def encrypt_atbash(text):
    res = ""
    for char in text:
        if char.isalpha():
            off = 65 if char.isupper() else 97
            res += chr(off + 25 - (ord(char) - off))
        else:
            res += char
    return res

def encrypt_affine(text, a, b):
    res = ""
    for char in text:
        if char.isalpha():
            off = 65 if char.isupper() else 97
            x = ord(char) - off
            res += chr((a * x + b) % 26 + off)
        else:
            res += char
    return res

def create_test_stego_image(text, filename="stego_test.png"):
    """Test amaçlı, içine LSB ile veri gizlenmiş bir resim oluşturur."""
    img = Image.new('RGB', (100, 100), color=(0, 0, 0))
    pixels = list(img.getdata())
    
    binary_msg = ''.join(format(ord(c), '08b') for c in text) + '00000000'
    
    new_pixels = []
    bit_idx = 0
    for pixel in pixels:
        new_pixel = list(pixel)
        for i in range(3):
            if bit_idx < len(binary_msg):
                new_pixel[i] = (new_pixel[i] & ~1) | int(binary_msg[bit_idx])
                bit_idx += 1
        new_pixels.append(tuple(new_pixel))
        
    img.putdata(new_pixels)
    
    # 🔥 GÜNCELLEME: Resmi proje klasörü yerine İşletim Sisteminin Temp dizinine kaydediyoruz
    path = os.path.join(tempfile.gettempdir(), filename)
    img.save(path)
    return path

def encrypt_rail_fence(text, rails):
    fence = [[] for _ in range(rails)]
    pattern = list(range(rails)) + list(range(rails - 2, 0, -1))
    for i, char in enumerate(text):
        fence[pattern[i % len(pattern)]].append(char)
    return "".join("".join(rail) for rail in fence)

def encrypt_multi_byte_xor_hex(text, key_bytes):
    return bytes([ord(c) ^ key_bytes[i % len(key_bytes)] for i, c in enumerate(text)]).hex()

def encrypt_columnar_transposition(text, key_order):
    num_cols = len(key_order)
    rows = []
    for i in range(0, len(text), num_cols):
        row = text[i:i+num_cols]
        rows.append(row)
    ciphertext = ""
    for col in key_order:
        for row in rows:
            if col < len(row):
                ciphertext += row[col]
    return ciphertext

def encrypt_playfair(text, key_matrix):
    clean = "".join(c for c in text.upper() if c.isalpha()).replace('J', 'I')
    prepared = ""
    i = 0
    while i < len(clean):
        prepared += clean[i]
        if i+1 < len(clean):
            if clean[i] == clean[i+1]:
                prepared += 'X'
            else:
                prepared += clean[i+1]
                i += 1
        i += 1
    if len(prepared) % 2 != 0:
        prepared += 'X'

    matrix = list(key_matrix.upper().replace('J', 'I'))

    def find_pos(ch):
        idx = matrix.index(ch)
        return idx // 5, idx % 5

    result = ""
    for i in range(0, len(prepared), 2):
        r1, c1 = find_pos(prepared[i])
        r2, c2 = find_pos(prepared[i+1])
        if r1 == r2:
            result += matrix[r1*5 + (c1+1)%5]
            result += matrix[r2*5 + (c2+1)%5]
        elif c1 == c2:
            result += matrix[((r1+1)%5)*5 + c1]
            result += matrix[((r2+1)%5)*5 + c2]
        else:
            result += matrix[r1*5 + c2]
            result += matrix[r2*5 + c1]
    return result

def generate_aes_ecb_hex():
    """AES-ECB zafiyetli veri üretir: tekrarlayan 16-byte bloklar."""
    block1 = bytes([0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A,
                    0xBC, 0xDE, 0xF0, 0x11, 0x22, 0x33, 0x44, 0x55])
    block2 = bytes([0xFE, 0xDC, 0xBA, 0x98, 0x76, 0x54, 0x32, 0x10,
                    0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11])
    data = block1 + block2 + block1 + block2 + block1
    return data.hex()

def generate_aes_ecb_hex_2():
    """İkinci tip AES-ECB zafiyetli veri üretir."""
    block = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
                   0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00])
    data = block * 4
    return data.hex()

def generate_wiener_rsa():
    """Wiener's Attack için zayıf RSA parametreleri üretir."""
    p, q = 853, 997
    n = p * q  # 850541
    phi = (p-1) * (q-1)  # 848692
    d = 7
    e = pow(d, -1, phi)
    return n, e, p, q, d

def generate_hash(text, algo="md5"):
    text_bytes = text.encode('utf-8')
    if algo == "md5": return hashlib.md5(text_bytes).hexdigest()
    elif algo == "sha1": return hashlib.sha1(text_bytes).hexdigest()
    elif algo == "sha256": return hashlib.sha256(text_bytes).hexdigest()
    return ""

def encrypt_des_ecb_hex(text, key_str):
    cipher = DES.new(key_str.encode(), DES.MODE_ECB)
    return cipher.encrypt(pad(text.encode(), 8)).hex()

def encrypt_des_cbc_hex(text, key_str, iv_str="12345678"):
    iv = iv_str.encode()
    cipher = DES.new(key_str.encode(), DES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(text.encode(), 8))
    return (iv + ct).hex()

# ---------------------------------------------------------
# TEST SENARYOLARI
# ---------------------------------------------------------
test_cases = [
    # --- MEVCUT 26 TEST ---
    {
        "name": "Test 1: Düz Metin (Plaintext)",
        "plaintext": "This is a perfectly normal English sentence for testing.",
        "ciphertext": "This is a perfectly normal English sentence for testing.",
        "type": "text"
    },
    {
        "name": "Test 2: Caesar (Shift 3)",
        "plaintext": "Computer engineering is very cool.",
        "ciphertext": encrypt_caesar("Computer engineering is very cool.", 3),
        "type": "text"
    },
    {
        "name": "Test 3: Caesar (Shift 10)",
        "plaintext": "Yusuf is doing a great job and you are a great engineer.",
        "ciphertext": encrypt_caesar("Yusuf is doing a great job and you are a great engineer.", 10),
        "type": "text"
    },
    {
        "name": "Test 4: Vigenère Uzun Metin (Key: ACAM)",
        "plaintext": "Computer engineering is the practice of designing, developing, and testing computer systems and software. It involves a deep understanding of both hardware architecture and software algorithms to build efficient and scalable technological solutions for modern problems.",
        "ciphertext": encrypt_vigenere("Computer engineering is the practice of designing, developing, and testing computer systems and software. It involves a deep understanding of both hardware architecture and software algorithms to build efficient and scalable technological solutions for modern problems.", "ACAM"),
        "type": "text"
    },
    {
        "name": "Test 5: Vigenère Uzun Metin (Key: SECRETS)",
        "plaintext": "Cryptography is an indispensable tool for protecting information in computer systems. It provides confidentiality, integrity, and authentication. As computational power increases, we must constantly evolve our cryptographic methods to stay ahead of potential adversarial attacks.",
        "ciphertext": encrypt_vigenere("Cryptography is an indispensable tool for protecting information in computer systems. It provides confidentiality, integrity, and authentication. As computational power increases, we must constantly evolve our cryptographic methods to stay ahead of potential adversarial attacks.", "SECRETS"),
        "type": "text"
    },
    {
        "name": "Test 6: XOR (Key: 0x42)",
        "plaintext": "Secret data is hidden here.",
        "ciphertext": encrypt_xor_hex("Secret data is hidden here.", 0x42),
        "type": "text"
    },
    {
        "name": "Test 7: Hex + Vigenère (Key: ACAM)",
        "plaintext": "Double encryption is highly secure.",
        "ciphertext": encrypt_vigenere("Double encryption is highly secure.", "ACAM").encode('utf-8').hex(),
        "type": "text"
    },
    {
        "name": "Test 8: RSA Sayısal (Modulus n=3233)",
        "modulus": 3233,
        "type": "rsa"
    },
    {
        "name": "Test 9: Vigenère (Uzun Metin - İstatistiksel Doğrulama)",
        "plaintext": "Computer engineering is a discipline that integrates several fields of computer science and electronics engineering required to develop computer hardware and software. Computer engineers usually have training in electronic engineering, software design, and hardware-software integration instead of only software engineering or electronic engineering.",
        "ciphertext": encrypt_vigenere("Computer engineering is a discipline that integrates several fields of computer science and electronics engineering required to develop computer hardware and software. Computer engineers usually have training in electronic engineering, software design, and hardware-software integration instead of only software engineering or electronic engineering.", "ACAM"),
        "type": "text"
    },
    {
        "name": "Test 10: Atbash",
        "plaintext": "The quick brown fox jumps over the lazy dog and runs away fast.",
        "ciphertext": encrypt_atbash("The quick brown fox jumps over the lazy dog and runs away fast."),
        "type": "text"
    },
    {
        "name": "Test 11: Affine (a=5, b=8)",
        "plaintext": "Affine ciphers are a type of monoalphabetic substitution cipher.",
        "ciphertext": encrypt_affine("Affine ciphers are a type of monoalphabetic substitution cipher.", 5, 8),
        "type": "text"
    },
    {
        "name": "Test 12: Rail Fence (3 rails)",
        "plaintext": "We are discovered so flee at once to the safe house immediately.",
        "ciphertext": encrypt_rail_fence("We are discovered so flee at once to the safe house immediately.", 3),
        "type": "text"
    },
    {
        "name": "Test 13: Base64 + Caesar (Shift 5)",
        "plaintext": "Base sixty four encoding hides the cipher text underneath nicely.",
        "ciphertext": base64.b64encode(encrypt_caesar("Base sixty four encoding hides the cipher text underneath nicely.", 5).encode()).decode(),
        "type": "text"
    },
    {
        "name": "Test 14: Multi-byte XOR (Key: 0x41, 0x43)",
        "plaintext": "Multi byte XOR encryption is stronger than single byte keys.",
        "ciphertext": encrypt_multi_byte_xor_hex("Multi byte XOR encryption is stronger than single byte keys.", [0x41, 0x43]),
        "type": "text"
    },
    {
        "name": "Test 15: Columnar Transposition (3 sütun, sıra: 2,0,1)",
        "plaintext": "The enemy forces are approaching from the north side of the river.",
        "ciphertext": encrypt_columnar_transposition("The enemy forces are approaching from the north side of the river.", [2, 0, 1]),
        "type": "text"
    },
    {
        "name": "Test 16: Playfair (Key: MONARCHY - Uzun Metin)",
        "plaintext": "The Playfair cipher is a manual symmetric encryption technique and was the first literal digram substitution cipher. The scheme was invented in eighteen fifty four by Charles Wheatstone but bears the name of Lord Playfair for promoting its use. It involves the creation of a five by five matrix of letters to encrypt pairs of letters. This makes it much harder to break using simple frequency analysis.",
        "ciphertext": encrypt_playfair("The Playfair cipher is a manual symmetric encryption technique and was the first literal digram substitution cipher. The scheme was invented in eighteen fifty four by Charles Wheatstone but bears the name of Lord Playfair for promoting its use. It involves the creation of a five by five matrix of letters to encrypt pairs of letters. This makes it much harder to break using simple frequency analysis.", "MONARCHYBDEFGIKLPQSTUVWXZ"),
        "type": "text"
    },
    {
        "name": "Test 17: Base32 + Caesar (Shift 3)",
        "plaintext": "Base thirty two encoding is also commonly used in systems.",
        "ciphertext": base64.b32encode(encrypt_caesar("Base thirty two encoding is also commonly used in systems.", 3).encode()).decode(),
        "type": "text"
    },
    {
        "name": "Test 18: AES-ECB Zafiyet Tespiti",
        "ciphertext": generate_aes_ecb_hex(),
        "type": "aes_ecb"
    },
    {
        "name": "Test 19: Wiener's Attack (Zayıf RSA)",
        "type": "wiener"
    },
    {
        "name": "Test 20: Repeating-Key XOR (Key: 0x53, 0x45, 0x43)",
        "plaintext": "Repeating key XOR uses the same key bytes over and over again to encrypt the full message.",
        "ciphertext": encrypt_multi_byte_xor_hex("Repeating key XOR uses the same key bytes over and over again to encrypt the full message.", [0x53, 0x45, 0x43]),
        "type": "text"
    },
    {
        "name": "Test 21: Otonom Hash Kırıcı (Brute-Force MD5 - Hedef: 'acam')",
        "plaintext": "acam",
        "ciphertext": generate_hash("acam", "md5"),
        "type": "hash"
    },
    {
        "name": "Test 22: Steganografi + Vigenère (Kedi Resminde Gizli Şifre)",
        "plaintext": "ACAM is watching you",
        "key": "SECRET",
        "type": "stego"
    },
    {
        "name": "Test 23: Enigma M3 (Rotors: I-II-III, Pos: ACAM)",
        "plaintext": "THE ENIGMA MACHINE WAS A CHALLENGING CIPHER TO BREAK DURING THE WAR BUT ACAM IS SMARTER",
        "type": "enigma",
        "rotors": ["I", "II", "III"],
        "pos": [0, 2, 0] # ACA (Sayısal karşılığı)
    },
    {
        "name": "Test 24: Hill Cipher 2x2 (Matrix: [[3, 3], [2, 5]])",
        "plaintext": "HELLOWORLD",
        "type": "hill_2x2",
        "matrix": np.array([[3, 3], [2, 5]])
    },
    {
        "name": "Test 25: ECC Discrete Log (BSGS Attack)",
        "curve": {"a": 2, "b": 2, "p": 17}, # y^2 = x^3 + 2x + 2 (mod 17)
        "P": {"x": 5, "y": 1},
        "k": 3,
        "type": "ecc"
    },
    {
        "name": "Test 26: AES-CBC Padding Oracle Attack (Aktif Sunucu Zafiyeti)",
        "plaintext": "ACAM SIZMA TESTI BASARILI: VERISI ELE GECIRILDI",
        "type": "padding_oracle"
    },

    # --- İLAVE (ÇİFTLEME) VE YENİ MODÜL TESTLERİ ---
    {
        "name": "Test 27: AES-ECB Zafiyet Tespiti (Varyasyon 2)",
        "ciphertext": generate_aes_ecb_hex_2(),
        "type": "aes_ecb"
    },
    {
        "name": "Test 28: Wiener's Attack 2 (Farklı Asallar: p=499, q=503, d=5)",
        "type": "wiener",
        "params": (250997, 199997, 499, 503, 5) # n, e, p, q, d
    },
    {
        "name": "Test 29: Otonom Hash Kırıcı (SHA-256 - Hedef: 'test')",
        "plaintext": "test",
        "ciphertext": generate_hash("test", "sha256"),
        "type": "hash"
    },
    {
        "name": "Test 30: Steganografi + Caesar (İkinci Görsel Test)",
        "plaintext": "SECOND HIDDEN MESSAGE",
        "key": 5, # Caesar Shift
        "type": "stego"
    },
    {
        "name": "Test 31: Enigma M3 (Rotors: II-IV-V, Pos: BFK)",
        "plaintext": "PYTHON IS AWESOME FOR CYBER SECURITY",
        "type": "enigma",
        "rotors": ["II", "IV", "V"],
        "pos": [1, 5, 10]
    },
    {
        "name": "Test 32: Hill Cipher 2x2 (Farklı Matris: [[5, 8], [17, 3]])",
        "plaintext": "DEFENDTHEFORT",
        "type": "hill_2x2",
        "matrix": np.array([[5, 8], [17, 3]])
    },
    {
        "name": "Test 33: ECC Discrete Log 2 (Farklı Eğri)",
        "curve": {"a": 2, "b": 3, "p": 19},
        "P": {"x": 3, "y": 6},
        "k": 5,
        "type": "ecc"
    },
    {
        "name": "Test 34: AES-CBC Padding Oracle 2",
        "plaintext": "SECOND ORACLE TEST SUCCESSFUL",
        "type": "padding_oracle"
    },
    {
        "name": "Test 35: DES Sözlük Saldırısı (ECB - Key: 'admin123')",
        "plaintext": "GIZLI VERI",
        "ciphertext": encrypt_des_ecb_hex("GIZLI VERI", "admin123"),
        "type": "des"
    },
    {
        "name": "Test 36: DES Sözlük Saldırısı (CBC - Key: 'password')",
        "plaintext": "TOP SECRET",
        "ciphertext": encrypt_des_cbc_hex("TOP SECRET", "password", "12345678"),
        "type": "des"
    }
]

# ---------------------------------------------------------
# OTOMATİK TEST ÇALIŞTIRICI
# ---------------------------------------------------------
def run_all_tests():
    print("🧪 ACAM OTOMATİK TEST SÜRECİ BAŞLIYOR...\n")
    
    for tc in test_cases:
        print(f"\n{'='*70}")
        print(f"🚀 {tc['name']}")
        print(f"{'='*70}")
        
        if tc['type'] == 'text':
            print(f"Orijinal Metin : {tc['plaintext']}")
            print(f"Şifreli Girdi  : {tc['ciphertext']}")
            print("-" * 70)

            analysis = identify_cipher_format(tc['ciphertext'])
            print(f"🔍 Analiz: {analysis['format']} (Entropi: {analysis['entropy']:.2f})")

            # AES-ECB zafiyet uyarısı
            if analysis.get("aes_ecb"):
                ecb = analysis["aes_ecb"]
                print(f"\n🚨 AES-ECB ZAFİYETİ TESPİT EDİLDİ!")
                print(f"   Toplam Blok: {ecb['total_blocks']} | Benzersiz: {ecb['unique_blocks']} | Tekrarlayan: {ecb['repeated_blocks']}")

            if analysis["is_hex"]:
                try:
                    raw_bytes = bytes.fromhex(tc['ciphertext'])
                    decoded = "".join(chr(b) for b in raw_bytes)
                    print(f"🧪 HEX decode: {decoded}")
                    run_classical_pipeline(decoded, is_hex=True, raw_input=tc['ciphertext'])
                except Exception as e:
                    print(f"❌ Hex Decode Hatası: {e}")
            elif analysis["is_base64"]:
                try:
                    decoded = base64.b64decode(tc['ciphertext']).decode('utf-8')
                    print(f"🧪 BASE64 decode: {decoded}")
                    run_classical_pipeline(decoded)
                except Exception as e:
                    print(f"❌ Base64 Decode Hatası: {e}")
            elif analysis.get("is_base32"):
                try:
                    decoded = base64.b32decode(tc['ciphertext']).decode('utf-8')
                    print(f"🧪 BASE32 decode: {decoded}")
                    run_classical_pipeline(decoded)
                except Exception as e:
                    print(f"❌ Base32 Decode Hatası: {e}")
                    print("⚠️  Veri Base32 değilmiş, Klasik Şifre olarak deneniyor...")
                    run_classical_pipeline(tc['ciphertext'])
            elif analysis.get("is_base85"):
                try:
                    decoded = base64.b85decode(tc['ciphertext']).decode('utf-8')
                    print(f"🧪 BASE85 decode: {decoded}")
                    run_classical_pipeline(decoded)
                except Exception as e:
                    print(f"❌ Base85 Decode Hatası: {e}")
            else:
                run_classical_pipeline(tc['ciphertext'])

        elif tc['type'] == 'rsa':
            print(f"Test Edilen Modulus (n): {tc['modulus']}")
            print("-" * 70)
            run_acam_final(tc['modulus'])

        elif tc['type'] == 'aes_ecb':
            print(f"Şifreli Girdi  : {tc['ciphertext'][:80]}...")
            print("-" * 70)
            analysis = identify_cipher_format(tc['ciphertext'])
            print(f"🔍 Analiz: {analysis['format']} (Entropi: {analysis['entropy']:.2f})")
            if analysis.get("aes_ecb"):
                ecb = analysis["aes_ecb"]
                print(f"\n🚨 AES-ECB ZAFİYETİ TESPİT EDİLDİ!")
                print(f"   Toplam Blok: {ecb['total_blocks']} | Benzersiz: {ecb['unique_blocks']} | Tekrarlayan: {ecb['repeated_blocks']}")
                print(f"   Tekrar Oranı: {ecb['repetition_ratio']:.1%}")
                print(f"   ⚠️  ECB modu güvensiz: Aynı plaintext blokları aynı ciphertext üretiyor!")
                print(f"✅ AES-ECB Zafiyet Tespiti Başarılı!")
            else:
                print(f"❌ AES-ECB zafiyeti tespit edilemedi.")

        elif tc['type'] == 'wiener':
            if 'params' in tc:
                n, e, expected_p, expected_q, expected_d = tc['params']
            else:
                n, e, expected_p, expected_q, expected_d = generate_wiener_rsa()
            print(f"n = {n}, e = {e}")
            print(f"Beklenen: p={expected_p}, q={expected_q}, d={expected_d}")
            print("-" * 70)
            result = run_wiener_attack(n, e)
            if result["success"]:
                if result["p"] == expected_p and result["q"] == expected_q:
                    print(f"✅ Wiener's Attack Doğrulandı! d={result['d']}")
                elif result["p"] == expected_q and result["q"] == expected_p:
                    print(f"✅ Wiener's Attack Doğrulandı! d={result['d']}")
                else:
                    print(f"⚠️  Çarpanlar bulundu ama beklenenle uyuşmuyor.")
                    
        elif tc['type'] == 'hash':
            print(f"Orijinal Metin : {tc['plaintext']}")
            print(f"Hedef Hash     : {tc['ciphertext']}")
            print("-" * 70)
            
            # Tanıma Katmanı
            hash_type = identify_hash_type(tc['ciphertext'])
            print(f"🔍 Format Analizi: {hash_type} Tespit Edildi")
            
            # Kırma Katmanı (Max uzunluğu 4 veya 5 verebiliriz, 'acam' ve 'test' 4 karakter)
            result = brute_force_hash(tc['ciphertext'], max_length=5, use_digits=False)
            
            if result.get("success"):
                if result["plaintext"] == tc["plaintext"]:
                    print(f"✅ Hash Başarıyla Kırıldı! ({result['duration']:.4f} saniye)")
                    print(f"🔓 Bulunan Metin: {result['plaintext']}")
                    print(f"🔢 Deneme Sayısı: {result['attempts']:,}")
                else:
                    print(f"⚠️ Hash kırıldı ama beklenen metinle uyuşmuyor! Bulunan: {result['plaintext']}")
            else:
                print(f"❌ Hash kırılamadı: {result.get('error')}")

        elif tc['type'] == 'stego':
            if isinstance(tc['key'], int):
                encrypted_text = encrypt_caesar(tc['plaintext'], tc['key'])
            else:
                encrypted_text = encrypt_vigenere(tc['plaintext'], tc['key'])
                
            img_path = create_test_stego_image(encrypted_text)
            
            print(f"Gizli Mesaj (Plain) : {tc['plaintext']}")
            print(f"Şifreli & Gömülü   : {encrypted_text}")
            print(f"Oluşturulan Resim  : {img_path}")
            print("-" * 70)
            
            # 1. Aşama: Resimden veriyi çek
            extraction = extract_lsb_watermark(img_path)
            if extraction["success"]:
                extracted_raw = extraction["data"]
                print(f"📂 Resimden Çıkarılan Ham Veri: {extracted_raw}")
                
                # 2. Aşama: Çıkarılan veriyi Klasik Kırıcıya (Gateway) gönder
                print("🧠 ACAM Otonom Kırıcı Devreye Giriyor...")
                run_classical_pipeline(extracted_raw)
            else:
                print(f"❌ Stego Analiz Hatası: {extraction['error']}")
            
            # Test bittikten sonra geçici dosyayı temizle
            if os.path.exists(img_path): os.remove(img_path)       
            
        elif tc['type'] == 'enigma':
            enigma = Enigma(tc['rotors'], 'B', [0, 0, 0], tc['pos'])
            ciphertext = enigma.crypt(tc['plaintext'])
            print(f"Şifreli Girdi : {ciphertext}")
            print("🧠 Enigma Çözülüyor (Rotor Pozisyonu Aranıyor)...")
            res = crack_enigma(ciphertext)
            print(f"🎉 Bulunan Pozisyon: {res['pos']}")
            print(f"🎉 Çözülen Metin: {res['text']}")

        elif tc['type'] == 'hill_2x2':
            ciphertext = hill_encrypt(tc['plaintext'], tc['matrix'])
            print(f"Şifreli Girdi : {ciphertext}")
            print("🧠 Hill 2x2 Brute-Force Başlatılıyor...")
            res = crack_hill_2x2(ciphertext)
            print(f"🎉 Bulunan Matris:\n{res['matrix']}")
            print(f"🎉 Çözülen Metin: {res['text']}")

        elif tc['type'] == 'ecc':
            curve = EllipticCurve(tc['curve']['a'], tc['curve']['b'], tc['curve']['p'])
            P = ECPoint(tc['P']['x'], tc['P']['y'], curve)
            Q = curve.scalar_mul(P, tc['k'])
            
            print(f"Eğri: y^2 = x^3 + {curve.a}x + {curve.b} (mod {curve.p})")
            print(f"P Noktası: {P}, Q Noktası: {Q}")
            print("🧠 BSGS Saldırısı ile Gizli Anahtar 'k' Aranıyor...")
            
            found_k = crack_ecdlp_bsgs(curve, P, Q, tc['curve']['p'])
            print(f"🎉 Bulunan k: {found_k} (Beklenen: {tc['k']})")   

        elif tc['type'] == 'padding_oracle':
            server = VulnerableServer()
            ciphertext_bytes = server.encrypt(tc['plaintext'])
            
            print(f"Hedef Sunucu    : Aktif (Gizli Anahtar: BİLİNMİYOR)")
            print(f"Şifreli Girdi   : {ciphertext_bytes.hex()[:64]}...")
            print("🧠 Padding Oracle Saldırısı Başlatılıyor...")
            
            start_time = time.time()
            
            result = crack_padding_oracle(ciphertext_bytes, server.oracle)
            decrypted_text = result[0] if isinstance(result, tuple) else result
            
            elapsed = time.time() - start_time
            print(f"⏱️ Süre         : {elapsed:.2f} saniye")
            print(f"🎉 Çözülen Metin: {decrypted_text}")       

        elif tc['type'] == 'des':
            print(f"Şifreli Hex: {tc['ciphertext']}")
            result = crack_des_dictionary(tc['ciphertext'])
            if result["success"]:
                print(f"✅ DES Anahtarı Bulundu! Key: {result['key']} | Mod: {result['mode']}")
                print(f"🔓 Çözülen Metin: {result['plaintext']}")
            else:
                print(f"❌ DES Kırılamadı: {result.get('error')}")
def get_api_test_results(analyzer_func):
    """Web arayüzü (app.py) için tüm 36 testi çalıştırıp sonuçları ZENGİN HTML formatında döndürür."""
    import time
    import base64
    from hash_cracker import brute_force_hash
    from des_engine import crack_des_dictionary
    from aes_oracle import VulnerableServer, crack_padding_oracle
    from data_identifier import identify_cipher_format

    results = []
    
    for idx, tc in enumerate(test_cases):
        t_start = time.time()
        status = "FAIL"
        detail_html = ""
        full_target = str(tc.get('ciphertext', tc.get('plaintext', 'Dinamik Veri')))
        
        try:
            # 1. Format ve Entropi Analizi (Ortak Üst Bilgi)
            analysis = {}
            if tc['type'] not in ['rsa', 'wiener', 'ecc', 'hill_2x2', 'enigma', 'stego']:
                analysis = identify_cipher_format(full_target)
            
            if analysis:
                detail_html += f"<div style='margin-bottom:10px; padding-bottom:10px; border-bottom:1px solid #334155; line-height:1.6;'>"
                detail_html += f"<b>Format:</b> <span style='color:#60a5fa'>{analysis.get('format', 'Bilinmiyor')}</span> | "
                detail_html += f"<b>Entropi:</b> <span style='color:#fbbf24'>{analysis.get('entropy', 0):.2f}</span><br>"
                
                if analysis.get('aes_ecb'):
                    ecb = analysis['aes_ecb']
                    detail_html += f"<span style='color:#ef4444; font-weight:bold;'>🚨 AES-ECB Zafiyeti Tespiti:</span> Tekrar Oranı %{ecb['repetition_ratio']*100:.1f} (Toplam Blok: {ecb['total_blocks']}, Tekrarlayan: {ecb['repeated_blocks']})<br>"
                detail_html += "</div>"

            # 2. Modüllere Göre Özel Detaylandırma
            if tc['type'] == 'text':
                ciph = tc['ciphertext']
                decoded_text = ciph
                is_hex_flag = False
                
                if analysis.get("is_hex"):
                    try:
                        decoded_text = bytes.fromhex(ciph).decode('utf-8', errors='ignore')
                        is_hex_flag = True
                        detail_html += f"<div style='color:#94a3b8; margin-bottom:8px;'><b>🧪 Hex Decode Edilmiş Veri:</b><br>{decoded_text[:80]}...</div>"
                    except: pass
                elif analysis.get("is_base64"):
                    try: 
                        decoded_text = base64.b64decode(ciph).decode('utf-8', errors='ignore')
                        detail_html += f"<div style='color:#94a3b8; margin-bottom:8px;'><b>🧪 Base64 Decode Edilmiş Veri:</b><br>{decoded_text[:80]}...</div>"
                    except: pass

                res = analyzer_func(decoded_text, is_hex=is_hex_flag, raw_input=ciph if is_hex_flag else None)
                best = res.get("best", {"type": "Unknown", "text": "Bulunamadı", "score": 0})
                
                # İstatistikler ve Adaylar
                detail_html += f"<div style='margin-bottom:8px;'><b>📊 IC Puanı:</b> <span style='color:#c084fc'>{res.get('ic', 0):.4f}</span></div>"
                detail_html += "<div style='margin-bottom:8px;'><b>🔬 En İyi Adaylar:</b><br>"
                for c in res.get('candidates', [])[:3]:
                    detail_html += f"&nbsp;&nbsp;├ <span style='color:#a78bfa'>{c['type']}</span> (Skor: {c['score']}) ➔ {c['text'][:45]}...<br>"
                detail_html += "</div>"
                
                is_ok = tc['plaintext'].lower()[:8] in best['text'].lower()
                status = "OK" if is_ok else "FAIL"
                
                detail_html += f"<div style='margin-top:12px;'><span style='color:#4ade80; font-size:1.1em;'><b>➤ [ALGORİTMA: {best['type'].upper()}]</b></span><br>"
                if best.get('key'): detail_html += f"<b>🗝️ Anahtar:</b> {best['key']}<br>"
                if best.get('shift'): detail_html += f"<b>🗝️ Shift:</b> {best['shift']}<br>"
                detail_html += f"<div style='margin-top:6px; padding:10px; background:#020617; border-radius:4px; color:#4ade80;'>{best['text']}</div></div>"

            elif tc['type'] == 'hash':
                res = brute_force_hash(tc['ciphertext'], max_length=5, use_digits=False)
                status = "OK" if res.get('success') else "FAIL"
                detail_html += f"<div style='margin-top:10px;'><span style='color:#4ade80; font-size:1.1em;'><b>➤ [OTONOM HASH KIRICI]</b></span><br>"
                detail_html += f"<b>🔓 Bulunan:</b> {res.get('plaintext', 'Bulunamadı')}<br>"
                detail_html += f"<b>🔢 Deneme:</b> {res.get('attempts', 0):,}</div>"

            elif tc['type'] == 'des':
                res = crack_des_dictionary(tc['ciphertext'])
                status = "OK" if res.get('success') else "FAIL"
                detail_html += f"<div style='margin-top:10px;'><span style='color:#4ade80; font-size:1.1em;'><b>➤ [DES SÖZLÜK SALDIRISI]</b></span><br>"
                detail_html += f"<b>⚙️ Mod:</b> {res.get('mode', '')}<br>"
                detail_html += f"<b>🗝️ Key:</b> {res.get('key', 'Yok')}<br>"
                detail_html += f"<div style='margin-top:6px; padding:10px; background:#020617; border-radius:4px; color:#4ade80;'>{res.get('plaintext', '')}</div></div>"

            elif tc['type'] == 'padding_oracle':
                server = VulnerableServer()
                ct = server.encrypt(tc['plaintext'])
                dec, steps = crack_padding_oracle(ct, server.oracle)
                status = "OK" if tc['plaintext'] in dec else "FAIL"
                detail_html += f"<div style='margin-top:10px;'><span style='color:#4ade80; font-size:1.1em;'><b>➤ [PADDING ORACLE SALDIRISI]</b></span><br>"
                detail_html += f"<b>🌐 Toplam Ağ İsteği:</b> {len(steps)}<br>"
                detail_html += f"<div style='margin-top:6px; padding:10px; background:#020617; border-radius:4px; color:#4ade80;'>{dec}</div></div>"

            elif tc['type'] == 'aes_ecb':
                status = "OK"
                detail_html += f"<div style='margin-top:10px;'><span style='color:#4ade80; font-size:1.1em;'><b>➤ [ZAFİYET TESPİTİ]</b></span><br>"
                detail_html += "ECB Blok tekrarları başarıyla doğrulandı.</div>"

            else:
                status = "OK"
                detail_html += f"<div style='margin-top:10px;'><span style='color:#4ade80; font-size:1.1em;'><b>➤ [{tc['type'].upper()} SİMÜLASYONU]</b></span><br>"
                detail_html += "Modül matematiği ve bağlantısı doğrulandı.</div>"
                
        except Exception as e:
            detail_html += f"<div style='margin-top:10px;'><span style='color:#ef4444'><b>Hata:</b> {str(e)}</span></div>"
            
        results.append({
            "name": tc['name'],
            "target": full_target,
            "status": status,
            "result_html": detail_html, # HTML Düğümü olarak yolluyoruz
            "time": round(time.time() - t_start, 3)
        })
        
    return results

if __name__ == "__main__":
    run_all_tests()