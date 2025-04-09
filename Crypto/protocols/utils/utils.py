from sympy import isprime

class Utils:
    @staticmethod
    def findprime(k: int, l: int):
        """Finds two prime numbers q and p based on the input parameters k and l."""
        n = 2 ** k
        s = (k % 2) - (l % 2)
        tmp = 2 ** l 
        q = (tmp + s) * n + 1
        p = 2 * q + 1
        limite = 10 ** 8
        
        for _ in range(limite):
            if (isprime(q) and isprime(p)):
                return q, p
            q += 3 * n
            p += 6 * n

        print("Primes not found.")
        return None, None

    @staticmethod
    def generator(q: int): 
        """Generates a number that is a quadratic non-residue modulo q."""
        for i in range(2, 2 * q + 1):
            po = pow(i, 2, q)
            if po == 1:
                continue
            po = pow(i, q, q)
            if po == 1:
                continue
            return i 
        return None

    @staticmethod
    def rootunity(n, q):
        """Finds the n-th root of unity modulo q."""
        i = 2  
        t = (q - 1) // n
        while True:
            w = pow(int(i), int(t), int(q))
            tmp = pow(int(w), int(n // 2), int(q))
            if tmp != 1:
                return w
            i += 1

    @staticmethod
    def ffte(self, n, L, w, q, p):
        """Performs a Fast Fourier Transform (FFT) with finite field elements."""
        if n == 1:
            return L
        
        m = n // 2
        hj = L[:m]
        hjm = L[m:]
        
        u = [0] * m
        v = [0] * m
        
        for j in range(m):
            u[j] = hj[j] * hjm[j]

            invhjm = pow(hjm[j], -1, p)         
            wj = pow(w, j, q)                   
            tmp = ((hj[j] * invhjm) % p)        
            v[j] = pow(tmp, wj, p)              

        w2 = pow(w, 2, q)       

        u2 = self.ffte(m, u, w2, q, p)
        v2 = self.ffte(m, v, w2, q, p)
        
        h_hat = u2 + v2

        return h_hat
