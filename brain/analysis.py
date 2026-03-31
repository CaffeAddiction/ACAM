import math

def extract_features(n):
    bit_len = n.bit_length()
    root = math.isqrt(n)
    # Fermat için kritik özellik: Bir sonraki tam kareye uzaklık
    diff = (root + 1)**2 - n
    
    return {
        'bit_length': bit_len,
        'dist_to_square': float(diff)
    }