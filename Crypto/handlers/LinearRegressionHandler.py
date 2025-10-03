import random

class LinearRegressionHandler:
    def __init__(self, id, devices, results):
        self.id = id
        self.devices = devices
        self.results = results

    def compute_local_sums(self, x, y):
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum([xi * yi for xi, yi in zip(x, y)])
        sum_x2 = sum([xi * xi for xi in x])

        # Enmascarar (2-privacy estilo protocolo original)
        r = [random.randint(1, 10) for _ in range(4)]
        return {
            "sum_x": sum_x + r[0], "r1": r[0],
            "sum_y": sum_y + r[1], "r2": r[1],
            "sum_xy": sum_xy + r[2], "r3": r[2],
            "sum_x2": sum_x2 + r[3], "r4": r[3],
            "n": n
        }

    def aggregate(self, shares):
        """shares = lista de diccionarios con sumas enmascaradas"""
        total_x = total_y = total_xy = total_x2 = n_total = 0
        for s in shares:
            total_x += s["sum_x"] - s["r1"]
            total_y += s["sum_y"] - s["r2"]
            total_xy += s["sum_xy"] - s["r3"]
            total_x2 += s["sum_x2"] - s["r4"]
            n_total += s["n"]

        beta1 = (n_total * total_xy - total_x * total_y) / (n_total * total_x2 - total_x**2)
        beta0 = (total_y - beta1 * total_x) / n_total
        return beta0, beta1
