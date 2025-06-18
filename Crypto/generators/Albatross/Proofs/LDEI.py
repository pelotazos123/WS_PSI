from sympy.polys.domains import ZZ 
from sympy.polys.galoistools import * 
from .hash import Hash
import random
 

class LDEI:
    def __init__(self):
        self.__a = []
        self.__e = 0 
        self.__z = []
    

    def probar(self, q: int, p: int, g: list[int], alpha: list[int], k: int, x: list[int], P: list[int]):
        m = len(g) 
        if(len(alpha) != m or len(x) != m or k > m): 
            self.__a = self.__a[:0]

        else: 
            R  = [ random.randint(0, q-1) for i in range(0, k+1) ]
            R_eval = gf_multi_eval(R, alpha, q, ZZ) 
            for i in range(m):
                self.__a.append(pow(g[i], R_eval[i], p))
            

            hash = Hash()
            self.__e = hash.hash_ZZp(q, x, self.__a, None)

             
            tmp = [(self.__e * coef) % q for coef in P]
            self.__z = [(x + y)%q for x, y in zip(tmp, R)]
            
            
            
           
    def verificar(self, q: int, p: int, g: list[int], alpha: list[int], k: int, x: list[int]):
        
        m = len(self.__a) 

        if(len(alpha) != m or len(x) != m or len(g) != m): 
            print("Verificacion fallida longitud incorrecta.")
            return False
        
        if(gf_degree(self.__z) > k):
            print("Verificacion fallida grado de z incorrecto.") 
            return False
        
        hash = Hash().hash_ZZp(q, x, self.__a)
        if (self.__e != hash):
            print("Verificacion fallida digest incorrecto.")
            return False

        zi = gf_multi_eval(self.__z, alpha, q, ZZ)

        tmp1, tmp2, tmp3 = 0, 0, 0
        
        for i in range(m):
            tmp2 = (pow(g[i], int(zi[i]), p))
            tmp3 = (pow(x[i], int(self.__e), p))
            tmp1 = gf_mul([tmp3], [self.__a[i]], p, ZZ)[0]
            if (tmp2 != tmp1):
                print("Verificacion fallida a_i incorrecto.")
                return False
        return True

    def localldei(q: int, p: int, alpha: list, k: int, x: list ,m: int): 
        u = []
        for i in range(m):
            prod = 1
            for l in range(m):
                if(l != i):
                    tmp = (alpha[i]-alpha[l]) % q
                    prod = (prod * tmp) % q
            u.append(pow(prod, -1, q))

        P  = [random.randint(0, q) for i in range(0, m - k - 1)]
        
        v = []
        for i in range(m):
            tmp = gf_multi_eval(P, [alpha[i]], q, ZZ)[0]
            v.append(((u[i] * tmp) % q))

        prod = 1
        for i in range(m):
            tmp = pow(x[i], v[i], p)
            prod = (prod * tmp) % p

        return prod == 1
        
        
