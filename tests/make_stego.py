from PIL import Image

def hide_text_in_image(text, input_image_path, output_image_path):
    img = Image.open(input_image_path).convert('RGB')
    pixels = list(img.getdata())
    
    # Metni binary'e çevir
    binary_msg = ''.join(format(ord(c), '08b') for c in text) + '00000000'
    
    new_pixels = []
    bit_idx = 0
    for pixel in pixels:
        new_pixel = list(pixel)
        for i in range(3):
            if bit_idx < len(binary_msg):
                new_pixel[i] = (new_pixel[i] & ~1) | int(binary_msg[bit_idx])
                bit_idx += 1
        new_pixels.append(tuple(new_pixel))
        
    img.putdata(new_pixels)
    img.save(output_image_path)
    print(f"Veri '{output_image_path}' içine gizlendi!")

# "ACAM SIZMA TESTI" cümlesinin Caesar (Shift 3) ile şifrelenmiş halini gömüyoruz:
gizli_sifre = "DFDP LV ZDWFKLQJ BRX" 
hide_text_in_image(gizli_sifre, "orijinal_resim.png", "sifreli_resim.png")