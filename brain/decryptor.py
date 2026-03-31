# brain/decryptor.py

from math import isqrt


def wiener_attack(n, e):
    """
    Wiener's Attack: Sürekli Kesirler (Continued Fractions) ile
    küçük gizli anahtar d'yi bulan RSA saldırısı.
    d < (1/3) * n^(1/4) olduğunda çalışır.
    """
    def continued_fractions(num, den):
        """Sürekli kesir açılımını hesaplar."""
        cf = []
        while den:
            q = num // den
            cf.append(q)
            num, den = den, num - q * den
        return cf

    def convergents(cf):
        """Sürekli kesirin yakınsak değerlerini (h/k) üretir."""
        h_prev, h_curr = 0, 1
        k_prev, k_curr = 1, 0
        for a in cf:
            h_prev, h_curr = h_curr, a * h_curr + h_prev
            k_prev, k_curr = k_curr, a * k_curr + k_prev
            yield h_curr, k_curr

    cf = continued_fractions(e, n)

    for k, d in convergents(cf):
        if k == 0:
            continue

        # phi = (e*d - 1) / k tam bölünmeli
        if (e * d - 1) % k != 0:
            continue

        phi = (e * d - 1) // k

        # phi'den p ve q'yu bul: x^2 - (n - phi + 1)*x + n = 0
        s = n - phi + 1  # s = p + q
        discriminant = s * s - 4 * n

        if discriminant < 0:
            continue

        sqrt_disc = isqrt(discriminant)
        if sqrt_disc * sqrt_disc != discriminant:
            continue

        p = (s + sqrt_disc) // 2
        q = (s - sqrt_disc) // 2

        if p * q == n:
            return {"p": p, "q": q, "d": d, "success": True}

    return {"success": False}


def crack_rsa(p, q, ciphertext, e=65537):
    """
    Bulunan p ve q asal çarpanları ile RSA şifreli metni (ciphertext) kırar.
    e: Açık anahtar üssü (Genelde 65537 kullanılır).
    """
    n = p * q
    
    # 1. Euler Totient Fonksiyonu
    phi = (p - 1) * (q - 1)
    
    # 2. Gizli Anahtarı (d) Hesapla
    try:
        # pow(e, -1, phi) Python 3.8+ ile modüler ters almanın en hızlı yoludur
        d = pow(e, -1, phi)
    except ValueError:
        return {"error": "e ve phi aralarında asal değil. d hesaplanamadı."}
    
    # 3. Şifreyi Çöz (Matematiksel olarak: M = C^d mod n)
    plaintext_int = pow(ciphertext, d, n)
    
    # 4. Sayısal veriyi UTF-8 (Okunabilir) metne çevirmeye çalış
    try:
        byte_len = (plaintext_int.bit_length() + 7) // 8
        plaintext_bytes = plaintext_int.to_bytes(byte_len, byteorder='big')
        decoded_text = plaintext_bytes.decode('utf-8')
        
        return {"d": d, "numeric": plaintext_int, "text": decoded_text}
    except Exception:
        # Eğer metin değil de sadece sayısal bir şifre ise text None döner
        return {"d": d, "numeric": plaintext_int, "text": None}
        
# Hızlı Test
if __name__ == "__main__":
    # Örnek: 'ACAM' kelimesinin şifrelenmiş hali
    test_p = 13
    test_q = 79
    test_n = test_p * test_q # 1027
    test_e = 17 
    # Normalde bu değerler çok daha büyüktür.
    
    print("Şifre Çözücü Modül Test Ediliyor...")
