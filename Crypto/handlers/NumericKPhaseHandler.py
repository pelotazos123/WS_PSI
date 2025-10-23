import random
import numpy as np
from sklearn.linear_model import LinearRegression

class NumericKPhaseHandler:
    def __init__(self, id, devices, results):
        self.id = id
        self.devices = devices
        self.results = results
        self.pending_results = {}

    def local_compute(self, x_i, k=2):
        """Genera localmente las muestras (s_i, r1, r2)"""
        shares = []
        for _ in range(k):
            r1 = random.uniform(0, 1)
            r2 = random.uniform(0, 1)
            s = x_i + r1 + r2
            shares.append({"s": s, "r1": r1, "r2": r2})
        return shares

    def aggregate_results(self, all_shares):
        """Calcula la regresión lineal global."""
        X = np.array([[v["r1"], v["r2"]] for v in all_shares])
        y = np.array([v["s"] for v in all_shares])
        model = LinearRegression().fit(X, y)
        return {
            "beta0": float(model.intercept_),
            "beta1": float(model.coef_[0]),
            "beta2": float(model.coef_[1])
        }
