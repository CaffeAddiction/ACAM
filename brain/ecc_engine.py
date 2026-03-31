# brain/ecc_engine.py

class ECPoint:
    """Eliptik eğri üzerindeki bir noktayı temsil eder."""
    def __init__(self, x, y, curve):
        self.x = x
        self.y = y
        self.curve = curve

    def is_infinity(self):
        return self.x is None and self.y is None

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        if self.is_infinity(): return "Infinity"
        return f"({self.x}, {self.y})"

class EllipticCurve:
    """y^2 = x^3 + ax + b (mod p) eğrisini tanımlar."""
    def __init__(self, a, b, p):
        self.a = a
        self.b = b
        self.p = p
        self.infinity = ECPoint(None, None, self)

    def point_add(self, P, Q):
        if P.is_infinity(): return Q
        if Q.is_infinity(): return P
        if P.x == Q.x and (P.y != Q.y or P.y == 0):
            return self.infinity

        # Eğim (m) hesaplama
        if P == Q:
            m = (3 * P.x**2 + self.a) * pow(2 * P.y, -1, self.p)
        else:
            m = (Q.y - P.y) * pow(Q.x - P.x, -1, self.p)
        
        m %= self.p
        x_r = (m**2 - P.x - Q.x) % self.p
        y_r = (m * (P.x - x_r) - P.y) % self.p
        
        return ECPoint(x_r, y_r, self)

    def scalar_mul(self, P, k):
        """Double-and-Add algoritması ile hızlı skaler çarpma."""
        res = self.infinity
        temp = P
        while k > 0:
            if k & 1:
                res = self.point_add(res, temp)
            temp = self.point_add(temp, temp)
            k >>= 1
        return res
    
def crack_ecdlp_bsgs(curve, P, Q, limit):
    """
    Baby-step Giant-step algoritması ile k değerini bulur.
    Q = kP mod p
    """
    import math
    m = math.ceil(math.sqrt(limit))
    
    # 1. Baby Steps: {jP : 0 <= j < m} tablosunu oluştur
    baby_steps = {}
    curr = curve.infinity
    for j in range(m):
        baby_steps[str(curr)] = j
        curr = curve.point_add(curr, P)
        
    # 2. Giant Steps: Q - i(mP) hesapla ve tabloda ara
    mP = curve.scalar_mul(P, m)
    # i(mP) değerini çıkarmak için negatifini ekliyoruz (y koordinatı mod p'de tersi)
    minus_mP = ECPoint(mP.x, (-mP.y) % curve.p, curve)
    
    giant_step = Q
    for i in range(m):
        if str(giant_step) in baby_steps:
            j = baby_steps[str(giant_step)]
            return i * m + j
        giant_step = curve.point_add(giant_step, minus_mP)
        
    return None