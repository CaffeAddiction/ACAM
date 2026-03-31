# brain/stego_analyzer.py
from PIL import Image

def extract_lsb_watermark(image_path):
    """
    Resmin piksellerindeki En Önemsiz Bitleri (LSB) toplayarak gizli mesajı çıkarır.
    """
    try:
        img = Image.open(image_path)
        img = img.convert('RGB')
        pixels = img.getdata()

        binary_data = ""
        for pixel in pixels:
            for value in pixel:
                # Renk değerinin (0-255) son bitini al (bin: ...0 veya ...1)
                binary_data += str(value & 1)

        # 8 bitlik gruplara ayır ve karakterlere çevir
        all_bytes = [binary_data[i:i+8] for i in range(0, len(binary_data), 8)]
        
        decoded_data = ""
        for byte in all_bytes:
            char_code = int(byte, 2)
            # Okunabilir karakter sınırında mı? (Basit bir temizlik)
            if 32 <= char_code <= 126:
                decoded_data += chr(char_code)
            elif char_code == 0: # Null terminator (mesajın sonu olabilir)
                break
        
        # Eğer çok fazla anlamsız veri varsa veya boşsa
        if len(decoded_data) < 3:
            return {"success": False, "error": "Gizli veri bulunamadı veya çok bozuk."}

        return {"success": True, "data": decoded_data}
    except Exception as e:
        return {"success": False, "error": str(e)}