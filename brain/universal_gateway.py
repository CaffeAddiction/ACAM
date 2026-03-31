import base64
import time
from data_identifier import identify_cipher_format
from acam_controller import run_acam_final
from classical_ciphers import *
# Yeni eklenen modüller
from hash_cracker import brute_force_hash, identify_hash_type
from des_engine import crack_des_dictionary

COMMON_WORDS = ["THE","AND","IS","TO","OF","IN"]

def english_word_score(text):
    t = text.upper()
    return sum(1 for w in COMMON_WORDS if w in t)

def is_gibberish(text):
    vowels = "AEIOU"
    count = sum(1 for c in text.upper() if c in vowels)
    return (count / max(len(text),1)) < 0.2

def run_classical_pipeline(target_text, is_hex=False, raw_input=None):
    candidates = []

    # 🔥 XOR (tek ve çoklu byte) - sadece hex girdi için
    if is_hex and raw_input:
        try:
            hex_bytes = bytes.fromhex(raw_input)
            candidates.append(crack_single_byte_xor(hex_bytes))
            candidates.append(crack_multi_byte_xor(hex_bytes))
        except:
            pass

    # Klasik yerine koyma şifreleri
    candidates.append(crack_caesar(target_text))
    candidates.append(crack_vigenere(target_text))
    candidates.append(crack_atbash(target_text))
    candidates.append(crack_affine(target_text))

    # Transpozisyon şifreleri
    candidates.append(crack_rail_fence(target_text))
    candidates.append(crack_columnar_transposition(target_text))

    # Playfair (sadece çift sayıda harf içeren metinler için)
    clean_alpha = "".join(c for c in target_text if c.isalpha())
    if len(clean_alpha) >= 4 and len(clean_alpha) % 2 == 0:
        candidates.append(crack_playfair(target_text))

    ic = calculate_ic(target_text)

    # 🔥 Heuristic Boosts
    for c in candidates:
        if not c: continue
        
        if c["type"] == "Vigenere" and ic < 0.05 and len(c.get("key", "")) > 1:
            c["score"] += 200

        if c["type"] == "Vigenere (Sözlük)":
            c["score"] += 100

        if c["type"] == "XOR" and is_hex and not is_gibberish(c["text"]):
            c["score"] += 150

        if c["type"] == "XOR (Repeating-Key)" and is_hex and not is_gibberish(c["text"]):
            c["score"] += 100

        c["score"] += english_word_score(c["text"]) * 50

    # 🔥 Gibberish Filter
    filtered = [c for c in candidates if c and not is_gibberish(c["text"])]
    if not filtered:
        filtered = [c for c in candidates if c]

    filtered = sorted(filtered, key=lambda x: x["score"], reverse=True)

    print(f"\n📊 Metin Analizi (IC): {ic:.4f}")
    print("\n🔬 TOP 5 ADAY:")
    for c in filtered[:5]:
        print(f"{c['type']} | score={c['score']} → {c['text'][:60]}")

    best = filtered[0]
    print(f"\n✅ Tespit Edilen Algoritma: {best.get('type').upper()}")

    if "shift" in best:
        print(f"🗝️  Kaydırma (Shift): {best['shift']}")
    if "key" in best:
        print(f"🗝️  Gizli Anahtar/Key: {best['key']}")

    print(f"🎉 ÇÖZÜLEN METİN: {best['text']}")

def main():
    while True:
        ciphertext = input("\n🕵️ ACAM > Şifreli veri girin (Çıkış: q): ").strip()
        if ciphertext.lower() == 'q' or not ciphertext:
            break

        # 1. HASH TESPİTİ (ÖNCELİKLİ)
        hash_type = identify_hash_type(ciphertext)
        if hash_type != "Unknown":
            print(f"\n🚀 HASH TESPİT EDİLDİ: {hash_type}")
            choice = input(f"Bu bir {hash_type} özeti. Brute-force denensin mi? (e/h): ")
            if choice.lower() == 'e':
                res = brute_force_hash(ciphertext)
                if res["success"]:
                    print(f"✅ HASH KIRILDI! -> Orijinal Metin: {res['plaintext']}")
                    print(f"⏱️ Süre: {res['time']}s | Deneme: {res['attempts']}")
                else:
                    print(f"❌ {res['error']}")
            continue

        # 2. FORMAT ANALİZİ
        analysis = identify_cipher_format(ciphertext)
        print(f"\n🔍 Analiz: {analysis['format']} (Entropi: {analysis['entropy']:.2f})")

        # RSA / Nümerik Durumu
        if analysis["is_numeric"]:
            n_val = input("Lütfen Modulus (n) girin: ")
            if n_val.isdigit():
                run_acam_final(int(n_val))

        # Hex Durumu (AES-ECB, DES, XOR veya Klasik)
        elif analysis["is_hex"]:
            # DES Denemesi
            print("🔬 DES Sözlük Saldırısı deneniyor...")
            des_res = crack_des_dictionary(ciphertext)
            if des_res["success"]:
                print(f"✅ DES ANAHTARI BULUNDU! [{des_res['mode']}]")
                print(f"🗝️ Anahtar: {des_res['key']} | Metin: {des_res['plaintext']}")
                continue

            if analysis.get("aes_ecb"):
                ecb = analysis["aes_ecb"]
                print(f"\n🚨 AES-ECB ZAFİYETİ TESPİT EDİLDİ!")
                print(f"   Tekrar Oranı: {ecb['repetition_ratio']:.1%}")

            try:
                raw_bytes = bytes.fromhex(ciphertext)
                decoded = "".join(chr(b) for b in raw_bytes if 32 <= b <= 126 or b in [10, 13])
                print("\n🧪 HEX decode:", decoded if decoded else "[Okunamayan Veri]")
                run_classical_pipeline(decoded if decoded else ciphertext, is_hex=True, raw_input=ciphertext)
            except:
                run_classical_pipeline(ciphertext)

        # Base64 / Base32 Durumları
        elif analysis["is_base64"] or analysis.get("is_base32"):
            try:
                if analysis["is_base64"]:
                    decoded = base64.b64decode(ciphertext).decode('utf-8', errors='replace')
                else:
                    decoded = base64.b32decode(ciphertext).decode('utf-8', errors='replace')
                print(f"\n🧪 DECODE: {decoded}")
                run_classical_pipeline(decoded)
            except:
                run_classical_pipeline(ciphertext)

        else:
            run_classical_pipeline(ciphertext)

if __name__ == "__main__":
    main()