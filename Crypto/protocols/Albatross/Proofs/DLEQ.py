from sympy.polys.galoistools import * 
from .hash import Hash
import random 

class DLEQ:
    def __init__(self):
        self.__a = []
        self.__e = 0 
        self.__z = 0 


    def probar(self, q: int, p: int, g: int, x: int, alpha: int):
        m = len(g) 
        if(len(x) != m): 
            self.__a = self.__a[:0]
            print("Tamaños de g y x incorrectos.")

        else: 
            w = random.randint(0, q-1)

            for i in range(m):
                self.__a.append(pow(g[i], w, p))
    
            hash = Hash()
            self.__e = hash.hash_ZZp(q, x, self.__a, g)
      
            tmp = (alpha * self.__e) % q 
            self.__z = (w - tmp) % q
            if self.__z < 0:
                self.__z += q

            
            
            
            
           
    def verificar(self, q: int, p: int, g: list[int], x: list[int]):
        m = len(self.__a)
        if(len(x) != m or len(g) != m): 
            print("Verificacion fallida longitud incorrecta.")
            return False
        
        hash = Hash().hash_ZZp(q, x, self.__a, g)
        if (self.__e != hash):
            print("Verificacion fallida digest incorrecto.")
            return False
        
        tmp1, tmp2, tmp3 = 0, 0, 0 
        for i in range(m):
            tmp2 = pow(g[i], self.__z, p)
            tmp3 = pow(x[i], self.__e, p)
            
            tmp1 = (tmp2 * tmp3) % p
            if (self.__a[i] != tmp1):
                print("Verificacion fallida a_i incorrecto.",i)
                

                return False
        return True   
        

           
            
