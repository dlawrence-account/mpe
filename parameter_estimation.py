import numpy as np
from dataclasses import dataclass
from typing import Sequence, Dict, Optional

@dataclass
class MPEParams:
    alpha: float
    H: float
    lambda_: float

class MAPMEstimator:
    def __init__(self, returns: Sequence[float],
                 q_vals=(1.0, 2.0, 3.0, 4.0),
                 scales=(2, 4, 8, 16, 32),
                 min_blocks=8,
                 verbose=True):
        self.returns = np.asarray(returns, dtype=float)
        self.abs_returns = np.abs(self.returns)
        self.n = int(self.returns.size)
        self.q_vals = np.asarray(q_vals, dtype=float)
        self.scales = np.asarray(scales, dtype=int)
        self.min_blocks = int(min_blocks)
        self.verbose = verbose
        self._filter_scales()

    def _warn(self, msg: str):
        if self.verbose:
            print(f"⚠️ {msg}")

    def _filter_scales(self):
        valid = [s for s in self.scales if s >= 2 and (self.n // s) >= self.min_blocks]
        if not valid:
            self._warn("No scales met min_blocks; using fallback scales.")
            valid = [s for s in (2, 4, 8, 16, 32) if (self.n // s) >= 2]
        self.scales = np.asarray(valid, dtype=int)

    def estimate_alpha(self) -> float:
        x = np.sort(self.abs_returns[~np.isnan(self.abs_returns)])[::-1]
        x = x[np.isfinite(x)]
        x = x[x > 0]
        n = x.size
        if n < 50:
            self._warn(f"Too few observations (n={n}); α=1.7 default.")
            return 1.7
        # Use fixed 5% of sample for tail index
        k = max(20, int(0.05 * n))
        if k >= n:
            k = max(10, n // 10)
        top = x[:k]
        xk = x[k]
        if xk <= 0 or not np.isfinite(xk):
            self._warn("Invalid Hill threshold; α=1.7 default.")
            return 1.7
        logs = np.log(top) - np.log(xk)
        logs = logs[np.isfinite(logs)]
        if logs.size == 0 or logs.mean() <= 0:
            self._warn("Non-positive Hill denominator; α=1.7 default.")
            alpha = 1.7
        else:
            alpha = 1.0 / logs.mean()
        if alpha < 1.0 or alpha > 2.0:
            self._warn(f"Alpha out of bounds: {alpha:.4f}. Clamping.")
            alpha = float(np.clip(alpha, 1.0, 2.0))
        return float(alpha)

    def _block_aggregate(self, s: int) -> np.ndarray:
        m = (self.n // s) * s
        if m < s * 2:
            return np.array([])
        reshaped = self.abs_returns[:m].reshape(-1, s)
        return reshaped.mean(axis=1)

    def _structure_function(self, q: float) -> Optional[float]:
        moments, scales_used = [], []
        for s in self.scales:
            blk = self._block_aggregate(s)
            if blk.size < self.min_blocks:
                continue
            val = np.mean(np.power(blk, q))
            if not np.isfinite(val) or val <= 0:
                continue
            moments.append(val)
            scales_used.append(s)
        if len(scales_used) < 2:
            return None
        lx = np.log(scales_used)
        ly = np.log(moments)
        mask = np.isfinite(lx) & np.isfinite(ly)
        if mask.sum() < 2:
            return None
        lx, ly = lx[mask], ly[mask]
        # Keep only scales where S_q increases with s
        if len(ly) > 2:
            inc_mask = np.concatenate(([True], np.diff(ly) > 0))
            lx, ly = lx[inc_mask], ly[inc_mask]
        if len(lx) < 2:
            return None
        slope = np.polyfit(lx, ly, 1)[0]
        return float(slope)

    def estimate_scaling(self) -> Dict[float, float]:
        tau = {}
        for q in self.q_vals:
            slope = self._structure_function(q)
            if slope is not None:
                tau[float(q)] = slope
            else:
                self._warn(f"Scaling failed for q={q}.")
        return tau

    def estimate_parameters(self) -> MPEParams:
        alpha = self.estimate_alpha()
        tau = self.estimate_scaling()
        if 2.0 in tau:
            H = 0.5 * tau[2.0]
        else:
            self._warn("τ(2) missing; H=0.5 fallback.")
            H = 0.5
        if not np.isfinite(H) or H < 0.0 or H > 1.0:
            self._warn(f"H out of bounds ({H}); clamping.")
            H = float(np.clip(0.5 if not np.isfinite(H) else H, 0.0, 1.0))
        lambda_ = 0.0
        if len(tau) >= 3:
            qs = np.array(sorted(tau.keys()), dtype=float)
            tvals = np.array([tau[q] for q in qs], dtype=float)
            coeffs = np.polyfit(qs, tvals, 2)
            lambda_ = abs(coeffs[0])
        elif len(tau) >= 2:
            qs = np.array(sorted(tau.keys()), dtype=float)
            slopes = np.diff([tau[q] for q in qs])
            lambda_ = float(np.mean(np.abs(slopes)))
        if not np.isfinite(lambda_) or lambda_ < 0:
            self._warn(f"Invalid λ ({lambda_}); setting to 0.")
            lambda_ = 0.0
        return MPEParams(alpha=float(alpha), H=float(H), lambda_=float(lambda_))

def estimate_parameters_from_series(returns: Sequence[float], **kwargs) -> Dict[str, float]:
    est = MAPMEstimator(returns, **kwargs)
    params = est.estimate_parameters()
    return {
        "alpha": round(params.alpha, 4),
        "H": round(params.H, 4),
        "lambda": round(params.lambda_, 4)
    }
