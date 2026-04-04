# brain/advanced_factoring.py
# ══════════════════════════════════════════════════════════════════════════
# ACAM Gelişmiş Çarpanlara Ayırma (Advanced Factoring) Motoru
# ══════════════════════════════════════════════════════════════════════════
# İçerik:
#   1. Trial Division (Küçük asallarla tarama)
#   2. Pollard's Rho (Python implementasyonu, C++ fallback'i)
#   3. Pollard's p-1 Algoritması
#   4. Williams' p+1 Algoritması
#   5. Lenstra ECM (Elliptic Curve Method) - Basitleştirilmiş
#   6. Fermat Faktorizasyon (Python implementasyonu)
#   7. Akıllı Orkestratör (sayı özelliklerine göre en iyi algoritmayı seçer)
# ══════════════════════════════════════════════════════════════════════════

import math
import random
import time
import os
import subprocess

# Küçük asal sayılar listesi (hızlı kontrol için)
SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
                53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107,
                109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167,
                173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229,
                233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283,
                293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359,
                367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431,
                433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491,
                499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571,
                577, 587, 593, 599, 601, 607, 613, 617, 619, 631, 641,
                643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 709,
                719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787,
                797, 809, 811, 821, 823, 827, 829, 839, 853, 857, 859,
                863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941,
                947, 953, 967, 971, 977, 983, 991, 997]


# ══════════════════════════════════════════════════════════════════════════
# 1. TRIAL DIVISION FACTORIZATION
# ══════════════════════════════════════════════════════════════════════════
def trial_division_factor(n, limit=100000):
    """
    Küçük asal sayılarla ardışık bölme.
    Küçük çarpanları hızlıca bulur ama büyük asallar için çok yavaştır.
    """
    if n <= 1:
        return {"success": False, "error": "n > 1 olmalı"}
    
    factors = []
    d = 2
    original_n = n
    
    while d * d <= n and d <= limit:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1 if d == 2 else 2
    
    if n > 1:
        factors.append(n)
    
    if len(factors) == 1 and factors[0] == original_n:
        return {"success": False, "error": "Çarpan bulunamadı (limit dahilinde)"}
    
    return {
        "success": True,
        "factors": factors,
        "p": factors[0] if len(factors) >= 2 else factors[0],
        "q": original_n // factors[0] if factors[0] != original_n else 1
    }


# ══════════════════════════════════════════════════════════════════════════
# 2. POLLARD'S RHO (Python implementasyonu)
# ══════════════════════════════════════════════════════════════════════════
def pollard_rho_factor(n, max_iterations=1_000_000):
    """
    Pollard's Rho algoritması - Floyd'un döngü tespiti ile.
    O(n^(1/4)) karmaşıklığında, orta büyüklükte sayılar için etkili.
    """
    if n <= 1:
        return {"success": False, "error": "n > 1 olmalı"}
    if n % 2 == 0:
        return {"success": True, "p": 2, "q": n // 2, "algorithm": "Pollard's Rho"}
    
    for _ in range(10):  # Farklı başlangıç noktalarıyla dene
        x = random.randrange(2, n)
        y = x
        c = random.randrange(1, n)
        d = 1
        
        iteration = 0
        while d == 1 and iteration < max_iterations:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = math.gcd(abs(x - y), n)
            iteration += 1
        
        if 1 < d < n:
            return {
                "success": True,
                "p": d,
                "q": n // d,
                "algorithm": "Pollard's Rho",
                "iterations": iteration
            }
    
    return {"success": False, "error": "Pollard's Rho ile çarpan bulunamadı."}


# ══════════════════════════════════════════════════════════════════════════
# 3. POLLARD'S p-1 ALGORITHM
# ══════════════════════════════════════════════════════════════════════════
def pollard_p_minus_1(n, B1=100000, B2=1000000):
    """
    Pollard's p-1 algoritması.
    p-1'in küçük asal çarpanları olduğunda (smooth) çok etkilidir.
    
    Teori: Eğer p | n ve (p-1) B-smooth ise:
    a^(B!) ≡ 1 (mod p) → gcd(a^(B!) - 1, n) bir çarpan verir.
    
    B1: Stage 1 sınırı (tüm küçük asallar)
    B2: Stage 2 sınırı (bir büyük asal faktör)
    """
    if n <= 1:
        return {"success": False, "error": "n > 1 olmalı"}
    if n % 2 == 0:
        return {"success": True, "p": 2, "q": n // 2, "algorithm": "Pollard's p-1"}
    
    a = 2  # Başlangıç tabanı
    
    # ── STAGE 1: B1-smooth çarpanlar ──
    # a^(B1!) mod n hesapla (verimli yol: her asal üssünü sırayla uygula)
    for p in SMALL_PRIMES:
        if p > B1:
            break
        # p^k <= B1 olan en büyük k'yı bul
        pk = p
        while pk * p <= B1:
            pk *= p
        a = pow(a, pk, n)
    
    # GCD kontrolü
    d = math.gcd(a - 1, n)
    
    if 1 < d < n:
        return {
            "success": True,
            "p": d,
            "q": n // d,
            "algorithm": "Pollard's p-1 (Stage 1)",
            "B1": B1,
            "detail": f"p-1 sayısı B1={B1}-smooth. Stage 1'de çarpan bulundu."
        }
    
    if d == n:
        return {"success": False, "error": "Stage 1'de trivial çarpan (n). Farklı parametreler gerekli."}
    
    # ── STAGE 2: Bir büyük asal çarpan (B1 < q <= B2) ──
    # Büyük asalları tek tek dene
    prev_p = B1
    # Stage 2 için B1'den B2'ye kadar asalları üret (basit elek)
    for candidate in range(B1 + 1, min(B2, B1 + 100000)):
        # Basit asallık kontrolü
        is_p = True
        if candidate < 2:
            continue
        for small_p in SMALL_PRIMES:
            if small_p * small_p > candidate:
                break
            if candidate % small_p == 0:
                is_p = False
                break
        if not is_p:
            continue
        
        a = pow(a, candidate, n)
        d = math.gcd(a - 1, n)
        
        if 1 < d < n:
            return {
                "success": True,
                "p": d,
                "q": n // d,
                "algorithm": "Pollard's p-1 (Stage 2)",
                "B1": B1,
                "B2": candidate,
                "detail": f"Stage 2'de çarpan bulundu. p-1'in en büyük asal çarpanı ≈ {candidate}."
            }
        
        if d == n:
            break
    
    return {"success": False, "error": f"Pollard's p-1 ile çarpan bulunamadı (B1={B1}, B2={B2})."}


# ══════════════════════════════════════════════════════════════════════════
# 4. WILLIAMS' p+1 ALGORITHM
# ══════════════════════════════════════════════════════════════════════════
def williams_p_plus_1(n, B=100000):
    """
    Williams' p+1 algoritması.
    p+1'in küçük asal çarpanları (smooth) olduğunda etkilidir.
    Lucas dizilerini kullanır.
    
    Pollard p-1'in tamamlayıcısıdır: p-1 smooth değilse p+1 smooth olabilir.
    """
    if n <= 1:
        return {"success": False, "error": "n > 1 olmalı"}
    if n % 2 == 0:
        return {"success": True, "p": 2, "q": n // 2, "algorithm": "Williams' p+1"}
    
    # Birden fazla başlangıç noktası dene
    for seed in range(3, 20):
        v = seed
        
        for p in SMALL_PRIMES:
            if p > B:
                break
            pk = p
            while pk * p <= B:
                pk *= p
            
            # Lucas chain: V_pk hesapla
            # V(2k) = V(k)^2 - 2 ve V(2k+1) = V(k)*V(k+1) - P kullanarak
            # Binary method ile hızlı hesaplama
            vl = v
            vh = (v * v - 2) % n
            
            bits = bin(pk)[3:]  # İlk bit atlanır
            for bit in bits:
                if bit == '0':
                    vh = (vl * vh - v) % n
                    vl = (vl * vl - 2) % n
                else:
                    vl = (vl * vh - v) % n
                    vh = (vh * vh - 2) % n
            v = vl
        
        d = math.gcd(v - 2, n)
        
        if 1 < d < n:
            return {
                "success": True,
                "p": d,
                "q": n // d,
                "algorithm": "Williams' p+1",
                "seed": seed,
                "B": B,
                "detail": f"p+1 sayısı B={B}-smooth. Seed={seed} ile çarpan bulundu."
            }
    
    return {"success": False, "error": f"Williams' p+1 ile çarpan bulunamadı (B={B})."}


# ══════════════════════════════════════════════════════════════════════════
# 5. LENSTRA ECM (Elliptic Curve Method) - Basitleştirilmiş
# ══════════════════════════════════════════════════════════════════════════
def _ecm_add(P, Q, n):
    """Eliptik eğri üzerinde nokta toplama (mod n)."""
    if P is None:
        return Q
    if Q is None:
        return P
    
    x1, y1 = P
    x2, y2 = Q
    
    if x1 == x2:
        if (y1 + y2) % n == 0:
            return None  # Sonsuz nokta
        # Nokta ikileştirme (doubling)
        denom = (2 * y1) % n
    else:
        denom = (x2 - x1) % n
    
    try:
        inv = pow(denom, -1, n)
    except (ValueError, ZeroDivisionError):
        # Modüler ters bulunamadı → gcd(denom, n) bir çarpan olabilir!
        d = math.gcd(denom, n)
        if 1 < d < n:
            raise ValueError(d)  # Çarpan bulundu!
        return None
    
    if x1 == x2:
        # a katsayısını global olarak alıyoruz (dışarıdan gelmeli)
        # Basitleştirme: a=0 kullan
        lam = (3 * x1 * x1) * inv % n
    else:
        lam = (y2 - y1) * inv % n
    
    x3 = (lam * lam - x1 - x2) % n
    y3 = (lam * (x1 - x3) - y1) % n
    
    return (x3, y3)

def _ecm_multiply(k, P, n):
    """Eliptik eğri üzerinde skaler çarpma (double-and-add)."""
    result = None
    addend = P
    
    while k > 0:
        if k & 1:
            result = _ecm_add(result, addend, n)
        addend = _ecm_add(addend, addend, n)
        k >>= 1
    
    return result

def lenstra_ecm(n, curves=100, B1=10000):
    """
    Lenstra'nın Eliptik Eğri Metodu (ECM).
    Eğriler üzerinde nokta çarpımı yaparken modüler ters alamazsa,
    gcd hesaplamasıyla çarpan bulur.
    
    Avantaj: En küçük çarpanın boyutuna bağlıdır (n'in boyutuna değil).
    20-30 basamaklı çarpanları bulmada çok etkilidir.
    """
    if n <= 1:
        return {"success": False, "error": "n > 1 olmalı"}
    if n % 2 == 0:
        return {"success": True, "p": 2, "q": n // 2, "algorithm": "Lenstra ECM"}
    
    for curve_num in range(curves):
        # Rastgele bir nokta ve eğri seç
        x0 = random.randrange(2, n)
        y0 = random.randrange(2, n)
        a = random.randrange(2, n)
        # b = y0^2 - x0^3 - a*x0 (mod n)  →  eğri bu noktadan geçsin
        
        P = (x0, y0)
        
        try:
            # B1! ile skaler çarpma
            for p in SMALL_PRIMES:
                if p > B1:
                    break
                pk = p
                while pk * p <= B1:
                    pk *= p
                P = _ecm_multiply(pk, P, n)
                if P is None:
                    break
        except ValueError as factor_found:
            d = int(str(factor_found))
            if 1 < d < n:
                return {
                    "success": True,
                    "p": d,
                    "q": n // d,
                    "algorithm": "Lenstra ECM",
                    "curve_number": curve_num + 1,
                    "B1": B1,
                    "detail": f"ECM: {curve_num + 1}. eğride çarpan bulundu! B1={B1}."
                }
    
    return {"success": False, "error": f"ECM ile çarpan bulunamadı ({curves} eğri, B1={B1})."}


# ══════════════════════════════════════════════════════════════════════════
# 6. FERMAT FAKTORIZASYON (Python implementasyonu)
# ══════════════════════════════════════════════════════════════════════════
def fermat_factor(n, max_iterations=1_000_000):
    """
    Fermat'ın Çarpanlara Ayırma Yöntemi.
    n = a² - b² = (a+b)(a-b) formunda çarpan arar.
    Çarpanlar birbirine yakın olduğunda çok hızlıdır.
    """
    if n <= 1:
        return {"success": False, "error": "n > 1 olmalı."}
    if n % 2 == 0:
        return {"success": True, "p": 2, "q": n // 2, "algorithm": "Fermat Faktorizasyon"}
    
    a = math.isqrt(n)
    if a * a == n:
        return {"success": True, "p": a, "q": a, "algorithm": "Fermat Faktorizasyon",
                "detail": f"Tam kare: {n} = {a}²"}
    
    a += 1
    
    for iteration in range(max_iterations):
        b2 = a * a - n
        b = math.isqrt(b2)
        
        if b * b == b2:
            p = a - b
            q = a + b
            if p > 1 and q > 1:
                return {
                    "success": True,
                    "p": p,
                    "q": q,
                    "algorithm": "Fermat Faktorizasyon",
                    "iterations": iteration + 1,
                    "detail": f"n = {a}² - {b}² = ({a}-{b})({a}+{b})"
                }
        a += 1
    
    return {"success": False, "error": "Fermat faktorizasyon ile çarpan bulunamadı."}


# ══════════════════════════════════════════════════════════════════════════
# 7. C++ MOTORU İLE FAKTORIZASYON (Mevcut factor.exe)
# ══════════════════════════════════════════════════════════════════════════
def cpp_engine_factor(n, algo_choice=1):
    """
    Mevcut C++ motorunu (factor.exe) çalıştırır.
    algo_choice: 1=Pollard's Rho, 2=Trial Division, 3=Fermat
    """
    import re
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base_dir, 'engine', 'factor.exe')
    
    if not os.path.exists(exe_path):
        return {"success": False, "error": "C++ motoru (factor.exe) bulunamadı."}
    
    algo_names = {1: "Pollard's Rho (C++)", 2: "Trial Division (C++)", 3: "Fermat (C++)"}
    
    try:
        # Windows'ta CREATE_NO_WINDOW flag'i ile çalıştır, timeout 10s
        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.run(
            [exe_path, str(n), str(algo_choice)],
            capture_output=True, text=True, timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        
        if process.returncode != 0:
            return {"success": False, "error": f"C++ motoru hata döndürdü: {process.stderr}"}
        
        output = process.stdout.strip()
        match = re.search(r'Carpan:\s*(\d+)', output)
        
        if match:
            p = int(match.group(1))
            if p > 1 and p != n:
                return {
                    "success": True,
                    "p": p,
                    "q": n // p,
                    "algorithm": algo_names.get(algo_choice, "C++ Engine"),
                    "detail": output
                }
        
        return {"success": False, "error": f"C++ motoru çarpan bulamadı: {output}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "C++ motoru zaman aşımına uğradı (10s)."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════
# 8. AKILLI ORKESTRATÖR (Tüm Algoritmaları Çalıştır + En İyisini Seç)
# ══════════════════════════════════════════════════════════════════════════
def smart_factorize(n, mode="auto"):
    """
    Verilen sayıyı çarpanlarına ayırmak için algoritmalar çalıştırır.
    
    Modlar:
    - "meta": ML modeli ile en iyi algoritmayı tahmin et, sadece onu çalıştır
    - "race": TÜM algoritmaları çalıştırıp yarıştır (orijinal davranış)
    - "auto": Model varsa meta, yoksa race
    
    Döndürülen yapı:
    {
        "number": n,
        "mode": "meta" / "race",
        "success": True/False,
        "best_result": { ... },
        "all_results": [ { "algorithm": ..., "result": ..., "time": ... } ],
        "total_time": ...,
        "meta_prediction": { ... }  (sadece meta modda)
    }
    """
    if n <= 1:
        return {"success": False, "error": "n > 1 olmalı."}
    
    # Asallık kontrolü (basit)
    from primality_testing import miller_rabin_test
    mr = miller_rabin_test(n, rounds=10)
    if mr.get("is_prime") == True and mr.get("certainty") == "DEFINITE":
        return {
            "number": str(n),
            "bit_length": n.bit_length(),
            "success": False,
            "is_prime": True,
            "error": "Bu sayı asal! Çarpanlarına ayrılamaz.",
            "all_results": [],
            "total_time": 0
        }
    
    # ── META MOD: ML ile en iyi algoritmayı tahmin et ──
    actual_mode = mode
    meta_prediction = None
    
    if mode in ("meta", "auto"):
        try:
            from meta_learner import predict_best_factor_algorithm, is_model_trained
            model_status = is_model_trained()
            
            if model_status.get("factor_model"):
                meta_prediction = predict_best_factor_algorithm(n)
                
                if mode == "meta" or (mode == "auto" and meta_prediction.get("confidence", 0) > 0.4):
                    actual_mode = "meta"
                    
                    # Tahmin edilen algoritmayı çalıştır
                    algo_map = {
                        'trial_division': ("Trial Division (Meta)", lambda: trial_division_factor(n)),
                        'pollard_rho': ("Pollard's Rho (Meta)", lambda: pollard_rho_factor(n)),
                        'pollard_p_minus_1': ("Pollard's p-1 (Meta)", lambda: pollard_p_minus_1(n)),
                        'williams_p_plus_1': ("Williams' p+1 (Meta)", lambda: williams_p_plus_1(n)),
                        'lenstra_ecm': ("Lenstra ECM (Meta)", lambda: lenstra_ecm(n, curves=100, B1=10000)),
                        'fermat': ("Fermat (Meta)", lambda: fermat_factor(n)),
                    }
                    
                    predicted = meta_prediction.get("predicted_algorithm", "pollard_rho")
                    algo_display, algo_func = algo_map.get(predicted, algo_map['pollard_rho'])
                    
                    total_start = time.time()
                    t0 = time.time()
                    try:
                        result = algo_func()
                        elapsed = round(time.time() - t0, 6)
                    except Exception as e:
                        result = {"success": False, "error": str(e)}
                        elapsed = round(time.time() - t0, 6)
                    
                    meta_result = {
                        "number": str(n),
                        "digit_count": len(str(n)),
                        "bit_length": n.bit_length(),
                        "mode": "meta",
                        "meta_prediction": meta_prediction,
                        "all_results": [{
                            "algorithm": algo_display,
                            "success": result.get("success", False),
                            "time": elapsed,
                            "result": result
                        }],
                        "total_time": round(time.time() - total_start, 6)
                    }
                    
                    if result.get("success"):
                        meta_result["success"] = True
                        meta_result["best_result"] = {
                            "algorithm": algo_display,
                            "p": result["p"],
                            "q": result["q"],
                            "time": elapsed,
                            "detail": result.get("detail", "")
                        }
                        meta_result["verification"] = {
                            "p_x_q_equals_n": result["p"] * result["q"] == n,
                            "p": result["p"],
                            "q": result["q"]
                        }
                    else:
                        # Meta başarısız oldu → fallback race moduna geç
                        actual_mode = "race"
                        # Aşağıdaki race moduna düş
                    
                    if actual_mode == "meta":
                        return meta_result
            else:
                actual_mode = "race"
        except ImportError:
            actual_mode = "race"
    
    # ── RACE MOD: Tüm algoritmaları çalıştır ──
    results = {
        "number": str(n),
        "digit_count": len(str(n)),
        "bit_length": n.bit_length(),
        "mode": "race",
        "all_results": [],
        "total_time": 0
    }
    
    if meta_prediction:
        results["meta_prediction"] = meta_prediction
    
    total_start = time.time()
    best_result = None
    best_time = float('inf')
    
    # ── Algoritma Sıralaması (akıllı seçim) ──
    algorithms = []
    bit_len = n.bit_length()
    
    # 1. Trial Division her zaman ilk (küçük çarpanlar için çok hızlı)
    algorithms.append(("Trial Division", lambda: trial_division_factor(n)))
    
    # 2. Sayı boyutuna göre strateji
    if bit_len <= 64:
        # Küçük sayılar → Pollard's Rho yeterli
        algorithms.append(("Pollard's Rho (Python)", lambda: pollard_rho_factor(n)))
        algorithms.append(("Fermat Faktorizasyon", lambda: fermat_factor(n)))
    elif bit_len <= 128:
        # Orta boyut → tüm algoritmalar
        algorithms.append(("Pollard's Rho (Python)", lambda: pollard_rho_factor(n)))
        algorithms.append(("Pollard's p-1", lambda: pollard_p_minus_1(n)))
        algorithms.append(("Williams' p+1", lambda: williams_p_plus_1(n)))
        algorithms.append(("Fermat Faktorizasyon", lambda: fermat_factor(n, max_iterations=500000)))
        algorithms.append(("Lenstra ECM", lambda: lenstra_ecm(n, curves=50, B1=5000)))
    else:
        # Büyük sayılar → ECM ve Rho öncelikli
        algorithms.append(("Pollard's Rho (Python)", lambda: pollard_rho_factor(n, max_iterations=2_000_000)))
        algorithms.append(("Lenstra ECM", lambda: lenstra_ecm(n, curves=200, B1=50000)))
        algorithms.append(("Pollard's p-1", lambda: pollard_p_minus_1(n, B1=500000)))
        algorithms.append(("Williams' p+1", lambda: williams_p_plus_1(n, B=500000)))
    
    # 3. C++ motoru varsa onu da ekle
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base_dir, 'engine', 'factor.exe')
    if os.path.exists(exe_path):
        algorithms.append(("C++ Pollard's Rho", lambda: cpp_engine_factor(n, 1)))
        algorithms.append(("C++ Fermat", lambda: cpp_engine_factor(n, 3)))
    
    # ── Tüm algoritmaları çalıştır ──
    for algo_name, algo_func in algorithms:
        t0 = time.time()
        try:
            result = algo_func()
            elapsed = round(time.time() - t0, 6)
            
            entry = {
                "algorithm": algo_name,
                "success": result.get("success", False),
                "time": elapsed,
                "result": result
            }
            results["all_results"].append(entry)
            
            # Başarılı ve şimdiye kadarki en hızlıysa → en iyi sonuç
            if result.get("success") and elapsed < best_time:
                best_result = result
                best_time = elapsed
                best_result["_algorithm_name"] = algo_name
                best_result["_time"] = elapsed
                
        except Exception as e:
            results["all_results"].append({
                "algorithm": algo_name,
                "success": False,
                "time": round(time.time() - t0, 6),
                "result": {"error": str(e)}
            })
    
    results["total_time"] = round(time.time() - total_start, 6)
    
    if best_result:
        results["success"] = True
        results["best_result"] = {
            "algorithm": best_result.get("_algorithm_name", best_result.get("algorithm", "?")),
            "p": best_result["p"],
            "q": best_result["q"],
            "time": best_result.get("_time", 0),
            "detail": best_result.get("detail", "")
        }
        
        # Doğrulama
        p, q = best_result["p"], best_result["q"]
        results["verification"] = {
            "p_x_q_equals_n": p * q == n,
            "p": p,
            "q": q
        }
    else:
        results["success"] = False
        results["error"] = "Hiçbir algoritma çarpan bulamadı. Sayı asal olabilir veya çarpanları çok büyük."
    
    return results


# ══════════════════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_numbers = [
        15,           # 3 × 5
        10403,        # 101 × 103
        1000003 * 1000033,  # İki büyük asal
        561,          # 3 × 11 × 17 (Carmichael)
        2**67 - 1,    # Mersenne bileşik
    ]
    
    for n in test_numbers:
        print(f"\n{'='*60}")
        print(f"Hedef: {n} ({n.bit_length()} bit)")
        result = smart_factorize(n)
        
        if result["success"]:
            br = result["best_result"]
            print(f"  En İyi: {br['algorithm']} → p={br['p']}, q={br['q']} ({br['time']}s)")
        else:
            print(f"  Başarısız: {result.get('error', '?')}")
        
        print(f"  Toplam süre: {result['total_time']}s")
        print(f"  Denenen: {len(result['all_results'])} algoritma")
