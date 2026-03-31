# brain/aes_oracle.py
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import os

class VulnerableServer:
    """
    Kurban Sunucu Simülasyonu.
    Kendi içinde gizli bir anahtarı vardır ve sadece dışarıdan gelen metnin
    'Padding' (Dolgu) yapısının doğru olup olmadığını (True/False) söyler.
    """
    def __init__(self):
        self.key = os.urandom(16) # 128-bit Rastgele Gizli Anahtar
        self.block_size = AES.block_size

    def encrypt(self, plaintext):
        """Metni şifreler ve IV + Ciphertext olarak döndürür."""
        iv = os.urandom(self.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        padded_data = pad(plaintext.encode('utf-8'), self.block_size)
        ciphertext = cipher.encrypt(padded_data)
        return iv + ciphertext

    def oracle(self, ciphertext):
        """
        KAHİN (ORACLE) FONKSİYONU:
        Sadece padding hatası verip vermediğini söyler. Gizli anahtarı sızdırmaz.
        """
        iv = ciphertext[:self.block_size]
        actual_ciphertext = ciphertext[self.block_size:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        try:
            decrypted = cipher.decrypt(actual_ciphertext)
            unpad(decrypted, self.block_size)
            return True  # 200 OK (Padding Doğru)
        except ValueError:
            return False # 500 Error (Padding Hatası)

def crack_padding_oracle(ciphertext, oracle_func):
    block_size = 16
    blocks = [ciphertext[i:i+block_size] for i in range(0, len(ciphertext), block_size)]
    decrypted_message = b""
    
    steps_log = [] # YAPILAN ADIMLARI KAYDEDECEĞİMİZ LİSTE

    for block_idx in range(len(blocks) - 1, 0, -1):
        target_block = blocks[block_idx]
        prev_block = blocks[block_idx - 1]
        
        intermediate_state = bytearray(block_size)
        decrypted_block = bytearray(block_size)
        
        steps_log.append(f"\n[+] --- Blok {block_idx} Analizi Başlıyor ---")

        for byte_idx in range(block_size - 1, -1, -1):
            padding_value = block_size - byte_idx
            
            fake_prev_block = bytearray(block_size)
            for k in range(byte_idx + 1, block_size):
                fake_prev_block[k] = intermediate_state[k] ^ padding_value

            for guess in range(256):
                fake_prev_block[byte_idx] = guess
                test_ciphertext = bytes(fake_prev_block) + target_block
                
                if oracle_func(test_ciphertext):
                    if byte_idx == block_size - 1 and guess == prev_block[byte_idx]:
                        fake_prev_block[byte_idx - 1] ^= 1
                        test_ciphertext_verify = bytes(fake_prev_block) + target_block
                        if not oracle_func(test_ciphertext_verify):
                            continue
                    
                    intermediate_state[byte_idx] = guess ^ padding_value
                    decrypted_block[byte_idx] = intermediate_state[byte_idx] ^ prev_block[byte_idx]
                    
                    # BAŞARILI BULUNAN BAYTI LOGLA
                    found_byte = decrypted_block[byte_idx]
                    char_repr = chr(found_byte) if 32 <= found_byte <= 126 else f"\\x{found_byte:02x}"
                    steps_log.append(f"[*] Bayt {byte_idx:02d} | Tahmin: 0x{guess:02x} -> Doğru! | Bulunan Karakter: '{char_repr}'")
                    break
        
        decrypted_message = bytes(decrypted_block) + decrypted_message

    try:
        final_text = unpad(decrypted_message, block_size).decode('utf-8')
    except ValueError:
        final_text = decrypted_message.decode('utf-8', errors='ignore')
        
    return final_text, steps_log # ARTIK İKİ VERİ DÖNDÜRÜYORUZ