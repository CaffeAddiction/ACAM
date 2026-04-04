# brain/primality_testing.py
# ══════════════════════════════════════════════════════════════════════════
# ACAM Kapsamlı Asallık Test Motoru
# ══════════════════════════════════════════════════════════════════════════
# İçerik:
#   1. Trial Division (Küçük Asallarla Hızlı Eleme)
#   2. Fermat Asallık Testi
#   3. Miller-Rabin Asallık Testi
#   4. Solovay-Strassen Asallık Testi
#   5. Lucas Asallık Testi (Strong Lucas)
#   6. Baillie-PSW Testi (Miller-Rabin + Lucas Hibrit)
#   7. Akıllı Orkestratör (Tüm testleri çalıştırıp güven skoru hesaplar)
# ══════════════════════════════════════════════════════════════════════════

import random
import math
import time

# ─── İlk 1000 asal sayı (Trial Division ve hızlı eleme için) ───────────
def _sieve_small_primes(limit=7920):
    """Eratosthenes Kalburu ile küçük asal sayıları üretir."""
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i*i, limit + 1, i):
                sieve[j] = False
    return [i for i in range(2, limit + 1) if sieve[i]]

SMALL_PRIMES = _sieve_small_primes()  # İlk ~1000 asal sayı

# ══════════════════════════════════════════════════════════════════════════
# 1. TRIAL DIVISION (Küçük Asallarla Hızlı Eleme)
# ══════════════════════════════════════════════════════════════════════════
def trial_division_test(n):
    """
    Küçük asal sayılarla bölünebilirlik kontrolü.
    Eğer bölünüyorsa -> kesinlikle asal değil (ve bölenini döndürür).
    Bölünmüyorsa -> büyük çarpanlar hakkında bilgi vermez (belirsiz).
    """
    if n < 2:
        return {"is_prime": False, "certainty": "DEFINITE", "factor": None, "detail": "2'den küçük sayılar asal değildir."}
    if n in (2, 3):
        return {"is_prime": True, "certainty": "DEFINITE", "factor": None, "detail": f"{n} bilinen küçük asal sayıdır."}
    if n % 2 == 0:
        return {"is_prime": False, "certainty": "DEFINITE", "factor": 2, "detail": "Çift sayılar asal değildir."}
    
    for p in SMALL_PRIMES:
        if p * p > n:
            # n tüm küçük asalların karesinden küçükse kesinlikle asal
            return {"is_prime": True, "certainty": "DEFINITE", "factor": None, 
                    "detail": f"√{n} < {p} olduğundan, trial division ile kesin asal."}
        if n % p == 0:
            return {"is_prime": False, "certainty": "DEFINITE", "factor": p, 
                    "detail": f"{n} sayısı {p} ile bölünebilir."}
    
    return {"is_prime": None, "certainty": "INCONCLUSIVE", "factor": None,
            "detail": f"İlk {len(SMALL_PRIMES)} asal sayı ile bölünemedi. Daha güçlü testler gerekli."}


# ══════════════════════════════════════════════════════════════════════════
# 2. FERMAT ASALLIK TESTİ
# ══════════════════════════════════════════════════════════════════════════
def fermat_test(n, rounds=20):
    """
    Fermat'ın Küçük Teoremi: Eğer n asal ise, a^(n-1) ≡ 1 (mod n).
    DİKKAT: Carmichael sayıları bu testi aldatabilir!
    """
    if n < 2:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "2'den küçük."}
    if n < 4:
        return {"is_prime": True, "certainty": "DEFINITE", "detail": f"{n} bilinen küçük asal."}
    if n % 2 == 0:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "Çift sayı."}
    
    witnesses_tested = []
    for _ in range(rounds):
        a = random.randrange(2, n - 1)
        witnesses_tested.append(a)
        # Fermat testi: a^(n-1) mod n == 1 olmalı
        if pow(a, n - 1, n) != 1:
            return {
                "is_prime": False, "certainty": "DEFINITE",
                "detail": f"Fermat tanığı bulundu: a={a}, a^(n-1) mod n ≠ 1. Kesinlikle bileşik.",
                "witness": a
            }
    
    # Carmichael sayıları (561, 1105, 1729...) tüm turları geçebilir!
    error_prob = 1.0 / (2 ** rounds)
    return {
        "is_prime": True, "certainty": "PROBABLE",
        "confidence": 1.0 - error_prob,
        "rounds": rounds,
        "detail": f"{rounds} tur Fermat testi geçti. Hata olasılığı: 1/{2**rounds}. ⚠️ Carmichael sayılarına karşı savunmasız!",
        "warning": "Carmichael sayıları (ör. 561, 1105, 1729) bu testi aldatabilir."
    }


# ══════════════════════════════════════════════════════════════════════════
# 3. MILLER-RABIN ASALLIK TESTİ
# ══════════════════════════════════════════════════════════════════════════
def _decompose(n):
    """n-1 = 2^s * d formuna ayrıştır (d tek sayı)."""
    s = 0
    d = n - 1
    while d % 2 == 0:
        d //= 2
        s += 1
    return s, d

def miller_rabin_test(n, rounds=40):
    """
    Miller-Rabin Asallık Testi.
    Fermat testinin güçlendirilmiş versiyonu - Carmichael sayılarını da yakalar.
    Her tur hata olasılığını ≤ 1/4 oranında düşürür.
    """
    if n < 2:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "2'den küçük."}
    if n < 4:
        return {"is_prime": True, "certainty": "DEFINITE", "detail": f"{n} bilinen küçük asal."}
    if n % 2 == 0:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "Çift sayı."}
    
    # Deterministic tanıklar (n < 3.317×10^24 için kesin sonuç)
    deterministic_witnesses = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    
    s, d = _decompose(n)
    
    witnesses_used = []
    
    # Önce deterministik tanıkları dene (küçük n için kesin sonuç)
    test_witnesses = [w for w in deterministic_witnesses if w < n]
    
    # Sonra rastgele tanıklar ekle
    for _ in range(max(0, rounds - len(test_witnesses))):
        a = random.randrange(2, n - 1)
        if a not in test_witnesses:
            test_witnesses.append(a)
    
    for a in test_witnesses:
        witnesses_used.append(a)
        x = pow(a, d, n)
        
        if x == 1 or x == n - 1:
            continue
        
        composite = True
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                composite = False
                break
        
        if composite:
            return {
                "is_prime": False, "certainty": "DEFINITE",
                "detail": f"Miller-Rabin tanığı bulundu: a={a}. Sayı kesinlikle bileşik (composite).",
                "witness": a
            }
    
    # Tüm turlar geçildi
    total_rounds = len(witnesses_used)
    error_prob = 1.0 / (4 ** total_rounds)
    
    # n < 3.317×10^24 ve tüm deterministik tanıklar geçildiyse, kesinlikle asal
    if n < 3_317_000_000_000_000_000_000_000 and all(w in witnesses_used for w in deterministic_witnesses if w < n):
        return {
            "is_prime": True, "certainty": "DEFINITE",
            "confidence": 1.0,
            "rounds": total_rounds,
            "detail": f"Deterministik Miller-Rabin: {total_rounds} tanık test edildi. n < 3.317×10²⁴ olduğundan sonuç KESİN."
        }
    
    return {
        "is_prime": True, "certainty": "PROBABLE",
        "confidence": 1.0 - error_prob,
        "rounds": total_rounds,
        "detail": f"{total_rounds} tur Miller-Rabin testi geçti. Hata olasılığı: ≤ 1/{4**total_rounds:,}."
    }


# ══════════════════════════════════════════════════════════════════════════
# 4. SOLOVAY-STRASSEN ASALLIK TESTİ
# ══════════════════════════════════════════════════════════════════════════
def _jacobi_symbol(a, n):
    """Jacobi sembolü (a/n) hesaplar. n tek ve pozitif olmalı."""
    if n <= 0 or n % 2 == 0:
        raise ValueError("n tek ve pozitif olmalı")
    
    a = a % n
    result = 1
    
    while a != 0:
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            result = -result
        a = a % n
    
    return result if n == 1 else 0

def solovay_strassen_test(n, rounds=20):
    """
    Solovay-Strassen Asallık Testi.
    Euler kriteri ve Jacobi sembolünü kullanır.
    a^((n-1)/2) ≡ (a/n) (mod n) olmalı.
    """
    if n < 2:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "2'den küçük."}
    if n < 4:
        return {"is_prime": True, "certainty": "DEFINITE", "detail": f"{n} bilinen küçük asal."}
    if n % 2 == 0:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "Çift sayı."}
    
    for i in range(rounds):
        a = random.randrange(2, n - 1)
        
        jacobi = _jacobi_symbol(a, n) % n
        euler = pow(a, (n - 1) // 2, n)
        
        if jacobi == 0 or euler != jacobi:
            return {
                "is_prime": False, "certainty": "DEFINITE",
                "detail": f"Solovay-Strassen tanığı: a={a}. Euler kriteri sağlanmadı: a^((n-1)/2) ≠ (a/n) mod n.",
                "witness": a
            }
    
    error_prob = 1.0 / (2 ** rounds)
    return {
        "is_prime": True, "certainty": "PROBABLE",
        "confidence": 1.0 - error_prob,
        "rounds": rounds,
        "detail": f"{rounds} tur Solovay-Strassen testi geçti. Hata olasılığı: 1/{2**rounds:,}."
    }


# ══════════════════════════════════════════════════════════════════════════
# 5. LUCAS ASALLIK TESTİ (Strong Lucas Primality Test)
# ══════════════════════════════════════════════════════════════════════════
def _is_perfect_square(n):
    """n tam kare mi kontrolü."""
    if n < 0:
        return False
    root = math.isqrt(n)
    return root * root == n

def _lucas_sequence(n, D, P, Q):
    """
    Lucas dizisi U_k ve V_k değerlerini hesaplar (mod n).
    n-1 = 2^s * d ayrıştırmasını kullanarak verimli hesaplama yapar.
    """
    # n + 1 = 2^s * d
    d = n + 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    
    U = 1
    V = P
    Qk = Q
    
    # Binary method ile U_d, V_d hesapla
    bits = bin(d)[2:]
    
    U_curr = 1
    V_curr = P
    Q_curr = Q
    
    for bit in bits[1:]:
        # Double
        U_curr, V_curr = (U_curr * V_curr) % n, (V_curr * V_curr - 2 * Q_curr) % n
        Q_curr = (Q_curr * Q_curr) % n
        
        if bit == '1':
            # Add
            U_new = (P * U_curr + V_curr)
            V_new = (D * U_curr + P * V_curr)
            if U_new % 2 != 0:
                U_new += n
            if V_new % 2 != 0:
                V_new += n
            U_curr = (U_new // 2) % n
            V_curr = (V_new // 2) % n
            Q_curr = (Q_curr * Q) % n
    
    # U_d ≡ 0 (mod n) kontrolü
    if U_curr == 0 or V_curr == 0:
        return True
    
    # V_{d·2^r} ≡ 0 (mod n) kontrolü (r = 0, 1, ..., s-1)
    for r in range(s):
        if V_curr == 0:
            return True
        V_curr = (V_curr * V_curr - 2 * Q_curr) % n
        Q_curr = (Q_curr * Q_curr) % n
    
    return False

def lucas_test(n):
    """
    Strong Lucas Asallık Testi.
    Selfridge parametreleri (D, P, Q) kullanır.
    Miller-Rabin'den bağımsız bir yaklaşımdır.
    """
    if n < 2:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "2'den küçük."}
    if n < 4:
        return {"is_prime": True, "certainty": "DEFINITE", "detail": f"{n} bilinen küçük asal."}
    if n % 2 == 0:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "Çift sayı."}
    if _is_perfect_square(n):
        return {"is_prime": False, "certainty": "DEFINITE", "detail": f"{n} tam kare bir sayıdır (√{n} = {math.isqrt(n)})."}
    
    # Selfridge parametreleri: D = 5, -7, 9, -11, 13, ... (Jacobi(D,n) = -1 olana dek)
    D = 5
    sign = 1
    for _ in range(100):  # Sonsuz döngüden kaçınmak için limit
        jacobi = _jacobi_symbol(D, n)
        if jacobi == 0:
            # D, n'yi böler -> n bileşik (eğer n != |D|)
            if abs(D) != n:
                return {"is_prime": False, "certainty": "DEFINITE", 
                        "detail": f"gcd(D={D}, n) > 1. Sayı bileşik."}
        if jacobi == -1:
            break  # Uygun D bulundu
        D = -(D + 2 * sign)
        sign = -sign
    else:
        return {"is_prime": None, "certainty": "INCONCLUSIVE",
                "detail": "Uygun Selfridge parametresi bulunamadı."}
    
    P = 1
    Q = (1 - D) // 4
    
    passed = _lucas_sequence(n, D, P, Q)
    
    if passed:
        return {
            "is_prime": True, "certainty": "PROBABLE",
            "confidence": 0.9999,
            "detail": f"Strong Lucas testi geçildi. D={D}, P={P}, Q={Q}. Hata olasılığı çok düşük.",
            "params": {"D": D, "P": P, "Q": Q}
        }
    else:
        return {
            "is_prime": False, "certainty": "DEFINITE",
            "detail": f"Strong Lucas testi başarısız. D={D} ile Lucas koşulu sağlanmadı."
        }


# ══════════════════════════════════════════════════════════════════════════
# 6. BAILLIE-PSW ASALLIK TESTİ (Miller-Rabin + Lucas Hibrit)
# ══════════════════════════════════════════════════════════════════════════
def baillie_psw_test(n):
    """
    Baillie-PSW Asallık Testi.
    Bilinen EN GÜVENİLİR olasılıksal testtir.
    = base-2 Miller-Rabin + Strong Lucas Test
    2^64'e kadar hiçbir karşı-örnek (counterexample) bilinmemektedir!
    """
    if n < 2:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "2'den küçük."}
    if n < 4:
        return {"is_prime": True, "certainty": "DEFINITE", "detail": f"{n} bilinen küçük asal."}
    if n % 2 == 0:
        return {"is_prime": False, "certainty": "DEFINITE", "detail": "Çift sayı."}
    
    # Küçük asallarla hızlı eleme
    for p in SMALL_PRIMES[:50]:
        if n == p:
            return {"is_prime": True, "certainty": "DEFINITE", "detail": f"{n} bilinen küçük asal."}
        if n % p == 0:
            return {"is_prime": False, "certainty": "DEFINITE", "detail": f"{n}, {p} ile bölünebilir.", "factor": p}
    
    # Tam kare kontrolü
    if _is_perfect_square(n):
        return {"is_prime": False, "certainty": "DEFINITE", "detail": f"Tam kare: {n} = {math.isqrt(n)}²"}
    
    steps = []
    
    # ADIM 1: base-2 Miller-Rabin Testi
    s, d = _decompose(n)
    x = pow(2, d, n)
    mr_passed = False
    
    if x == 1 or x == n - 1:
        mr_passed = True
    else:
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                mr_passed = True
                break
    
    if not mr_passed:
        steps.append("❌ base-2 Miller-Rabin: BAŞARISIZ")
        return {
            "is_prime": False, "certainty": "DEFINITE",
            "detail": "Baillie-PSW Adım 1 (base-2 Miller-Rabin) başarısız. Kesinlikle bileşik.",
            "steps": steps
        }
    steps.append("✅ base-2 Miller-Rabin: GEÇTİ")
    
    # ADIM 2: Strong Lucas Testi
    lucas_result = lucas_test(n)
    
    if lucas_result.get("is_prime") == False:
        steps.append("❌ Strong Lucas: BAŞARISIZ")
        return {
            "is_prime": False, "certainty": "DEFINITE",
            "detail": "Baillie-PSW Adım 2 (Strong Lucas) başarısız. Kesinlikle bileşik.",
            "steps": steps
        }
    steps.append("✅ Strong Lucas: GEÇTİ")
    
    return {
        "is_prime": True, "certainty": "ALMOST_CERTAIN",
        "confidence": 0.999999999,
        "detail": "Baillie-PSW testi geçildi. 2⁶⁴'e kadar hiçbir karşı-örneği yoktur. Pratikte kesin asal kabul edilir.",
        "steps": steps
    }


# ══════════════════════════════════════════════════════════════════════════
# 7. AKILLI ORKESTRATÖR (Tüm Testleri Çalıştır, Güven Skoru Hesapla)
# ══════════════════════════════════════════════════════════════════════════
def run_all_primality_tests(n, mode="auto"):
    """
    Verilen sayı üzerinde asallık testlerini çalıştırır.
    
    Modlar:
    - "meta": ML modeli ile en iyi testi tahmin et, sadece onu çalıştır
    - "race": TÜM testleri çalıştırıp karşılaştır (orijinal davranış)
    - "auto": Model varsa meta, yoksa race
    """
    # ── META MOD ──
    meta_prediction = None
    actual_mode = mode
    
    if mode in ("meta", "auto"):
        try:
            from meta_learner import predict_best_prime_test, is_model_trained
            model_status = is_model_trained()
            
            if model_status.get("prime_model"):
                meta_prediction = predict_best_prime_test(n)
                
                if mode == "meta" or (mode == "auto" and meta_prediction.get("confidence", 0) > 0.4):
                    actual_mode = "meta"
                    
                    # Tahmin edilen testi çalıştır
                    test_map = {
                        'trial_division': ('Trial Division (Meta)', lambda: trial_division_test(n)),
                        'fermat': ('Fermat (Meta)', lambda: fermat_test(n)),
                        'miller_rabin': ('Miller-Rabin (Meta)', lambda: miller_rabin_test(n)),
                        'solovay_strassen': ('Solovay-Strassen (Meta)', lambda: solovay_strassen_test(n)),
                        'lucas': ('Lucas (Meta)', lambda: lucas_test(n)),
                        'baillie_psw': ('Baillie-PSW (Meta)', lambda: baillie_psw_test(n)),
                    }
                    
                    predicted = meta_prediction.get("predicted_test", "baillie_psw")
                    test_display, test_func = test_map.get(predicted, test_map['baillie_psw'])
                    
                    total_start = time.time()
                    
                    # 1. ML'nin seçtiği testi çalıştır
                    t0 = time.time()
                    primary_result = test_func()
                    primary_time = round(time.time() - t0, 6)
                    
                    tests_run = [{
                        "name": test_display,
                        "emoji": "🧠",
                        "result": primary_result,
                        "time": primary_time
                    }]
                    
                    # 2. Eğer ML Baillie-PSW seçmediyse, onu da doğrulama olarak çalıştır
                    if predicted != 'baillie_psw':
                        t0 = time.time()
                        bpsw = baillie_psw_test(n)
                        bpsw_time = round(time.time() - t0, 6)
                        tests_run.append({
                            "name": "Baillie-PSW (Doğrulama)",
                            "emoji": "🏆",
                            "result": bpsw,
                            "time": bpsw_time
                        })
                        final_result = bpsw  # Baillie-PSW her zaman güvenilir
                    else:
                        final_result = primary_result
                    
                    total_time = round(time.time() - total_start, 6)
                    
                    # Verdikt oluştur
                    if final_result.get("certainty") == "DEFINITE":
                        if final_result.get("is_prime"):
                            verdict = "KESİNLİKLE ASAL"
                            confidence = 1.0
                        else:
                            verdict = "KESİNLİKLE BİLEŞİK (COMPOSITE)"
                            confidence = 1.0
                    elif final_result.get("certainty") == "ALMOST_CERTAIN":
                        verdict = "BÜYÜK OLASILIKLA ASAL (PROBABLE PRIME)"
                        confidence = final_result.get("confidence", 0.999)
                    else:
                        verdict = "MUHTEMELEN ASAL" if final_result.get("is_prime") else "MUHTEMELEN BİLEŞİK"
                        confidence = final_result.get("confidence", 0.5)
                    
                    return {
                        "number": str(n),
                        "digit_count": len(str(n)),
                        "bit_length": n.bit_length(),
                        "mode": "meta",
                        "meta_prediction": meta_prediction,
                        "tests": tests_run,
                        "total_time": total_time,
                        "is_prime": final_result.get("is_prime"),
                        "confidence": round(confidence, 6),
                        "verdict": verdict,
                        "recommendation": f"Meta-Öğrenme {meta_prediction.get('predicted_test_display', '?')} testini seçti. {meta_prediction.get('reason', '')}",
                        "factor_found": final_result.get("factor")
                    }
            else:
                actual_mode = "race"
        except ImportError:
            actual_mode = "race"
    
    # ── RACE MOD: Tüm testleri çalıştır ──
    results = {
        "number": str(n),
        "digit_count": len(str(n)),
        "bit_length": n.bit_length(),
        "mode": "race",
        "tests": [],
        "total_time": 0
    }
    
    if meta_prediction:
        results["meta_prediction"] = meta_prediction
    
    total_start = time.time()
    
    # ── Test 1: Trial Division ──
    t0 = time.time()
    td_result = trial_division_test(n)
    t1 = time.time()
    results["tests"].append({
        "name": "Trial Division",
        "emoji": "🔢",
        "result": td_result,
        "time": round(t1 - t0, 6)
    })
    
    # Eğer Trial Division kesin sonuç verdiyse, diğer testleri de çalıştır (karşılaştırma için)
    # ama sonucu biliriz
    early_definite = td_result["certainty"] == "DEFINITE" and td_result["is_prime"] is not None
    
    # ── Test 2: Fermat Testi ──
    t0 = time.time()
    fermat_result = fermat_test(n)
    t1 = time.time()
    results["tests"].append({
        "name": "Fermat Testi",
        "emoji": "📐",
        "result": fermat_result,
        "time": round(t1 - t0, 6)
    })
    
    # ── Test 3: Miller-Rabin Testi ──
    t0 = time.time()
    mr_result = miller_rabin_test(n)
    t1 = time.time()
    results["tests"].append({
        "name": "Miller-Rabin Testi",
        "emoji": "🎯",
        "result": mr_result,
        "time": round(t1 - t0, 6)
    })
    
    # ── Test 4: Solovay-Strassen Testi ──
    t0 = time.time()
    ss_result = solovay_strassen_test(n)
    t1 = time.time()
    results["tests"].append({
        "name": "Solovay-Strassen Testi",
        "emoji": "🧮",
        "result": ss_result,
        "time": round(t1 - t0, 6)
    })
    
    # ── Test 5: Lucas Testi ──
    t0 = time.time()
    lucas_result = lucas_test(n)
    t1 = time.time()
    results["tests"].append({
        "name": "Lucas Testi",
        "emoji": "🌀",
        "result": lucas_result,
        "time": round(t1 - t0, 6)
    })
    
    # ── Test 6: Baillie-PSW Testi ──
    t0 = time.time()
    bpsw_result = baillie_psw_test(n)
    t1 = time.time()
    results["tests"].append({
        "name": "Baillie-PSW Testi",
        "emoji": "🏆",
        "result": bpsw_result,
        "time": round(t1 - t0, 6)
    })
    
    results["total_time"] = round(time.time() - total_start, 6)
    
    # ── NİHAİ KARAR VERME (ENSEMBLE / OY VERME) ──
    prime_votes = 0
    composite_votes = 0
    definite_composite = False
    definite_prime = False
    composite_factor = None
    
    # Ağırlıklı oylama: Baillie-PSW en ağır, Fermat en hafif
    weights = {
        "Trial Division": 10,
        "Fermat Testi": 1,
        "Miller-Rabin Testi": 5,
        "Solovay-Strassen Testi": 3,
        "Lucas Testi": 4,
        "Baillie-PSW Testi": 8
    }
    
    for test in results["tests"]:
        r = test["result"]
        w = weights.get(test["name"], 1)
        
        if r.get("is_prime") == True:
            prime_votes += w
            if r.get("certainty") == "DEFINITE":
                definite_prime = True
        elif r.get("is_prime") == False:
            composite_votes += w
            if r.get("certainty") == "DEFINITE":
                definite_composite = True
            if r.get("factor"):
                composite_factor = r["factor"]
    
    total_weight = prime_votes + composite_votes
    
    if definite_composite:
        results["is_prime"] = False
        results["confidence"] = 1.0
        results["verdict"] = "KESİNLİKLE BİLEŞİK (COMPOSITE)"
        if composite_factor:
            results["factor_found"] = composite_factor
            results["recommendation"] = f"Sayı kesinlikle bileşik. Bulunan bölen: {composite_factor}. Çarpanlara ayırma analizi başlatılabilir."
        else:
            results["recommendation"] = "Sayı kesinlikle bileşik. Çarpanlarını bulmak için Gelişmiş Faktorizasyon sekmesini kullanın."
    elif definite_prime:
        results["is_prime"] = True
        results["confidence"] = 1.0
        results["verdict"] = "KESİNLİKLE ASAL"
        results["recommendation"] = "Bu sayı kesinlikle asaldır. RSA gibi kriptografik sistemlerde güvenle kullanılabilir."
    elif total_weight > 0:
        confidence = prime_votes / total_weight
        results["is_prime"] = confidence > 0.5
        results["confidence"] = round(confidence, 6)
        
        if confidence > 0.95:
            results["verdict"] = "BÜYÜK OLASILIKLA ASAL (PROBABLE PRIME)"
            results["recommendation"] = f"Güven skoru: %{confidence*100:.4f}. 6 farklı test bu sayıyı asal olarak değerlendirdi."
        elif confidence > 0.5:
            results["verdict"] = "MUHTEMELEN ASAL"
            results["recommendation"] = "Bazı testler çelişkili sonuç verdi. Daha fazla tur ile tekrar deneyin."
        else:
            results["verdict"] = "MUHTEMELEN BİLEŞİK"
            results["recommendation"] = "Testlerin çoğunluğu sayının bileşik olduğunu gösteriyor."
    else:
        results["is_prime"] = None
        results["confidence"] = 0.0
        results["verdict"] = "BELİRSİZ"
        results["recommendation"] = "Yeterli bilgi toplanamadı."
    
    return results


# ══════════════════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Test: Bilinen asal sayıları dene
    test_numbers = [
        2, 7, 13, 561,  # 561 = Carmichael sayısı (Fermat'ı aldatır!)
        1729,            # Ramanujan sayısı, aynı zamanda Carmichael
        104729,          # Asal
        999999999989,    # Büyük asal
        15485863,        # 1 milyonuncu asal
        100000004987,    # Asal
    ]
    
    for n in test_numbers:
        result = run_all_primality_tests(n)
        print(f"\n{'='*60}")
        print(f"Sayı: {n}")
        print(f"Sonuç: {result['verdict']}")
        print(f"Güven: {result.get('confidence', 'N/A')}")
        print(f"Toplam süre: {result['total_time']}s")
