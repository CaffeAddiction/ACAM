# brain/acam_controller.py
import os
import joblib
import pandas as pd
import re
from bridge import measure_execution
from analysis import extract_features
from decryptor import crack_rsa, wiener_attack

def run_acam_final(number):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base_dir, 'brain', 'acam_selector.pkl')
    
    if not os.path.exists(model_path):
        print("Hata: Model dosyası bulunamadı! Önce predictor.py çalıştırılmalı.")
        return

    # 1. Analiz Katmanı
    features = extract_features(number)
    X_input = pd.DataFrame([features]) 
    
    # 2. Zeka Katmanı
    model = joblib.load(model_path)
    best_algo_idx = int(model.predict(X_input)[0])
    
    algo_map = {1: "Pollard's Rho", 2: "Trial Division", 3: "Fermat's Factorization"}
    selected_name = algo_map[best_algo_idx]

    print(f"\n" + "="*50)
    print(f"🚀 ACAM INTELLIGENT FACTORING & DECRYPTION ENGINE")
    print(f"="*50)
    print(f"🔢 Girdi (n): {number}")
    print(f"📊 Analiz: {features['bit_length']} bit | Δ²: {features['dist_to_square']:.0f}")
    print(f"🧠 AI Kararı: {selected_name}")
    print(f"..." + "-"*46)

    # 3. Yürütme Katmanı
    print(f"Sistem {selected_name} motorunu ateşliyor...")
    result = measure_execution(number, best_algo_idx)
    
    if result["status"] == "success" and ("Bulunamadi" in result["output"] or result["output"].endswith(": 1")):
        print(f"⚠️  {selected_name} ile sonuç alınamadı. Fallback başlatılıyor...")
        
        if best_algo_idx != 1:
            print("🔄 B Planı: Pollard's Rho devreye giriyor...")
            result = measure_execution(number, 1)
        
        if "Bulunamadi" in result["output"]:
            print(f"🔍 ANALİZ SONUCU: Bu sayı ({number}) yüksek ihtimalle bir ASAL SAYI.")
    
    # 4. Çıktı ve DECRYPTION (Şifre Çözme) Aşaması
    if result["status"] == "success" and "Bulunan Carpan" in result["output"] and not result["output"].endswith(": 1"):
        print(f"✅ Çarpanlara Ayırma Tamamlandı! ({result['duration']:.6f} saniye)")
        
        # C++ Çıktısından Çarpanı (p) Çekip Çıkar
        match = re.search(r'Carpan:\s*(\d+)', result["output"])
        if match:
            p = int(match.group(1))
            q = number // p
            
            print(f"🔑 Bulunan Çarpanlar:")
            print(f"   p = {p}")
            print(f"   q = {q}")
            print("-" * 50)
            
            # Kullanıcıdan Şifreli Metni İste
            ct_input = input("🔓 Şifreyi çözmek için Ciphertext girin (Atlamak için 'Enter'a basın): ")
            
            if ct_input.strip():
                try:
                    ciphertext = int(ct_input.strip())
                    print("⚙️  Gizli anahtar hesaplanıyor ve şifre çözülüyor...")
                    
                    decrypted_data = crack_rsa(p, q, ciphertext)
                    
                    if "error" in decrypted_data:
                        print(f"❌ Kripto Hatası: {decrypted_data['error']}")
                    else:
                        print(f"🗝️  Elde Edilen Gizli Anahtar (d): {decrypted_data['d']}")
                        
                        if decrypted_data['text']:
                            print(f"🎉 ÇÖZÜLEN METİN: {decrypted_data['text']}")
                        else:
                            print(f"🔢 ÇÖZÜLEN SAYISAL VERİ: {decrypted_data['numeric']}")
                            
                except ValueError:
                    print("❌ Hata: Ciphertext sadece sayılardan oluşmalıdır.")
    else:
        # result içinde 'output' anahtarı var mı diye güvenli kontrol yapıyoruz
        if "output" in result and "Bulunamadi" not in result["output"]:
            print(f"❌ Beklenmeyen Hata: {result['output']}")
        elif "error" in result:
            print(f"❌ Motor Hatası (C++ exe bulunamadı veya çalışmadı): {result['error']}")
            
    print("="*50 + "\n")

def run_wiener_attack(n, e):
    """Wiener's Attack ile zayıf RSA anahtarını kırar."""
    print(f"\n" + "="*50)
    print(f"🚀 WIENER'S ATTACK (Sürekli Kesirler)")
    print(f"="*50)
    print(f"🔢 n = {n}")
    print(f"🔢 e = {e}")
    print(f"📊 Analiz: {n.bit_length()} bit modulus")
    print("-"*50)

    result = wiener_attack(n, e)

    if result["success"]:
        print(f"✅ Wiener's Attack Başarılı!")
        print(f"🔑 Bulunan Çarpanlar:")
        print(f"   p = {result['p']}")
        print(f"   q = {result['q']}")
        print(f"🗝️  Gizli Anahtar (d) = {result['d']}")
    else:
        print(f"❌ Wiener's Attack başarısız - d yeterince küçük değil.")

    print("="*50 + "\n")
    return result


if __name__ == "__main__":
    while True:
        val = input("Analiz edilecek sayıyı (n) girin (Çıkış: q): ")
        if val.lower() == 'q':
            break
        try:
            run_acam_final(int(val))
        except ValueError:
            print("Lütfen geçerli bir sayı girin.")