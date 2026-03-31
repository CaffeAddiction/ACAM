# brain/hash_cracker.py
import hashlib
import itertools
import string
import time

# 🌐 NORDPASS 2023-2024 SİBER GÜVENLİK RAPORU - KÜRESEL VE TÜRKİYE VERİ SETİ 🌐
COMMON_PASSWORDS = [
    "123456", "password", "123456789", "12345678", "qwerty", "111111", 
    "12345", "secret", "123123", "admin", "qwerty123", "qwerty1", "welcome", 
    "1234", "1234567890", "Aa123456", "root", "user",
    "turktelekom", "superonline", "galatasaray", "fenerbahce", "besiktas",
    "iloveyou", "mustafa", "ahmet", "mehmet", "system", "test", "cyber", "acam", "yusuf"
]

# Sık kullanılan son ekler (Şifreyi güçlendirdiğini sananların yanılgıları)
COMMON_SUFFIXES = ["", "123", "1234", "1", "2023", "2024", "01", "34", "35", "99", "!", ".", "?"]

def identify_hash_type(hash_string):
    """Hash'in uzunluğuna bakarak türünü otonom olarak tespit eder."""
    length = len(hash_string)
    if length == 32: return "MD5"
    elif length == 40: return "SHA-1"
    elif length == 56: return "SHA-224"
    elif length == 64: return "SHA-256"
    elif length == 96: return "SHA-384"
    elif length == 128: return "SHA-512"
    return "Unknown"

def brute_force_hash(target_hash, max_length=5, use_digits=True, use_upper=False, use_special=False):
    """
    Önce Siber İstihbarat (Mutasyonlu Sözlük) ile hızlı tarama yapar.
    Bulamazsa, belirlenen max_length'e kadar tüm kombinasyonları sıfırdan üreterek (Brute-Force) Hash çözer.
    """
    target_hash = target_hash.lower().strip()
    hash_type = identify_hash_type(target_hash)
    
    if hash_type == "Unknown":
        return {"success": False, "error": "Bilinmeyen veya desteklenmeyen Hash uzunluğu."}

    # 1. Karakter Setini (Evreni) Belirle
    charset = string.ascii_lowercase  # a-z
    if use_digits:
        charset += string.digits      # 0-9
    if use_upper:
        charset += string.ascii_uppercase # A-Z
    if use_special:
        charset += "!@#$%^&*()-_+="   # Özel karakterler

    # 2. Doğru Hash Fonksiyonunu Seç
    hash_functions = {
        "MD5": hashlib.md5,
        "SHA-1": hashlib.sha1,
        "SHA-224": hashlib.sha224,
        "SHA-256": hashlib.sha256,
        "SHA-384": hashlib.sha384,
        "SHA-512": hashlib.sha512
    }
    hash_func = hash_functions[hash_type]

    print(f"\n🚀 ACAM HASH MOTORU ATEŞLENDİ")
    print(f"Hedef: {target_hash} ({hash_type})")
    print("-" * 50)

    start_time = time.perf_counter()
    attempts = 0

    # 🔥 AŞAMA 1: SİBER İSTİHBARAT (MUTASYONLU SÖZLÜK SALDIRISI) 🔥
    print("[*] Aşama 1: Mutasyonlu Sözlük Saldırısı başlatılıyor...")
    for word in COMMON_PASSWORDS:
        for suffix in COMMON_SUFFIXES:
            attempts += 1
            guess = word + suffix
            hashed_guess = hash_func(guess.encode('utf-8')).hexdigest()
            
            if hashed_guess == target_hash:
                duration = time.perf_counter() - start_time
                return {
                    "success": True,
                    "plaintext": guess,
                    "type": f"{hash_type} (Sözlük)",
                    "attempts": attempts,
                    "time": round(duration, 3)
                }

    # 🔥 AŞAMA 2: KABA KUVVET (BRUTE-FORCE) ÜRETİMİ 🔥
    print(f"[*] Aşama 2: Kaba Kuvvet (1-{max_length} karakter) başlatılıyor...")
    print(f"Karakter Seti: {len(charset)} karakter")
    
    for length in range(1, max_length + 1):
        for guess_tuple in itertools.product(charset, repeat=length):
            attempts += 1
            guess = "".join(guess_tuple)
            
            hashed_guess = hash_func(guess.encode('utf-8')).hexdigest()

            if hashed_guess == target_hash:
                duration = time.perf_counter() - start_time
                return {
                    "success": True,
                    "plaintext": guess,
                    "type": f"{hash_type} (Kaba Kuvvet)", 
                    "attempts": attempts,
                    "time": round(duration, 3) 
                }

    # Eğer hiçbir aşamada bulamazsa
    duration = time.perf_counter() - start_time
    return {
        "success": False,
        "error": f"Sözlük ve {max_length} karaktere kadar olan kaba kuvvet ({attempts:,} deneme) tükendi.",
        "type": hash_type,
        "time": round(duration, 3),
        "attempts": attempts
    }

if __name__ == "__main__":
    # HIZLI TEST
    # 1. 'admin123' kelimesinin MD5 Hash'i (Sözlükten anında bulacak):
    test_hash_1 = "0192023a7bbd73250516f069df18b500" 
    
    # 2. 'acam' kelimesinin MD5 Hash'i (Kaba kuvvetten bulacak):
    test_hash_2 = "b67b39ab91bfb29ca653c21e17665e1a"
    
    for th in [test_hash_1, test_hash_2]:
        result = brute_force_hash(th, max_length=5, use_digits=True)
        if result.get("success"):
            print(f"✅ HASH KIRILDI! ({result['type']})")
            print(f"🔓 Orijinal Metin: {result['plaintext']}")
            print(f"⏱️ Süre: {result['time']} saniye")
            print(f"🔢 Deneme Sayısı: {result['attempts']:,}\n")
        else:
            print(f"❌ Başarısız: {result.get('error')}\n")