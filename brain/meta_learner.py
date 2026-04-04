# brain/meta_learner.py
# ══════════════════════════════════════════════════════════════════════════
# ACAM Meta-Öğrenme Motoru
# ══════════════════════════════════════════════════════════════════════════
# Sayının matematiksel özelliklerini çıkararak, en verimli algoritmayı
# Random Forest ile tahmin eder. Benchmark verisiyle eğitilir.
#
# İçerik:
#   1. Zengin Özellik Çıkarma (Feature Engineering)
#   2. Benchmark Veri Üretimi (Sentetik Eğitim Verisi)
#   3. Model Eğitimi (Random Forest)
#   4. Tahmin (Prediction)
# ══════════════════════════════════════════════════════════════════════════

import math
import random
import time
import os
import json

# Küçük asal sayılar
SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
                53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107,
                109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167,
                173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229,
                233, 239, 241, 251]


# ══════════════════════════════════════════════════════════════════════════
# 1. ZENGİN ÖZELLİK ÇIKARMA (Feature Engineering)
# ══════════════════════════════════════════════════════════════════════════

def extract_rich_features(n):
    """
    Sayıdan 15+ matematiksel özellik çıkarır.
    Bu özellikler, hangi algoritmanın en hızlı çalışacağını tahmin etmek için kullanılır.
    """
    n = int(n)
    features = {}
    
    # ── Temel Özellikler ──
    features['bit_length'] = n.bit_length()
    features['digit_count'] = len(str(n))
    features['is_even'] = 1 if n % 2 == 0 else 0
    features['last_digit'] = n % 10
    
    # ── Tam Kare Uzaklığı (Fermat için kritik) ──
    root = math.isqrt(n)
    features['dist_to_square'] = float((root + 1)**2 - n)
    features['dist_to_square_ratio'] = features['dist_to_square'] / max(n, 1)
    features['is_perfect_square'] = 1 if root * root == n else 0
    
    # ── Tam Kuvvet Kontrolü ──
    features['is_perfect_power'] = 0
    for exp in [2, 3, 5, 7]:
        r = round(n ** (1.0 / exp))
        for candidate in [r - 1, r, r + 1]:
            if candidate > 1 and candidate ** exp == n:
                features['is_perfect_power'] = 1
                break
    
    # ── Smoothness Skoru: n-1 (Pollard p-1 için kritik) ──
    # n-1'in küçük asallarla ne kadar bölünebildiğini ölç
    n_minus_1 = n - 1
    smooth_score = 0
    temp = n_minus_1
    for p in SMALL_PRIMES[:30]:
        while temp > 1 and temp % p == 0:
            temp //= p
            smooth_score += 1
    # Oran olarak: tam smooth ise 1.0, hiç bölünemediyse 0.0
    total_bits = max(n_minus_1.bit_length(), 1)
    remaining_bits = max(temp.bit_length(), 0) if temp > 1 else 0
    features['n_minus_1_smoothness'] = round(1.0 - (remaining_bits / total_bits), 4)
    features['n_minus_1_small_factors'] = smooth_score
    
    # ── Smoothness Skoru: n+1 (Williams p+1 için kritik) ──
    n_plus_1 = n + 1
    smooth_score_p1 = 0
    temp_p1 = n_plus_1
    for p in SMALL_PRIMES[:30]:
        while temp_p1 > 1 and temp_p1 % p == 0:
            temp_p1 //= p
            smooth_score_p1 += 1
    remaining_bits_p1 = max(temp_p1.bit_length(), 0) if temp_p1 > 1 else 0
    features['n_plus_1_smoothness'] = round(1.0 - (remaining_bits_p1 / total_bits), 4)
    features['n_plus_1_small_factors'] = smooth_score_p1
    
    # ── Küçük Asal Bölünebilirlik (Trial Division hızlı mı?) ──
    features['has_small_factor'] = 0
    features['smallest_factor_bits'] = features['bit_length']  # default: kendisi kadar büyük
    for p in SMALL_PRIMES:
        if n % p == 0 and n != p:
            features['has_small_factor'] = 1
            features['smallest_factor_bits'] = p.bit_length()
            break
    
    # ── GCD ile Faktoriyal Testi ──
    # gcd(n, 50!) > 1 ise küçük çarpanı var demek
    factorial_val = math.factorial(50)
    g = math.gcd(n, factorial_val)
    features['gcd_factorial_50'] = 1 if g > 1 and g < n else 0
    
    # ── Fermat Residue (Carmichael tespiti) ──
    # a^(n-1) mod n == 1 olup olmadığını test et (birkaç taban ile)
    fermat_pass_count = 0
    if n > 4 and n % 2 != 0:
        for a in [2, 3, 5, 7, 11]:
            if a < n:
                try:
                    if pow(a, n - 1, n) == 1:
                        fermat_pass_count += 1
                except:
                    pass
    features['fermat_pass_ratio'] = fermat_pass_count / 5.0
    
    # ── Mod Pattern (son basamak yapısı) ──
    features['mod_3'] = n % 3
    features['mod_7'] = n % 7
    features['mod_11'] = n % 11
    features['mod_30'] = n % 30  # 2×3×5 primorial deseni
    
    return features


def get_feature_names():
    """Özellik isimlerini sıralı döndürür (model eğitimi için)."""
    return [
        'bit_length', 'digit_count', 'is_even', 'last_digit',
        'dist_to_square', 'dist_to_square_ratio', 'is_perfect_square',
        'is_perfect_power',
        'n_minus_1_smoothness', 'n_minus_1_small_factors',
        'n_plus_1_smoothness', 'n_plus_1_small_factors',
        'has_small_factor', 'smallest_factor_bits',
        'gcd_factorial_50', 'fermat_pass_ratio',
        'mod_3', 'mod_7', 'mod_11', 'mod_30'
    ]


def features_to_vector(features_dict):
    """Özellik dict'ini sıralı liste/vektöre çevirir."""
    return [features_dict.get(name, 0) for name in get_feature_names()]


# ══════════════════════════════════════════════════════════════════════════
# 2. BENCHMARK VERİ ÜRETİMİ (Sentetik Eğitim Verisi)
# ══════════════════════════════════════════════════════════════════════════

def _generate_training_numbers():
    """
    Meta-öğrenme için çeşitli sayı tipleri üretir.
    Her tip, farklı bir algoritmanın güçlü olduğu alanı temsil eder.
    """
    numbers = []
    
    # Tip 1: Küçük çarpanlı sayılar (Trial Division güçlü)
    for _ in range(40):
        small_p = random.choice(SMALL_PRIMES[:20])
        big_q = random.randint(10**4, 10**8)
        # big_q'nun tek olmasını sağla
        if big_q % 2 == 0:
            big_q += 1
        numbers.append(('trial_div', small_p * big_q))
    
    # Tip 2: Birbirine yakın çarpanlar (Fermat güçlü)
    for _ in range(40):
        bits = random.choice([16, 20, 24, 28, 32])
        base = random.getrandbits(bits)
        if base < 100:
            base = 100
        if base % 2 == 0:
            base += 1
        # p ve q yakın
        p = base
        q = base + random.randint(2, 100) * 2  # yakın ve tek
        if p > 1 and q > 1:
            numbers.append(('fermat', p * q))
    
    # Tip 3: p-1 smooth çarpanlı sayılar (Pollard p-1 güçlü)
    for _ in range(40):
        # p-1'i smooth yapacak bir asal üret
        smooth_part = 1
        for _ in range(random.randint(3, 8)):
            smooth_part *= random.choice(SMALL_PRIMES[:15])
        p = smooth_part + 1
        # p'nin gerçekten asal olup olmadığı önemli değil (bileşik de olur)
        q = random.choice(SMALL_PRIMES[20:50])
        n = p * q
        if n > 5:
            numbers.append(('p_minus_1', n))
    
    # Tip 4: Genel sayılar (Pollard Rho güçlü)
    for _ in range(60):
        bits = random.choice([20, 24, 28, 32, 36, 40, 44, 48])
        p = random.getrandbits(bits // 2)
        q = random.getrandbits(bits // 2)
        if p < 3: p = 3
        if q < 3: q = 5
        if p % 2 == 0: p += 1
        if q % 2 == 0: q += 1
        numbers.append(('rho', p * q))
    
    # Tip 5: Orta büyüklükte sayılar (ECM iyi çalışır)
    for _ in range(30):
        # Küçük p, büyük q
        p = random.getrandbits(random.choice([12, 16, 20]))
        q = random.getrandbits(random.choice([32, 40, 48]))
        if p < 3: p = 7
        if q < 3: q = 13
        if p % 2 == 0: p += 1
        if q % 2 == 0: q += 1
        numbers.append(('ecm', p * q))
    
    # Tip 6: Asal sayılar (hiçbir faktorizasyon çalışmamalı)
    known_primes = [
        104729, 1299709, 15485863, 32452843, 49979687,
        67867967, 86028121, 104395301, 122949823, 141650939,
        961748941, 982451653, 999999937
    ]
    for p in known_primes[:8]:
        numbers.append(('prime', p))
    
    # Tip 7: Carmichael sayıları (Fermat testi aldanır)
    carmichaels = [561, 1105, 1729, 2465, 2821, 6601, 8911, 10585, 15841,
                   29341, 41041, 46657, 52633, 62745, 63973, 75361]
    for c in carmichaels:
        numbers.append(('carmichael', c))
    
    return numbers


def _benchmark_factoring(n, timeout_per_algo=5.0):
    """
    Bir sayı üzerinde tüm faktorizasyon algoritmalarını benchmark eder.
    Her algoritma için süreyi ölçer ve başarı durumunu kaydeder.
    """
    from advanced_factoring import (
        trial_division_factor, pollard_rho_factor, pollard_p_minus_1,
        williams_p_plus_1, lenstra_ecm, fermat_factor
    )
    
    algorithms = {
        'trial_division': trial_division_factor,
        'pollard_rho': lambda n: pollard_rho_factor(n, max_iterations=100_000),
        'pollard_p_minus_1': lambda n: pollard_p_minus_1(n, B1=10000),
        'williams_p_plus_1': lambda n: williams_p_plus_1(n, B=10000),
        'lenstra_ecm': lambda n: lenstra_ecm(n, curves=20, B1=2000),
        'fermat': lambda n: fermat_factor(n, max_iterations=100_000),
    }
    
    results = {}
    
    for algo_name, algo_func in algorithms.items():
        t0 = time.time()
        try:
            result = algo_func(n)
            elapsed = time.time() - t0
            
            if elapsed > timeout_per_algo:
                results[algo_name] = {'success': False, 'time': timeout_per_algo}
            else:
                results[algo_name] = {
                    'success': result.get('success', False),
                    'time': round(elapsed, 6)
                }
        except Exception:
            results[algo_name] = {'success': False, 'time': timeout_per_algo}
    
    return results


def _benchmark_primality(n):
    """
    Bir sayı üzerinde tüm asallık testlerini benchmark eder.
    """
    from primality_testing import (
        trial_division_test, fermat_test, miller_rabin_test,
        solovay_strassen_test, lucas_test, baillie_psw_test
    )
    
    tests = {
        'trial_division': trial_division_test,
        'fermat': lambda n: fermat_test(n, rounds=10),
        'miller_rabin': lambda n: miller_rabin_test(n, rounds=10),
        'solovay_strassen': lambda n: solovay_strassen_test(n, rounds=10),
        'lucas': lucas_test,
        'baillie_psw': baillie_psw_test,
    }
    
    results = {}
    
    for test_name, test_func in tests.items():
        t0 = time.time()
        try:
            result = test_func(n)
            elapsed = time.time() - t0
            
            # Doğru sonuç verdi mi? (kesin veya yüksek güven)
            is_correct = result.get('certainty') in ('DEFINITE', 'ALMOST_CERTAIN')
            is_probable = result.get('certainty') == 'PROBABLE' and result.get('confidence', 0) > 0.99
            
            results[test_name] = {
                'reliable': is_correct or is_probable,
                'time': round(elapsed, 6),
                'result': result.get('is_prime')
            }
        except Exception:
            results[test_name] = {'reliable': False, 'time': 1.0, 'result': None}
    
    return results


# ══════════════════════════════════════════════════════════════════════════
# 3. MODEL EĞİTİMİ (Random Forest)
# ══════════════════════════════════════════════════════════════════════════

ALGO_NAMES_FACTOR = [
    'trial_division', 'pollard_rho', 'pollard_p_minus_1',
    'williams_p_plus_1', 'lenstra_ecm', 'fermat'
]

ALGO_NAMES_PRIME = [
    'trial_division', 'fermat', 'miller_rabin',
    'solovay_strassen', 'lucas', 'baillie_psw'
]


def train_meta_models(progress_callback=None):
    """
    Benchmark verisi toplayıp Random Forest modelleri eğitir.
    
    Returns:
        dict: Eğitim sonuçları (doğruluk, süre, vb.)
    """
    try:
        from sklearn.ensemble import RandomForestClassifier
        import joblib
    except ImportError:
        return {"error": "scikit-learn veya joblib yüklü değil. pip install scikit-learn joblib"}
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("🧠 ACAM META-ÖĞRENME: Eğitim Başlıyor")
    print("=" * 60)
    
    # ── Eğitim Verisi Üret ──
    training_numbers = _generate_training_numbers()
    total = len(training_numbers)
    
    print(f"📊 {total} eğitim sayısı üretildi.")
    
    X_factor = []  # Özellik vektörleri
    y_factor = []  # En iyi faktorizasyon algoritması indeksi
    X_prime = []
    y_prime = []
    
    benchmark_log = []
    
    for idx, (num_type, n) in enumerate(training_numbers):
        if n < 4:
            continue
        
        if progress_callback:
            progress_callback(idx + 1, total, f"Benchmarking: {n} ({num_type})")
        
        if (idx + 1) % 25 == 0:
            print(f"  ⏳ [{idx+1}/{total}] Benchmark: {n} ({num_type})")
        
        # Özellik çıkar
        try:
            features = extract_rich_features(n)
            feature_vec = features_to_vector(features)
        except Exception:
            continue
        
        # Faktorizasyon benchmark
        if num_type != 'prime':
            try:
                factor_bench = _benchmark_factoring(n, timeout_per_algo=3.0)
                
                # En hızlı başarılı algoritmayı bul
                best_algo = None
                best_time = float('inf')
                for algo_name in ALGO_NAMES_FACTOR:
                    res = factor_bench.get(algo_name, {})
                    if res.get('success') and res['time'] < best_time:
                        best_time = res['time']
                        best_algo = algo_name
                
                if best_algo is not None:
                    X_factor.append(feature_vec)
                    y_factor.append(ALGO_NAMES_FACTOR.index(best_algo))
                    benchmark_log.append({
                        'n': n, 'type': num_type, 'best_factor': best_algo,
                        'best_time': best_time
                    })
            except Exception:
                pass
        
        # Asallık benchmark
        try:
            prime_bench = _benchmark_primality(n)
            
            # En hızlı güvenilir testi bul
            best_test = None
            best_time = float('inf')
            for test_name in ALGO_NAMES_PRIME:
                res = prime_bench.get(test_name, {})
                if res.get('reliable') and res['time'] < best_time:
                    best_time = res['time']
                    best_test = test_name
            
            if best_test is not None:
                X_prime.append(feature_vec)
                y_prime.append(ALGO_NAMES_PRIME.index(best_test))
        except Exception:
            pass
    
    # ── Random Forest Eğitimi ──
    results = {
        "factor_samples": len(X_factor),
        "prime_samples": len(X_prime),
        "feature_count": len(get_feature_names()),
        "feature_names": get_feature_names()
    }
    
    # Faktorizasyon Modeli
    if len(X_factor) >= 10:
        print(f"\n🔧 Faktorizasyon modeli eğitiliyor ({len(X_factor)} örnek)...")
        clf_factor = RandomForestClassifier(
            n_estimators=100, max_depth=12, random_state=42,
            class_weight='balanced'
        )
        clf_factor.fit(X_factor, y_factor)
        
        # Eğitim doğruluğu
        train_acc = clf_factor.score(X_factor, y_factor)
        results["factor_accuracy"] = round(train_acc, 4)
        
        # Özellik önem sıralaması
        importances = clf_factor.feature_importances_
        feat_names = get_feature_names()
        importance_pairs = sorted(zip(feat_names, importances), key=lambda x: -x[1])
        results["factor_top_features"] = [
            {"feature": name, "importance": round(imp, 4)}
            for name, imp in importance_pairs[:8]
        ]
        
        # Model kaydet
        factor_model_path = os.path.join(base_dir, 'meta_model_factor.pkl')
        joblib.dump(clf_factor, factor_model_path)
        results["factor_model_path"] = factor_model_path
        print(f"  ✅ Faktorizasyon modeli kaydedildi: {factor_model_path}")
        print(f"  📊 Eğitim doğruluğu: {train_acc:.2%}")
    else:
        results["factor_error"] = "Yeterli eğitim verisi yok"
    
    # Asallık Modeli
    if len(X_prime) >= 10:
        print(f"\n🔧 Asallık modeli eğitiliyor ({len(X_prime)} örnek)...")
        clf_prime = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42,
            class_weight='balanced'
        )
        clf_prime.fit(X_prime, y_prime)
        
        train_acc = clf_prime.score(X_prime, y_prime)
        results["prime_accuracy"] = round(train_acc, 4)
        
        importances = clf_prime.feature_importances_
        importance_pairs = sorted(zip(feat_names, importances), key=lambda x: -x[1])
        results["prime_top_features"] = [
            {"feature": name, "importance": round(imp, 4)}
            for name, imp in importance_pairs[:8]
        ]
        
        prime_model_path = os.path.join(base_dir, 'meta_model_prime.pkl')
        joblib.dump(clf_prime, prime_model_path)
        results["prime_model_path"] = prime_model_path
        print(f"  ✅ Asallık modeli kaydedildi: {prime_model_path}")
        print(f"  📊 Eğitim doğruluğu: {train_acc:.2%}")
    else:
        results["prime_error"] = "Yeterli eğitim verisi yok"
    
    # Benchmark logunu kaydet
    log_path = os.path.join(base_dir, 'meta_benchmark_log.json')
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(benchmark_log[:50], f, indent=2, ensure_ascii=False, default=str)
    results["log_path"] = log_path
    
    print(f"\n{'='*60}")
    print(f"🎉 META-ÖĞRENME EĞİTİMİ TAMAMLANDI!")
    print(f"   Faktorizasyon: {results.get('factor_accuracy', 'N/A')}")
    print(f"   Asallık: {results.get('prime_accuracy', 'N/A')}")
    print(f"{'='*60}")
    
    return results


# ══════════════════════════════════════════════════════════════════════════
# 4. TAHMİN (Prediction)
# ══════════════════════════════════════════════════════════════════════════

def _load_model(model_name):
    """Model dosyasını yükler, yoksa None döner."""
    try:
        import joblib
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, model_name)
        if os.path.exists(model_path):
            return joblib.load(model_path)
    except Exception:
        pass
    return None


def predict_best_factor_algorithm(n):
    """
    ML modeli ile en verimli faktorizasyon algoritmasını tahmin eder.
    
    Returns:
        dict: {
            "predicted_algorithm": "pollard_rho",
            "confidence": 0.85,
            "all_probabilities": {...},
            "features_used": {...},
            "model_available": True
        }
    """
    model = _load_model('meta_model_factor.pkl')
    
    if model is None:
        return {
            "model_available": False,
            "predicted_algorithm": "pollard_rho",
            "confidence": 0.0,
            "reason": "Model dosyası bulunamadı. Önce eğitim yapılmalı."
        }
    
    features = extract_rich_features(n)
    feature_vec = [features_to_vector(features)]
    
    # Tahmin
    prediction = model.predict(feature_vec)[0]
    probabilities = model.predict_proba(feature_vec)[0]
    
    predicted_algo = ALGO_NAMES_FACTOR[prediction]
    confidence = float(max(probabilities))
    
    # Tüm olasılıklar
    algo_probs = {}
    for i, name in enumerate(ALGO_NAMES_FACTOR):
        if i < len(probabilities):
            algo_probs[name] = round(float(probabilities[i]), 4)
    
    # Seçim Nedeni
    reason = _explain_factor_choice(predicted_algo, features, confidence)
    
    return {
        "model_available": True,
        "predicted_algorithm": predicted_algo,
        "predicted_algorithm_display": _algo_display_name(predicted_algo),
        "confidence": round(confidence, 4),
        "all_probabilities": algo_probs,
        "features_summary": {
            "bit_length": features['bit_length'],
            "n_minus_1_smoothness": features['n_minus_1_smoothness'],
            "dist_to_square_ratio": features['dist_to_square_ratio'],
            "has_small_factor": features['has_small_factor'],
        },
        "reason": reason
    }


def predict_best_prime_test(n):
    """
    ML modeli ile en verimli asallık testini tahmin eder.
    """
    model = _load_model('meta_model_prime.pkl')
    
    if model is None:
        return {
            "model_available": False,
            "predicted_test": "baillie_psw",
            "confidence": 0.0,
            "reason": "Model dosyası bulunamadı. Önce eğitim yapılmalı."
        }
    
    features = extract_rich_features(n)
    feature_vec = [features_to_vector(features)]
    
    prediction = model.predict(feature_vec)[0]
    probabilities = model.predict_proba(feature_vec)[0]
    
    predicted_test = ALGO_NAMES_PRIME[prediction]
    confidence = float(max(probabilities))
    
    test_probs = {}
    for i, name in enumerate(ALGO_NAMES_PRIME):
        if i < len(probabilities):
            test_probs[name] = round(float(probabilities[i]), 4)
    
    reason = _explain_prime_choice(predicted_test, features, confidence)
    
    return {
        "model_available": True,
        "predicted_test": predicted_test,
        "predicted_test_display": _test_display_name(predicted_test),
        "confidence": round(confidence, 4),
        "all_probabilities": test_probs,
        "features_summary": {
            "bit_length": features['bit_length'],
            "fermat_pass_ratio": features['fermat_pass_ratio'],
            "has_small_factor": features['has_small_factor'],
        },
        "reason": reason
    }


def _algo_display_name(algo_name):
    """Algoritma iç adını kullanıcı-dostu isme çevirir."""
    names = {
        'trial_division': 'Trial Division',
        'pollard_rho': "Pollard's Rho",
        'pollard_p_minus_1': "Pollard's p-1",
        'williams_p_plus_1': "Williams' p+1",
        'lenstra_ecm': 'Lenstra ECM',
        'fermat': 'Fermat Faktorizasyon',
    }
    return names.get(algo_name, algo_name)


def _test_display_name(test_name):
    """Test iç adını kullanıcı-dostu isme çevirir."""
    names = {
        'trial_division': 'Trial Division',
        'fermat': 'Fermat Testi',
        'miller_rabin': 'Miller-Rabin',
        'solovay_strassen': 'Solovay-Strassen',
        'lucas': 'Lucas Testi',
        'baillie_psw': 'Baillie-PSW',
    }
    return names.get(test_name, test_name)


def _explain_factor_choice(algo, features, confidence):
    """ML seçiminin nedenini açıklar."""
    reasons = []
    
    if algo == 'trial_division':
        reasons.append("Sayının küçük çarpanları olma olasılığı yüksek.")
        if features.get('has_small_factor'):
            reasons.append("gcd(n, 50!) > 1: Küçük çarpan teyidi.")
    elif algo == 'fermat':
        if features.get('dist_to_square_ratio', 1) < 0.01:
            reasons.append(f"Tam kareye çok yakın (oran: {features['dist_to_square_ratio']:.6f})")
        reasons.append("Çarpanlar birbirine yakın olabilir.")
    elif algo == 'pollard_rho':
        reasons.append("Genel amaçlı, orta boyutlu sayılar için optimal.")
    elif algo == 'pollard_p_minus_1':
        if features.get('n_minus_1_smoothness', 0) > 0.3:
            reasons.append(f"n-1 smooth skoru yüksek ({features['n_minus_1_smoothness']:.2f})")
        reasons.append("p-1 sayısının B-smooth olma olasılığı yüksek.")
    elif algo == 'williams_p_plus_1':
        if features.get('n_plus_1_smoothness', 0) > 0.3:
            reasons.append(f"n+1 smooth skoru yüksek ({features['n_plus_1_smoothness']:.2f})")
        reasons.append("p+1 sayısının B-smooth olma olasılığı yüksek.")
    elif algo == 'lenstra_ecm':
        reasons.append("Küçük çarpanları bulmada eliptik eğri metodu etkilidir.")
    
    reasons.append(f"ML güven skoru: {confidence:.1%}")
    return " | ".join(reasons)


def _explain_prime_choice(test, features, confidence):
    """ML seçiminin nedenini açıklar."""
    reasons = []
    
    if test == 'trial_division':
        reasons.append("Küçük sayı — Trial Division kesin sonuç verir.")
    elif test == 'baillie_psw':
        reasons.append("En güvenilir hibrit test (MR + Lucas). Bilinen 0 false positive.")
    elif test == 'miller_rabin':
        reasons.append("Deterministik tanıklarla hızlı ve güvenilir.")
    elif test == 'fermat':
        reasons.append("Hızlı ama Carmichael sayılarına karşı savunmasız.")
        if features.get('fermat_pass_ratio', 0) == 1.0:
            reasons.append("⚠️ Tüm Fermat tanıkları geçti — Carmichael olabilir!")
    elif test == 'lucas':
        reasons.append("MR'dan bağımsız ikinci görüş sağlar.")
    elif test == 'solovay_strassen':
        reasons.append("Jacobi sembolü ile Euler kriteri kontrolü.")
    
    reasons.append(f"ML güven skoru: {confidence:.1%}")
    return " | ".join(reasons)


def is_model_trained():
    """Model dosyalarının varlığını kontrol eder."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    factor_exists = os.path.exists(os.path.join(base_dir, 'meta_model_factor.pkl'))
    prime_exists = os.path.exists(os.path.join(base_dir, 'meta_model_prime.pkl'))
    return {
        "factor_model": factor_exists,
        "prime_model": prime_exists,
        "both_ready": factor_exists and prime_exists
    }


# ══════════════════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Meta-Öğrenme Modülü Test")
    print("=" * 50)
    
    # Özellik çıkarma testi
    test_nums = [10403, 561, 15485863, 2**67 - 1]
    for n in test_nums:
        feats = extract_rich_features(n)
        print(f"\n{n}:")
        for k, v in feats.items():
            print(f"  {k}: {v}")
    
    # Model durumu
    status = is_model_trained()
    print(f"\nModel durumu: {status}")
    
    # Eğitim isteniyor mu?
    inp = input("\nEğitim başlatılsın mı? (e/h): ")
    if inp.lower() == 'e':
        results = train_meta_models()
        print(json.dumps(results, indent=2, default=str))
        
        # Tahmin testi
        print("\n--- TAHMİN TESTLERİ ---")
        for n in test_nums:
            print(f"\n{n}:")
            fp = predict_best_factor_algorithm(n)
            print(f"  Faktorizasyon: {fp['predicted_algorithm_display']} (güven: {fp['confidence']:.1%})")
            print(f"  Neden: {fp['reason']}")
            
            pp = predict_best_prime_test(n)
            print(f"  Asallık: {pp['predicted_test_display']} (güven: {pp['confidence']:.1%})")
            print(f"  Neden: {pp['reason']}")
