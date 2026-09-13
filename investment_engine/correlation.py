import numpy as np


def validate_correlation(matrix):
    a = np.asarray(matrix, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("Correlation matrix must be square")
    if not np.allclose(a, a.T, atol=1e-10):
        raise ValueError("Correlation matrix must be symmetric")
    if not np.allclose(np.diag(a), 1.0, atol=1e-10):
        raise ValueError("Correlation diagonal must be 1")
    if np.min(np.linalg.eigvalsh(a)) < -1e-10:
        raise ValueError("Correlation matrix must be positive semidefinite")
    return True


def sample_correlated(matrix, n, rng):
    validate_correlation(matrix)
    return rng.multivariate_normal(np.zeros(len(matrix)), matrix, size=n)


class CorrelatedSampler:
    def __call__(self, matrix, n, rng):
        return sample_correlated(matrix, n, rng)


class CorrelationValidator:
    def __call__(self, matrix):
        return validate_correlation(matrix)
