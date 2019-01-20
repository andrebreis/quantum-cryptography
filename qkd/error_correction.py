import json
import math
import random

import utils
import communication


class CascadeAlgorithm(object):

    def __init__(self, party):
        self.party = party

    def run_algorithm(self):
        pass

    def _binary(self, block):
        pass


class CascadeSender(CascadeAlgorithm):
    def __init__(self, party):
        CascadeAlgorithm.__init__(self, party)

    def run_algorithm(self):
        n = math.ceil(0.73/self.party.error_estimation)
        iterations = [[]]

        # 1st iteration
        for i in range(0, len(self.party.sifted_key), n):
            iterations[0].append(list(range(i, min(i + n, len(self.party.sifted_key) - 1))))

        parities = utils.calculate_parities(self.party.sifted_key, iterations[0])
        communication.send_binary_list(self.party.cqc, self.party.receiver, self.party.skey, parities)
        msg = communication.receive_message(self.party.cqc, self.party.receiver_pkey)
        while msg != 'ALL DONE':
            block_num = int(msg)
            self._binary(iterations[0][block_num])
            msg = communication.receive_message(self.party.cqc, self.party.receiver_pkey)

        # nth iteration
        for iter_num in range(1, 4):
            n = 2 * n
            iterations.append([])

            # Choose function fi [1...n] -> [1...n/ki], send and save in iterations[iter_num]
            temp_indices = list(range(0, len(self.party.sifted_key)))
            random.shuffle(temp_indices)
            communication.send_message(self.party.cqc, self.party.receiver, self.party.skey, temp_indices)
            for i in range(0, len(self.party.sifted_key), n):
                iterations[iter_num].append(temp_indices[i:min(i + n, len(self.party.sifted_key) - 1)])

            parities = utils.calculate_parities(self.party.sifted_key, iterations[iter_num])
            communication.send_binary_list(self.party.cqc, self.party.receiver, self.party.skey, parities)

            msg = communication.receive_message(self.party.cqc, self.party.receiver_pkey)
            while msg != 'ALL DONE':
                iter_num, block_num = json.loads(msg)
                self._binary(iterations[iter_num][block_num])
                msg = communication.receive_message(self.party.cqc, self.party.receiver_pkey)

    def _binary(self, block):
        first_half_size = math.ceil(len(block) / 2.0)
        first_half_par = utils.calculate_parity(self.party.sifted_key, block[:first_half_size])
        communication.send_message(self.party.cqc, self.party.receiver, self.party.skey, first_half_par)
        msg = communication.receive_message(self.party.cqc, self.party.receiver_pkey)
        if msg != 'DONE':
            block_part = int(msg)
            if block_part == 0:
                self._binary(block[:first_half_size])
            else:
                self._binary(block[first_half_size:])


class CascadeReceiver(CascadeAlgorithm):
    def __init__(self, party):
        CascadeAlgorithm.__init__(self, party)

    def run_algorithm(self):
        n = math.ceil(0.73 / self.party.error_estimation)
        iterations = [[]]

        # 1st iteration
        for i in range(0, len(self.party.sifted_key), n):
            iterations[0].append(list(range(i, min(i + n, len(self.party.sifted_key) - 1))))

        parities = utils.calculate_parities(self.party.sifted_key, iterations[0])
        alice_parities = communication.receive_binary_list(self.party.cqc, self.party.sender_pkey)

        for i in range(0, len(alice_parities)):
            if parities[i] != alice_parities[i]:
                communication.send_message(self.party.cqc, self.party.sender, self.party.skey, i)
                self._binary(iterations[0][i])
        communication.send_message(self.party.cqc, self.party.sender, self.party.skey, 'ALL DONE')

        # nth iteration
        for iter_num in range(1, 4):
            n = 2 * n
            iterations.append([])
            temp_indices = communication.receive_list(self.party.cqc, self.party.sender_pkey)
            for i in range(0, len(self.party.sifted_key), n):
                iterations[iter_num].append(temp_indices[i:min(i + n, len(self.party.sifted_key) - 1)])
            parities = utils.calculate_parities(self.party.sifted_key, iterations[iter_num])
            alice_parities = communication.receive_binary_list(self.party.cqc, self.party.sender_pkey)
            for i in range(0, len(alice_parities)):
                if parities[i] != alice_parities[i]:
                    correcting_block = i
                    for j in range(0, iter_num + 1):
                        communication.send_message(self.party.cqc, self.party.sender, self.party.skey, [iter_num - j, correcting_block])
                        corrected_index = self._binary(iterations[iter_num - j][correcting_block])
                        if iter_num - j - 1 >= 0:
                            correcting_block = utils.get_num_block_with_index(iterations[iter_num - j - 1], corrected_index)
            communication.send_message(self.party.cqc, self.party.sender, self.party.skey, 'ALL DONE')

    def _binary(self, block):
        alice_first_half_par = int(communication.receive_message(self.party.cqc, self.party.sender_pkey))

        first_half_size = math.ceil(len(block) / 2.0)
        first_half_par = utils.calculate_parity(self.party.sifted_key, block[:first_half_size])

        if first_half_par != alice_first_half_par:
            if first_half_size == 1:
                self.party.sifted_key[block[0]] = (self.party.sifted_key[block[0]] + 1) % 2
                communication.send_message(self.party.cqc, self.party.sender, self.party.skey, 'DONE')
                return block[0]
            else:
                communication.send_message(self.party.cqc, self.party.sender, self.party.skey, 0)
                return self._binary(block[:first_half_size])
        else:
            if len(block) - first_half_size == 1:
                self.party.sifted_key[block[-1]] = (self.party.sifted_key[block[-1]] + 1) % 2
                communication.send_message(self.party.cqc, self.party.sender, self.party.skey, 'DONE')
                return block[-1]
            else:
                communication.send_message(self.party.cqc, self.party.sender, self.party.skey, 1)
                return self._binary(block[first_half_size:])
