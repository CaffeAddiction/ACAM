from Crypto.Cipher import DES
from Crypto.Util.Padding import unpad

def crack_des_dictionary(ciphertext_hex):
    """DES şifresini en yaygın anahtarlarla kırmaya çalışır (Dictionary Attack)"""
    try:
        ciphertext = bytes.fromhex(ciphertext_hex)
    except ValueError:
        return {"success": False, "error": "Lütfen geçerli bir Hexadecimal veri girin."}

    # DES kesinlikle 8 bayt (64 bit) anahtar gerektirir (56 bit aktif, 8 bit parity)
    common_keys = [
        b"admin123", b"password", b"12345678", b"ACAMKEY1",
        b"secretky", b"rootroot", b"deskey8b", b"qwertyui"
    ]

    for key in common_keys:
        try:
            # 1. Senaryo: ECB Modu (Block zincirlemesi yok)
            cipher = DES.new(key, DES.MODE_ECB)
            decrypted = cipher.decrypt(ciphertext)
            unpadded = unpad(decrypted, DES.block_size)
            text = unpadded.decode('utf-8')

            if text.isprintable():
                return {"success": True, "key": key.decode('utf-8'), "plaintext": text, "mode": "ECB"}
        except Exception:
            pass

        try:
            # 2. Senaryo: CBC Modu (İlk 8 bayt IV olarak kabul edilir)
            if len(ciphertext) > 8:
                iv = ciphertext[:8]
                actual_cipher = ciphertext[8:]
                cipher = DES.new(key, DES.MODE_CBC, iv)
                decrypted = cipher.decrypt(actual_cipher)
                unpadded = unpad(decrypted, DES.block_size)
                text = unpadded.decode('utf-8')

                if text.isprintable():
                    return {"success": True, "key": key.decode('utf-8'), "plaintext": text, "mode": "CBC"}
        except Exception:
            pass

    return {"success": False, "error": "Kötü amaçlı yazılım analizi: Sözlükteki anahtarlarla eşleşme bulunamadı."}