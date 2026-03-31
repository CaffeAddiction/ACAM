# brain/data_identifier.py
import math
import re
import base64

def calculate_entropy(data_string):
    """Bir metnin Shannon Entropisini hesaplar. Yüksek entropi (örneğin > 4.5) güçlü bir şifrelemeye veya sıkıştırmaya işaret eder."""
    if not data_string:
        return 0
    entropy = 0
    for x in set(data_string):
        p_x = float(data_string.count(x)) / len(data_string)
        entropy += - p_x * math.log(p_x, 2)
    return entropy


def detect_aes_ecb(data_bytes):
    """
    AES-ECB zafiyeti tespiti: 16 baytlık tekrarlayan bloklar aranır.
    ECB modunda aynı plaintext blokları aynı ciphertext bloğunu üretir.
    """
    if len(data_bytes) < 32:  # En az 2 blok gerekli
        return None

    block_size = 16
    blocks = [data_bytes[i:i+block_size] for i in range(0, len(data_bytes), block_size)]

    # Tam olmayan son bloğu çıkar
    blocks = [b for b in blocks if len(b) == block_size]

    total_blocks = len(blocks)
    unique_blocks = len(set(blocks))
    repeated = total_blocks - unique_blocks

    if repeated > 0:
        return {
            "detected": True,
            "total_blocks": total_blocks,
            "unique_blocks": unique_blocks,
            "repeated_blocks": repeated,
            "repetition_ratio": repeated / total_blocks
        }
    return None


def detect_base32(text):
    """Base32 formatını tespit eder."""
    # Sadece harflerden oluşuyorsa (rakam veya '=' yoksa) büyük ihtimalle Klasik Şifredir
    if text.isalpha() and not text.endswith('='):
        return False

    if re.fullmatch(r'[A-Z2-7]+=*', text) and len(text) >= 8:
        try:
            base64.b32decode(text)
            return True
        except:
            pass
    return False


def detect_base85(text):
    """Base85 (Ascii85) formatını tespit eder."""
    # Sadece harflerden oluşan metinler base85 değil, klasik şifre olabilir
    if text.isalpha():
        return False
    try:
        decoded = base64.b85decode(text)
        if len(text) >= 5 and all(32 <= ord(c) <= 117 for c in text):
            # Decode edilen veri anlamlı mı kontrol et (en az birkaç printable karakter)
            printable_ratio = sum(1 for b in decoded if 32 <= b <= 126) / max(len(decoded), 1)
            if printable_ratio > 0.5:
                return True
    except:
        pass
    return False


def detect_base58(text):
    """Base58 formatını tespit eder (Bitcoin/IPFS)."""
    BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    if len(text) >= 6 and all(c in BASE58_CHARS for c in text):
        # Base58'e has: 0, O, I, l karakterleri yok
        has_exclusions = any(c in text for c in "0OIl")
        if not has_exclusions and not text.isalpha():
            return True
    return False


def identify_cipher_format(ciphertext):
    """Verilen metnin olası formatını ve özelliklerini analiz eder."""
    ciphertext = ciphertext.strip()
    analysis = {
        "original_length": len(ciphertext),
        "entropy": calculate_entropy(ciphertext),
        "format": "Unknown",
        "is_numeric": False,
        "is_hex": False,
        "is_base64": False,
        "is_base32": False,
        "is_base85": False,
        "is_base58": False,
        "aes_ecb": None,
        "clean_data": ciphertext,
        "hill_compatibility": [] # Hill Cipher için yeni alan
    }

    # 1. Hexadecimal (On altılık) formatta mı?
    if re.fullmatch(r'[0-9a-fA-F]+', ciphertext) and len(ciphertext) >= 2 and len(ciphertext) % 2 == 0:
        if ciphertext.isdigit() and len(ciphertext) < 20:
            analysis["format"] = "Numeric (Olası RSA/Asimetrik)"
            analysis["is_numeric"] = True
            return analysis
        
        has_hex_alpha = any(c in 'abcdefABCDEF' for c in ciphertext)
        if ciphertext.isdigit() and not has_hex_alpha:
            analysis["format"] = "Numeric (Olası RSA/Asimetrik)"
            analysis["is_numeric"] = True
            return analysis

        analysis["format"] = "Hexadecimal"
        analysis["is_hex"] = True

        if len(ciphertext) >= 64:
            try:
                raw_bytes = bytes.fromhex(ciphertext)
                ecb_result = detect_aes_ecb(raw_bytes)
                if ecb_result:
                    analysis["aes_ecb"] = ecb_result
                    analysis["format"] = "Hexadecimal (AES-ECB Zafiyeti Tespit Edildi!)"
            except:
                pass
        return analysis

    # 3. Base64 formatında mı?
    has_b64_special = any(c in ciphertext for c in '+/=') or any(c.isdigit() for c in ciphertext)
    has_mixed_case = any(c.islower() for c in ciphertext) and any(c.isupper() for c in ciphertext)
    is_likely_base64 = has_b64_special or has_mixed_case

    if is_likely_base64 and re.fullmatch(r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$', ciphertext):
        try:
            decoded = base64.b64decode(ciphertext, validate=True)
            analysis["format"] = "Base64"
            analysis["is_base64"] = True

            if len(decoded) >= 32:
                ecb_result = detect_aes_ecb(decoded)
                if ecb_result:
                    analysis["aes_ecb"] = ecb_result
                    analysis["format"] = "Base64 (AES-ECB Zafiyeti Tespit Edildi!)"
            return analysis
        except Exception:
            pass

    # 4. Base32 formatında mı?
    if detect_base32(ciphertext):
        analysis["format"] = "Base32"
        analysis["is_base32"] = True
        return analysis

    # 5. Base85 formatında mı?
    if detect_base85(ciphertext):
        analysis["format"] = "Base85 (Ascii85)"
        analysis["is_base85"] = True
        return analysis

    # 6. Base58 formatında mı?
    if detect_base58(ciphertext):
        analysis["format"] = "Base58 (Bitcoin/IPFS)"
        analysis["is_base58"] = True
        return analysis

    # 7. Standart Metin ve Hill Cipher Uyumluluk Analizi
    # Sadece harfleri filtreleyip uzunluğa bakıyoruz
    clean_text = "".join(filter(str.isalpha, ciphertext))
    length = len(clean_text)
    
    if length > 0:
        if length % 2 == 0: analysis["hill_compatibility"].append("2x2")
        if length % 3 == 0: analysis["hill_compatibility"].append("3x3")
        if length % 4 == 0: analysis["hill_compatibility"].append("4x4")

    if ciphertext.isalpha():
        analysis["format"] = "Alphabetic Text (Olası Klasik Şifre)"
        # Hill Cipher uyumluluğu varsa formata ek bilgi olarak yazdır
        if analysis["hill_compatibility"]:
            analysis["format"] += f" | Hill Uyumlu: {', '.join(analysis['hill_compatibility'])}"

    return analysis

if __name__ == "__main__":
    # Test Senaryoları
    test_cases = [
        "279013131313",  # Sayısal (Seni ACAM'a yönlendirecek tip)
        "48656c6c6f20576f726c64",  # Hex (Hello World)
        "SGVsbG8gV29ybGQ=",  # Base64 (Hello World)
        "VHIQEKFX"  # Klasik Metin Şifresi
    ]

    print("🔍 VERİ TANIMA MODÜLÜ TESTİ BAŞLIYOR...\n")
    for test in test_cases:
        result = identify_cipher_format(test)
        print(f"Girdi: {test}")
        print(f"Format: {result['format']}")
        print(f"Entropi: {result['entropy']:.2f}")
        print("-" * 40)