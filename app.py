# app.py - ACAM Flask Web Application
import sys
import os
import base64
import time
import tempfile
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad

# brain/ klasörünü Python path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'brain'))

# --- DÜZELTİLMİŞ IMPORT BÖLÜMÜ ---
from classical_ciphers import (
    crack_caesar, crack_vigenere, crack_atbash, crack_affine,
    crack_rail_fence, crack_columnar_transposition, crack_playfair,
    crack_single_byte_xor, crack_multi_byte_xor, calculate_ic
)
from data_identifier import identify_cipher_format
from stego_analyzer import extract_lsb_watermark
from aes_oracle import VulnerableServer, crack_padding_oracle
from hash_cracker import brute_force_hash, identify_hash_type
from des_engine import crack_des_dictionary
from decryptor import wiener_attack, crack_rsa
from primality_testing import run_all_primality_tests
from advanced_factoring import smart_factorize
from meta_learner import train_meta_models, is_model_trained, predict_best_factor_algorithm, predict_best_prime_test

app = Flask(__name__)

# ─── YARDIMCI FONKSİYONLAR ─────────────────────────────────────

COMMON_WORDS = ["THE", "AND", "IS", "TO", "OF", "IN", "FOR", "ARE", "WITH", "THAT", "THIS", "HAVE", "FROM"]

def english_word_score(text):
    # Noktalama işaretlerini temizle ve metni boşluklarla sar
    t = " " + text.upper().replace(".", " ").replace(",", " ").replace("\n", " ") + " "
    score = 0
    for w in COMMON_WORDS:
        # Sadece TAM KELİME eşleşmelerini (boşluklu) sayar. Sahte heceler puan alamaz!
        score += t.count(" " + w + " ") 
    return score

def is_gibberish(text):
    vowels = "AEIOU"
    alpha_text = "".join(c for c in text.upper() if c.isalpha())
    if not alpha_text: return True
    count = sum(1 for c in alpha_text if c in vowels)
    return (count / len(alpha_text)) < 0.2

def run_classical_analysis(target_text, is_hex=False, raw_input=None):
    """Classical pipeline'ın ZEKİ ve ANTI-OVERFITTING versiyonu."""
    candidates = []

    if is_hex and raw_input:
        try:
            hex_bytes = bytes.fromhex(raw_input)
            candidates.append(crack_single_byte_xor(hex_bytes))
            candidates.append(crack_multi_byte_xor(hex_bytes))
        except:
            pass

    candidates.append(crack_caesar(target_text))
    candidates.append(crack_vigenere(target_text))
    candidates.append(crack_atbash(target_text))
    candidates.append(crack_affine(target_text))
    candidates.append(crack_rail_fence(target_text))
    candidates.append(crack_columnar_transposition(target_text))

    clean_alpha = "".join(c for c in target_text if c.isalpha())
    if len(clean_alpha) >= 4 and len(clean_alpha) % 2 == 0:
        candidates.append(crack_playfair(target_text))

    ic = calculate_ic(target_text)

    for c in candidates:
        if c is None: continue
        
        # 🔥 ANTI-OVERFITTING (YAPAY ZEKA FİLTRESİ) 🔥
        
        # 1. Kesin Kelime Puanı (Hile yapılamaz) - Gücünü 2000'den 5000'e çıkardık!
        word_matches = english_word_score(c["text"])
        c["score"] += word_matches * 5000 
        
        # 2. Ockham'ın Usturası (Basitlik İlkesi) ve IC Filtresi
        is_short_text = len(clean_alpha) < 150  # 50 harften kısaysa istatistik yalan söyleyebilir!
        
        # Eğer IC yüksekse VEYA metin çok kısaysa ve kesin kelime bulunduysa basitliğe ödül ver
        if ic > 0.058 or (is_short_text and word_matches > 0):
            if c["type"] in ["Caesar", "Atbash", "Affine"]:
                c["score"] += 5000 # Caesar'ı şahlandır
            elif c["type"] == "Vigenere":
                c["score"] -= 5000 # Vigenere'i ağır cezalandır
                
        # 3. Vigenere Sınırlandırması
        if c["type"] == "Vigenere":
            if ic < 0.055 and not is_short_text and len(c.get("key", "")) > 1:
                c["score"] += 500
                
        if c["type"] == "Vigenere (Sözlük)":
            c["score"] += 1000

        # 4. XOR Güvenilirliği
        if c["type"] == "XOR" and is_hex and not is_gibberish(c["text"]):
            c["score"] += 2000
        if c["type"] == "XOR (Repeating-Key)" and is_hex and not is_gibberish(c["text"]):
            c["score"] += 2000

    filtered = [c for c in candidates if c and not is_gibberish(c["text"])]
    if not filtered:
        filtered = [c for c in candidates if c]

    filtered = sorted(filtered, key=lambda x: x["score"], reverse=True)

    for c in filtered:
        if isinstance(c.get("key"), list):
            c["key"] = str(c["key"])

    best = filtered[0] if filtered else {"type": "Bilinmiyor", "score": 0, "text": "Çözülemedi"}

    return {
        "ic": round(ic, 4),
        "candidates": [
            {
                "type": c["type"],
                "score": c["score"],
                "text": c["text"][:100],
                "key": str(c.get("key", "")),
                "shift": c.get("shift")
            }
            for c in filtered[:5]
        ],
        "best": {
            "type": best.get("type"),
            "score": best.get("score"),
            "text": best.get("text"),
            "key": str(best.get("key", "")),
            "shift": best.get("shift")
        }
    }

def run_rsa_analysis(modulus, ciphertext=None, e=65537):
    """RSA faktorizasyon + çözme işleminin API-dostu versiyonu."""
    try:
        from analysis import extract_features
        from bridge import measure_execution
        import joblib
        import pandas as pd
        import re

        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, 'brain', 'acam_selector.pkl')

        if not os.path.exists(model_path):
            return {"error": "ML model dosyası bulunamadı."}

        features = extract_features(modulus)
        X_input = pd.DataFrame([features])
        model = joblib.load(model_path)
        best_algo_idx = int(model.predict(X_input)[0])

        algo_map = {1: "Pollard's Rho", 2: "Trial Division", 3: "Fermat's Factorization"}
        selected_name = algo_map[best_algo_idx]

        result = measure_execution(modulus, best_algo_idx)

        if result["status"] == "success" and ("Bulunamadi" in result["output"] or result["output"].endswith(": 1")):
            if best_algo_idx != 1:
                result = measure_execution(modulus, 1)
                selected_name = "Pollard's Rho (Fallback)"

        if result["status"] == "success" and "Bulunan Carpan" in result["output"] and not result["output"].endswith(": 1"):
            match = re.search(r'Carpan:\s*(\d+)', result["output"])
            if match:
                p = int(match.group(1))
                q = modulus // p

                response = {
                    "success": True,
                    "algorithm": selected_name,
                    "duration": round(result["duration"], 6),
                    "bit_length": features["bit_length"],
                    "dist_to_square": features["dist_to_square"],
                    "p": p,
                    "q": q
                }

                if ciphertext is not None:
                    decrypted = crack_rsa(p, q, ciphertext, e)
                    if "error" in decrypted:
                        response["decrypt_error"] = decrypted["error"]
                    else:
                        response["d"] = decrypted["d"]
                        response["plaintext_numeric"] = decrypted["numeric"]
                        response["plaintext_text"] = decrypted.get("text")

                return response

        return {"success": False, "message": "Çarpanlara ayrılamadı. Sayı asal olabilir."}

    except Exception as ex:
        return {"error": str(ex)}


# ─── ROUTES ─────────────────────────────────────────────────────

@app.route('/api/padding-oracle', methods=['POST'])
def padding_oracle_attack():
    """AES-CBC Padding Oracle saldırısını web arayüzünden tetikler."""
    data = request.get_json()
    user_cipher_hex = data.get('ciphertext', '').strip()

    server = VulnerableServer()
    
    try:
        if not user_cipher_hex:
            secret_msg = "ACAM SIZMA TESTI BASARILI: GIZLI VERI ELE GECIRILDI"
            ciphertext_bytes = server.encrypt(secret_msg)
        else:
            ciphertext_bytes = bytes.fromhex(user_cipher_hex)

        start_time = time.time()
        
        decrypted_text, attack_steps = crack_padding_oracle(ciphertext_bytes, server.oracle)
        
        elapsed_time = round(time.time() - start_time, 2)

        return jsonify({
            "success": True,
            "decrypted": decrypted_text,
            "steps": attack_steps,
            "time": elapsed_time
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/hash-crack', methods=['POST'])
def api_hash_crack():
    data = request.get_json()
    target_hash = data.get('hash', '').strip()
    start_time = time.time()
    
    res = brute_force_hash(target_hash)
    res['time'] = round(time.time() - start_time, 3)
    return jsonify(res)

@app.route('/api/des-crack', methods=['POST'])
def api_des_crack():
    data = request.get_json()
    cipher_hex = data.get('ciphertext', '').strip()
    start_time = time.time()
    
    res = crack_des_dictionary(cipher_hex)
    res['time'] = round(time.time() - start_time, 3)
    return jsonify(res)    

@app.route('/api/analyze-stego', methods=['POST'])
def analyze_stego():
    """Resimden LSB verisini çıkarır ve otonom kırmaya gönderir."""
    if 'file' not in request.files:
        return jsonify({"error": "Dosya seçilmedi"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Dosya seçilmedi"}), 400

    temp_dir = tempfile.gettempdir()
    filename = secure_filename(file.filename)
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)

    try:
        result = extract_lsb_watermark(file_path)
        
        if result["success"]:
            hidden_text = result["data"]
            decryption_res = run_classical_analysis(hidden_text)
            
            return jsonify({
                "success": True,
                "hidden_raw": hidden_text,
                "analysis": decryption_res
            })
        
        return jsonify({"success": False, "error": result["error"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Şifreli veriyi analiz et ve formatını tespit et."""
    data = request.get_json()
    ciphertext = data.get('ciphertext', '')

    if not ciphertext:
        return jsonify({"error": "Şifreli veri boş olamaz."}), 400

    analysis = identify_cipher_format(ciphertext)
    analysis["entropy"] = round(analysis["entropy"], 2)

    return jsonify(analysis)

@app.route('/api/break', methods=['POST'])
def break_cipher():
    """Ana şifre kırma endpoint'i. Format tespiti + otomatik çözme + Otonom Hash + DES."""
    data = request.get_json()
    ciphertext = data.get('ciphertext', '')

    if not ciphertext:
        return jsonify({"error": "Şifreli veri boş olamaz."}), 400

    analysis = identify_cipher_format(ciphertext)
    analysis["entropy"] = round(analysis["entropy"], 2)

    result = {"analysis": analysis}

    # 🔥 0. AŞAMA: AES-ECB ZAFİYET KONTROLÜ (En Yüksek Öncelik) 🔥
    # Hash'ler tekrarlayan bloklar üretmez (Avalanche effect). 
    # Eğer veri içinde tekrar eden bloklar varsa, bu veri Hash OLAMAZ.
    is_ecb_vulnerable = False
    if analysis.get("aes_ecb"):
        result["aes_ecb_warning"] = analysis["aes_ecb"]
        is_ecb_vulnerable = True

   # 🔥 1. AŞAMA: OTONOM HASH KONTROLÜ 🔥
    if analysis["is_hex"] and not is_ecb_vulnerable:
        # HASH'lerde boşluk affedilmez, o yüzden burada .strip() kullanıyoruz!
        clean_hash = ciphertext.strip().lower() 
        hash_type = identify_hash_type(clean_hash)
        
        if hash_type != "Unknown":
            analysis["format"] = f"{hash_type} Hash Özeti"
            
            start_time = time.time()
            # max_length'i 6 yaptık ki "123456" gibi 6 haneli parolaları da bulabilsin!
            hash_res = brute_force_hash(clean_hash, max_length=6, use_digits=True)
            elapsed_time = time.time() - start_time
            
            if hash_res.get("success"):
                result["decryption"] = {
                    "ic": 0.0,
                    "candidates": [],
                    "best": {
                        "type": f"Otonom Hash Kırıcı ({hash_type})",
                        "score": 10000,
                        "text": hash_res.get("plaintext", ""),
                        "key": f"Süre: {elapsed_time:.2f}sn | Deneme: {hash_res.get('attempts', 0):,}"
                    }
                }
            else:
                result["decryption"] = {
                    "ic": 0.0,
                    "candidates": [],
                    "best": {
                        "type": f"Hash Kırıcı ({hash_type})",
                        "score": 0,
                        "text": "Sözlük ve kaba kuvvet kombinasyonlarında eşleşme bulunamadı.",
                        "key": f"Süre: {elapsed_time:.2f}sn | Deneme: {hash_res.get('attempts', 0):,}"
                    }
                }
            return jsonify(result)

    # 🔥 2. AŞAMA: OTONOM DES SÖZLÜK SALDIRISI 🔥
    if analysis["is_hex"] and not is_ecb_vulnerable:
        des_res = crack_des_dictionary(ciphertext)
        if des_res.get("success"):
            analysis["format"] = f"Modern Şifreleme (DES - {des_res.get('mode', '')})"
            result["decryption"] = {
                "ic": 0.0,
                "candidates": [],
                "best": {
                    "type": f"Otonom DES Kırıcı ({des_res.get('mode', '')})",
                    "score": 9000,
                    "text": des_res.get("plaintext", ""),
                    "key": f"Sözlükten Bulunan Anahtar: {des_res.get('key', '')}"
                }
            }
            return jsonify(result)

    # 🔥 3. AŞAMA: KLASİK ŞİFRELER VE DİĞER FORMATLAR 🔥
    if analysis["is_hex"]:
        try:
            raw_bytes = bytes.fromhex(ciphertext)
            decoded = "".join(chr(b) for b in raw_bytes)
            result["hex_decoded"] = decoded
            
            # Eğer AES-ECB ise, anlamsız veriyi boşuna klasik analize sokup "Çözülemedi" dedirtmeyelim!
            if is_ecb_vulnerable:
                result["decryption"] = {
                    "ic": 0.0, "candidates": [],
                    "best": {
                        "type": "AES-ECB Zafiyet Tespiti",
                        "score": 10000,
                        "text": "Ağ üzerinde şifreli verinin tekrarlayan blokları (pattern) başarıyla tespit edildi. ECB modu güvensizdir ve saldırganlara veri deseni hakkında bilgi sızdırır.",
                        "key": "Zafiyet Doğrulandı"
                    }
                }
            else:
                result["decryption"] = run_classical_analysis(decoded, is_hex=True, raw_input=ciphertext)
        except:
            result["decryption"] = run_classical_analysis(ciphertext)

    elif analysis["is_base64"]:
        if analysis.get("aes_ecb"):
            result["aes_ecb_warning"] = analysis["aes_ecb"]
        try:
            decoded_bytes = base64.b64decode(ciphertext)
            decoded = decoded_bytes.decode('utf-8', errors='replace')
            result["base64_decoded"] = decoded
            result["decryption"] = run_classical_analysis(decoded)
        except:
            result["decryption"] = run_classical_analysis(ciphertext)

    elif analysis.get("is_base32"):
        try:
            decoded = base64.b32decode(ciphertext).decode('utf-8', errors='replace')
            result["base32_decoded"] = decoded
            result["decryption"] = run_classical_analysis(decoded)
        except:
            result["decryption"] = run_classical_analysis(ciphertext)

    elif analysis.get("is_base85"):
        try:
            decoded = base64.b85decode(ciphertext).decode('utf-8', errors='replace')
            result["base85_decoded"] = decoded
            result["decryption"] = run_classical_analysis(decoded)
        except:
            result["decryption"] = run_classical_analysis(ciphertext)

    elif analysis["is_numeric"]:
        result["is_rsa"] = True
        result["message"] = "Sayısal veri tespit edildi. RSA analizi sekmesine yönlendiriliyorsunuz..."

    else:
        result["decryption"] = run_classical_analysis(ciphertext)

    return jsonify(result)

@app.route('/api/run-auto-tests', methods=['GET'])
def run_auto_tests():
    """auto_tester.py dosyasından 36 testin sonucunu çeker ve arayüze iletir."""
    import traceback
    
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')
    if test_dir not in sys.path:
        sys.path.insert(0, test_dir)
        
    try:
        from auto_tester import get_api_test_results
        # run_classical_analysis fonksiyonunu doğrudan içeri yolluyoruz
        results = get_api_test_results(run_classical_analysis)
        return jsonify({"success": True, "tests": results})
    except Exception as e:
        print("\n" + "="*50)
        print("🚨 AUTO-TESTER ÇALIŞTIRILIRKEN KRİTİK HATA:")
        traceback.print_exc()
        print("="*50 + "\n")
        
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/break-rsa', methods=['POST'])
def break_rsa():
    """RSA faktorizasyon ve şifre çözme."""
    data = request.get_json()
    modulus = data.get('modulus')
    ciphertext = data.get('ciphertext')
    e = data.get('e', 65537)

    if not modulus:
        return jsonify({"error": "Modulus (n) değeri gerekli."}), 400

    try:
        modulus = int(modulus)
        ciphertext = int(ciphertext) if ciphertext else None
        e = int(e)
    except ValueError:
        return jsonify({"error": "Geçersiz sayısal değer."}), 400

    result = run_rsa_analysis(modulus, ciphertext, e)
    return jsonify(result)

@app.route('/api/wiener', methods=['POST'])
def wiener():
    """Wiener's Attack endpoint'i."""
    data = request.get_json()
    n = data.get('n')
    e = data.get('e')

    if not n or not e:
        return jsonify({"error": "n ve e değerleri gerekli."}), 400

    try:
        result = wiener_attack(int(n), int(e))
        
        if result.get("success"):
            result["p"] = str(result["p"])
            result["q"] = str(result["q"])
            result["d"] = str(result["d"])
            
        return jsonify(result)
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

# ─── ASALLIK TESTİ & GELİŞMİŞ ÇARPANLARA AYIRMA ──────────────

@app.route('/api/primality-test', methods=['POST'])
def primality_test():
    """Kapsamlı asallık testi: 6 farklı algoritma ile sayıyı test eder."""
    data = request.get_json()
    number_str = data.get('number', '').strip()

    if not number_str:
        return jsonify({"error": "Sayı değeri boş olamaz."}), 400

    try:
        n = int(number_str)
    except ValueError:
        return jsonify({"error": "Geçersiz sayısal değer."}), 400

    if n < 2:
        return jsonify({"error": "Sayı 2 veya daha büyük olmalıdır."}), 400

    start_time = time.time()
    mode = data.get('mode', 'auto')  # meta / race / auto
    result = run_all_primality_tests(n, mode=mode)
    result['api_time'] = round(time.time() - start_time, 6)

    return jsonify(result)


@app.route('/api/advanced-factor', methods=['POST'])
def advanced_factor():
    """Gelişmiş çarpanlara ayırma: 6+ algoritma ile sayıyı faktorize eder."""
    data = request.get_json()
    number_str = data.get('number', '').strip()

    if not number_str:
        return jsonify({"error": "Sayı değeri boş olamaz."}), 400

    try:
        n = int(number_str)
    except ValueError:
        return jsonify({"error": "Geçersiz sayısal değer."}), 400

    if n < 2:
        return jsonify({"error": "Sayı 2 veya daha büyük olmalıdır."}), 400

    start_time = time.time()
    mode = data.get('mode', 'auto')  # meta / race / auto
    result = smart_factorize(n, mode=mode)
    result['api_time'] = round(time.time() - start_time, 6)

    return jsonify(result)


# ─── META-ÖĞRENME EĞİTİM & DURUM ─────────────────────────────

@app.route('/api/meta-status', methods=['GET'])
def meta_status():
    """Meta-öğrenme model durumunu kontrol eder."""
    status = is_model_trained()
    return jsonify(status)


@app.route('/api/meta-train', methods=['POST'])
def meta_train():
    """Meta-öğrenme modellerini benchmark ile eğitir. (Birkaç dakika sürebilir)"""
    try:
        start_time = time.time()
        results = train_meta_models()
        results['training_time'] = round(time.time() - start_time, 2)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ─── HAZIR TEST ÖRNEKLERİ (Frontend için) ──────────────────────
@app.route('/api/test-cases', methods=['GET'])
def get_test_cases():
    """Auto-tester'daki test örneklerini frontend'e sunar."""
    import hashlib

    def enc_caesar(text, shift):
        res = ""
        for c in text:
            if c.isalpha():
                off = 65 if c.isupper() else 97
                res += chr((ord(c) - off + shift) % 26 + off)
            else:
                res += c
        return res

    def enc_vigenere(text, key):
        res, ki = "", 0
        key = key.upper()
        for c in text:
            if c.isalpha():
                s = ord(key[ki % len(key)]) - 65
                off = 65 if c.isupper() else 97
                res += chr((ord(c) - off + s) % 26 + off)
                ki += 1
            else:
                res += c
        return res

    def enc_xor_hex(text, kb):
        return bytes([ord(c) ^ kb for c in text]).hex()

    def enc_atbash(text):
        res = ""
        for c in text:
            if c.isalpha():
                off = 65 if c.isupper() else 97
                res += chr(off + 25 - (ord(c) - off))
            else:
                res += c
        return res

    def enc_affine(text, a, b):
        res = ""
        for c in text:
            if c.isalpha():
                off = 65 if c.isupper() else 97
                x = ord(c) - off
                res += chr((a * x + b) % 26 + off)
            else:
                res += c
        return res

    def enc_rail_fence(text, rails):
        fence = [[] for _ in range(rails)]
        pat = list(range(rails)) + list(range(rails - 2, 0, -1))
        for i, c in enumerate(text):
            fence[pat[i % len(pat)]].append(c)
        return "".join("".join(r) for r in fence)

    def enc_multi_xor_hex(text, keys):
        return bytes([ord(c) ^ keys[i % len(keys)] for i, c in enumerate(text)]).hex()

    def enc_columnar(text, order):
        nc = len(order)
        rows = [text[i:i+nc] for i in range(0, len(text), nc)]
        ct = ""
        for col in order:
            for row in rows:
                if col < len(row):
                    ct += row[col]
        return ct

    def enc_playfair(text, km):
        clean = "".join(c for c in text.upper() if c.isalpha()).replace('J', 'I')
        prep = ""
        i = 0
        while i < len(clean):
            prep += clean[i]
            if i+1 < len(clean):
                if clean[i] == clean[i+1]:
                    prep += 'X'
                else:
                    prep += clean[i+1]
                    i += 1
            i += 1
        if len(prep) % 2 != 0:
            prep += 'X'
        matrix = list(km.upper().replace('J', 'I'))
        def fp(ch):
            idx = matrix.index(ch)
            return idx // 5, idx % 5
        res = ""
        for i in range(0, len(prep), 2):
            r1, c1 = fp(prep[i])
            r2, c2 = fp(prep[i+1])
            if r1 == r2:
                res += matrix[r1*5+(c1+1)%5] + matrix[r2*5+(c2+1)%5]
            elif c1 == c2:
                res += matrix[((r1+1)%5)*5+c1] + matrix[((r2+1)%5)*5+c2]
            else:
                res += matrix[r1*5+c2] + matrix[r2*5+c1]
        return res

    def gen_aes_ecb():
        b1 = bytes([0xAB,0xCD,0xEF,0x12,0x34,0x56,0x78,0x9A,0xBC,0xDE,0xF0,0x11,0x22,0x33,0x44,0x55])
        b2 = bytes([0xFE,0xDC,0xBA,0x98,0x76,0x54,0x32,0x10,0xAA,0xBB,0xCC,0xDD,0xEE,0xFF,0x00,0x11])
        return (b1 + b2 + b1 + b2 + b1).hex()

    def gen_aes_ecb_2():
        b = bytes([0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99,0xAA,0xBB,0xCC,0xDD,0xEE,0xFF,0x00])
        return (b * 4).hex()

    def enc_des_ecb(text, key_str):
        cipher = DES.new(key_str.encode(), DES.MODE_ECB)
        return cipher.encrypt(pad(text.encode(), 8)).hex()

    def enc_des_cbc(text, key_str, iv_str="12345678"):
        iv = iv_str.encode()
        cipher = DES.new(key_str.encode(), DES.MODE_CBC, iv)
        ct = cipher.encrypt(pad(text.encode(), 8))
        return (iv + ct).hex()

    cases = {
        "plaintext": {
            "ciphertext": "This is a perfectly normal English sentence for testing.",
            "info": "Düz metin — şifreleme yok. Sistem bunu tanımalı."
        },
        "caesar3": {
            "ciphertext": enc_caesar("Computer engineering is very cool.", 3),
            "info": "Caesar Shift=3 | Orijinal: Computer engineering is very cool."
        },
        "caesar10": {
            "ciphertext": enc_caesar("Yusuf is doing a great job and you are a great engineer.", 10),
            "info": "Caesar Shift=10 | Orijinal: Yusuf is doing a great job..."
        },
        "vig_acam": {
            "ciphertext": enc_vigenere("Computer engineering is the practice of designing, developing, and testing computer systems and software. It involves a deep understanding of both hardware architecture and software algorithms to build efficient and scalable technological solutions for modern problems.", "ACAM"),
            "info": "Vigenère Key=ACAM | Uzun mühendislik metni"
        },
        "vig_secrets": {
            "ciphertext": enc_vigenere("Cryptography is an indispensable tool for protecting information in computer systems. It provides confidentiality, integrity, and authentication. As computational power increases, we must constantly evolve our cryptographic methods to stay ahead of potential adversarial attacks.", "SECRETS"),
            "info": "Vigenère Key=SECRETS | Kriptografi hakkında uzun metin"
        },
        "vig_acam_long": {
            "ciphertext": enc_vigenere("Computer engineering is a discipline that integrates several fields of computer science and electronics engineering required to develop computer hardware and software. Computer engineers usually have training in electronic engineering, software design, and hardware-software integration instead of only software engineering or electronic engineering.", "ACAM"),
            "info": "Vigenère Key=ACAM | Çok uzun metin (istatistiksel doğrulama)"
        },
        "xor_42": {
            "ciphertext": enc_xor_hex("Secret data is hidden here.", 0x42),
            "info": "Single-byte XOR Key=0x42 | Hex çıktı"
        },
        "hex_vig": {
            "ciphertext": enc_vigenere("Double encryption is highly secure.", "ACAM").encode('utf-8').hex(),
            "info": "Hex + Vigenère Key=ACAM | Çift katman"
        },
        "atbash": {
            "ciphertext": enc_atbash("The quick brown fox jumps over the lazy dog and runs away fast."),
            "info": "Atbash (ayna şifre) | Orijinal: The quick brown fox..."
        },
        "affine": {
            "ciphertext": enc_affine("Affine ciphers are a type of monoalphabetic substitution cipher.", 5, 8),
            "info": "Affine a=5, b=8 | Monoalfabetik yerine koyma"
        },
        "rail_fence": {
            "ciphertext": enc_rail_fence("We are discovered so flee at once to the safe house immediately.", 3),
            "info": "Rail Fence 3 ray | Transpozisyon şifre"
        },
        "b64_caesar": {
            "ciphertext": base64.b64encode(enc_caesar("Base sixty four encoding hides the cipher text underneath nicely.", 5).encode()).decode(),
            "info": "Base64 + Caesar Shift=5 | Kodlama + şifreleme"
        },
        "multi_xor": {
            "ciphertext": enc_multi_xor_hex("Multi byte XOR encryption is stronger than single byte keys.", [0x41, 0x43]),
            "info": "Multi-byte XOR Keys=[0x41, 0x43] | Hex çıktı"
        },
        "columnar": {
            "ciphertext": enc_columnar("The enemy forces are approaching from the north side of the river.", [2, 0, 1]),
            "info": "Columnar Transposition sıra=[2,0,1] | Sütun bazlı"
        },
        "playfair": {
            "ciphertext": enc_playfair("The Playfair cipher is a manual symmetric encryption technique and was the first literal digram substitution cipher. The scheme was invented in eighteen fifty four by Charles Wheatstone but bears the name of Lord Playfair for promoting its use. It involves the creation of a five by five matrix of letters to encrypt pairs of letters. This makes it much harder to break using simple frequency analysis.", "MONARCHYBDEFGIKLPQSTUVWXZ"),
            "info": "Playfair Key=MONARCHY | Digram yerine koyma şifresi"
        },
        "b32_caesar": {
            "ciphertext": base64.b32encode(enc_caesar("Base thirty two encoding is also commonly used in systems.", 3).encode()).decode(),
            "info": "Base32 + Caesar Shift=3 | Farklı kodlama"
        },
        "repeat_xor": {
            "ciphertext": enc_multi_xor_hex("Repeating key XOR uses the same key bytes over and over again to encrypt the full message.", [0x53, 0x45, 0x43]),
            "info": "Repeating-Key XOR [0x53, 0x45, 0x43] | S-E-C anahtarı"
        },
        "aes_ecb_1": {
            "ciphertext": gen_aes_ecb(),
            "info": "AES-ECB tekrarlayan bloklar — zafiyet tespiti beklenir"
        },
        "aes_ecb_2": {
            "ciphertext": gen_aes_ecb_2(),
            "info": "AES-ECB varyasyon 2 — 4 adet aynı blok"
        },
        "hash_md5": {
            "ciphertext": hashlib.md5("acam".encode()).hexdigest(),
            "info": "MD5 Hash | Hedef: 'acam' — brute-force ile kırılır"
        },
        "hash_sha256": {
            "ciphertext": hashlib.sha256("test".encode()).hexdigest(),
            "info": "SHA-256 Hash | Hedef: 'test' — brute-force ile kırılır"
        },
        "des_ecb": {
            "ciphertext": enc_des_ecb("GIZLI VERI", "admin123"),
            "info": "DES ECB Key=admin123 | Sözlük saldırısı ile kırılır"
        },
        "des_cbc": {
            "ciphertext": enc_des_cbc("TOP SECRET", "password", "12345678"),
            "info": "DES CBC Key=password IV=12345678 | Sözlük saldırısı"
        }
    }

    return jsonify(cases)


UPLOAD_FOLDER = 'data/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if __name__ == '__main__':
    # use_reloader=False ekleyerek dosya izleme ve reset atma huyunu kapatıyoruz.
    app.run(debug=True, port=5000, use_reloader=False)