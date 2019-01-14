USAGE (assuming default simulaqron settings and server running):

sh run_example.sh

Alice will send a Qubit in a randomly chosen BB84 state (using its classical value 0/1 as key)
And then send a classical bit set to 1 from Alice to Bob, encoded with the key
Bob will choose a random basis and measure and then decipher the bit sent with the measurement result.
