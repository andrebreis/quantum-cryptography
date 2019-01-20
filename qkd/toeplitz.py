from scipy.linalg import toeplitz
from numpy import matmul


def generate_toeplitz_matrix(seed_column, seed_line):
    return toeplitz(seed_column, seed_line)


def extract(matrix, sifted_key):
    return matmul(matrix, sifted_key)

