import numpy as np
from scipy import stats
from scipy.optimize import minimize
import warnings

class MAPMEstimator:
    """
    MPE: Multifractal Price Estimator for alpha, H, lambda from return series.
    Based on MAPM framework from Journal of Finance article.
    """

    def __init__(self, returns: np.ndarray, min_lag: int = 1, max_lag: int = 252):
        self.returns = np.array(returns)
        self.min_lag = min_lag
        self.max_lag = min(max_lag, len(returns) // 4)
        self.lags = np.logspace(np.log10(min_lag), np.log10(self.max_lag), 20).astype(int)

    def estimate_alpha_hill(self, tail_fraction: float = 0.1) -> tuple:
        abs_returns = np.abs(self.returns)
        n = len(abs_returns)
        k = int(n * tail_fraction)
        sorted_returns = np.sort(abs_returns)[::-1]
        log_ratios = np.log(sorted_returns[:k]) - np.log(sorted_returns[k])
        alpha_inv = np.mean(log_ratios)
        alpha_est = 1.0 / alpha_inv if alpha_inv > 0 else 2.0
        std_err = alpha_est / np.sqrt(k)
        alpha_est = np.clip(alpha_est, 1.5, 2.0)
        return alpha_est, std_err

    def structure_functions(self, q_values: np.ndarray = None) -> dict:
        if q_values is None:
            q_values = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
        n_lags = len(self.lags)
        n_q = len(q_values)
        S_q = np.zeros((n_lags, n_q))
        for i, lag in enumerate(self.lags):
            if lag >= len(self.returns):
                continue
            increments = np.abs(self.returns[lag:] - self.returns[:-lag])
            for j, q in enumerate(q_values):
                S_q[i, j] = np.mean(increments ** q) if q > 0 else np.mean(increments > 0)
        return {'lags': self.lags, 'q_values': q_values, 'S_q': S_q}

    def estimate_hurst_lambda(self) -> tuple:
        sf_data = self.structure_functions()
        lags = sf_data['lags']
        q_values = sf_data['q_values']
        S_q = sf_data['S_q']
        zeta_q = []
        valid_q = []
        for j, q in enumerate(q_values):
            y = np.log(S_q[:, j])
            x = np.log(lags)
            valid = np.isfinite(y) & np.isfinite(x) & (S_q[:, j] > 0)
            if np.sum(valid) < 3:
                continue
            slope, _, r_value, _, _ = stats.linregress(x[valid], y[valid])
            if r_value**2 > 0.8:
                zeta_q.append(slope)
                valid_q.append(q)
        if len(zeta_q) < 3:
            warnings.warn("Insufficient valid scaling exponents")
            return 0.55, 0.1, 0.0
        zeta_q = np.array(zeta_q)
        valid_q = np.array(valid_q)

        def zeta_model(params, q): return q * params[0] - params[1] * q * (q - 1)
        def objective(params): return np.sum((zeta_q - zeta_model(params, valid_q))**2)

        H_init = zeta_q[valid_q == 1.0][0] if 1.0 in valid_q else 0.55
        lam_init = 0.1
        try:
            result = minimize(objective, [H_init, lam_init], bounds=[(0.3, 0.8), (0.0, 0.5)])
            if result.success:
                H_est, lam_est = result.x
                predicted = zeta_model(result.x, valid_q)
                r_squared = 1 - np.sum((zeta_q - predicted)**2) / np.var(zeta_q)
                return H_est, lam_est, max(0.0, r_squared)
            else:
                return 0.55, 0.1, 0.0
        except:
            return 0.55, 0.1, 0.0

    def estimate_parameters(self) -> dict:
        alpha, alpha_se = self.estimate_alpha_hill()
        H, lam, r_sq = self.estimate_hurst_lambda()
        return {
            'alpha': alpha,
            'alpha_se': alpha_se,
            'H': H,
            'lambda': lam,
            'fit_quality': r_sq,
            'sample_size': len(self.returns),
            'empirical_bounds': {
                'alpha': (1.5, 2.0),
                'H': (0.3, 0.8),
                'lambda': (0.0, 0.5)
            }
        }

    def validate_derivative_consistency(self, derivative_params: dict) -> dict:
        if len(derivative_params) < 2:
            return {'error': 'Need at least 2 derivative types for consistency test'}
        alphas = [params[0] for params in derivative_params.values()]
        alpha_var = np.var(alphas, ddof=1)
        grand_mean = np.mean(alphas)
        f_stat = alpha_var / (grand_mean * 0.01)**2
        df1 = len(alphas) - 1
        df2 = len(self.returns) - len(alphas)
        p_value = 1 - stats.f.cdf(f_stat, df1, df2) if df2 > 0 else 1.0
        return {
            'alphas': alphas,
            'grand_mean': grand_mean,
            'variance': alpha_var,
            'f_statistic': f_stat,
            'p_value': p_value,
            'consistent': p_value > 0.05,
            'derivatives_tested': list(derivative_params.keys())
        }

