import math


def log(x,base):
    if x == 0:
        return 0
    return math.log(x,base)


def h(p):
    return -p*log(p, 2)-(1-p)*log((1-p), 2)


def remove_indices(l, indices):
    for indice in reversed(indices):
        del l[indice]

    return l


def calculate_parity(key, indexes):
    parity = 0
    for index in indexes:
        parity = (parity + key[index]) % 2
    return parity


def calculate_parities(key, list_blocks):
    parities = []
    for block in list_blocks:
        parities.append(calculate_parity(key, block))
    return parities


def get_num_block_with_index(blocks, index):
    for i in range(0, len(blocks)):
        for ind in blocks[i]:
            if ind == index:
                return i
