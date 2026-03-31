# brain/hill_cipher.py
import numpy as np
from classical_ciphers import fitness_score

def matrix_mod_inverse(matrix, modulus):
    """Matrisin mod n'deki tersini hesaplar."""
    det = int(np.round(np.linalg.det(matrix)))
    det_inv = pow(det, -1, modulus) # Modüler çarpımsal ters
    
    # Adjoint matris hesaplama
    adj = np.round(det * np.linalg.inv(matrix)).astype(int)
    return (det_inv * adj) % modulus

def hill_encrypt(text, key_matrix):
    n = key_matrix.shape[0]
    text = "".join(filter(str.isalpha, text.upper()))
    # Padding: Metin n'in katı değilse 'X' ekle
    while len(text) % n != 0:
        text += 'X'
        
    res = ""
    for i in range(0, len(text), n):
        block = [ord(c) - 65 for c in text[i:i+n]]
        # C = P * K mod 26
        cipher_block = np.dot(block, key_matrix) % 26
        res += "".join(chr(int(c) + 65) for c in cipher_block)
    return res

def hill_decrypt(ciphertext, key_matrix):
    try:
        inv_key = matrix_mod_inverse(key_matrix, 26)
        n = key_matrix.shape[0]
        res = ""
        for i in range(0, len(ciphertext), n):
            block = [ord(c) - 65 for c in ciphertext[i:i+n]]
            plain_block = np.dot(block, inv_key) % 26
            res += "".join(chr(int(c) + 65) for c in plain_block)
        return res
    except ValueError:
        return "HATA: Anahtar matrisinin tersi mod 26'da yok!"

def crack_hill_2x2(ciphertext):
    """
    2x2 matris için Quadgram skorlamalı akıllı kaba kuvvet.
    4 karakterli anahtar uzayını (26^4) tarar.
    """
    best_score = -1e10
    best_text = ""
    best_matrix = None
    
    # Sadece tersi olan matrisleri denemek için determinant kontrolü
    for a in range(26):
        for b in range(26):
            for c in range(26):
                for d in range(26):
                    det = (a*d - b*c) % 26
                    if det % 2 == 0 or det % 13 == 0 or det == 0:
                        continue
                    
                    K = np.array([[a, b], [c, d]])
                    decrypted = hill_decrypt(ciphertext, K)
                    score = fitness_score(decrypted)
                    
                    if score > best_score:
                        best_score = score
                        best_text = decrypted
                        best_matrix = K
    
    return {"text": best_text, "matrix": best_matrix, "score": best_score}


def crack_hill_known_plaintext(plain_sample, cipher_sample, n=3):
    """
    Known-Plaintext Attack: P * K = C => K = P^-1 * C (mod 26)
    plain_sample: Bilinen orijinal metin (n*n uzunluğunda olmalı)
    cipher_sample: Bilinen metne karşılık gelen şifreli metin
    """
    try:
        # Karakterleri rakamlara çevir (0-25)
        P_list = [ord(c.upper()) - 65 for c in plain_sample]
        C_list = [ord(c.upper()) - 65 for c in cipher_sample]
        
        # Matrisleri oluştur (n x n)
        P_matrix = np.array(P_list).reshape(n, n)
        C_matrix = np.array(C_list).reshape(n, n)
        
        # P matrisinin mod 26'da tersini al
        P_inv = matrix_mod_inverse(P_matrix, 26)
        
        # K = P_inv * C mod 26
        K = np.dot(P_inv, C_matrix) % 26
        return {"success": True, "matrix": K.astype(int)}
    except ValueError as e:
        return {"success": False, "error": f"Matris tersi alınamadı: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}