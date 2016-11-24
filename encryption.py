from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
import random
import string
import os

padding = lambda s: (16 - len(s) % 16) * 'X'

salt = "98agy98mceriaucjhmiuefc"

def ran(N):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(N))

#given a string s, returns a list containing an encrypted string and a key
def encrypt(s):
    secret = ran(8)
    key = PBKDF2(secret,salt,count=100000)
    cipher = AES.new(key + padding(key))
    pad = padding(s)
    return [cipher.encrypt(s + pad), secret + chr(len(pad) + 97)]

#given an encrypted string and a key, returns a string
def decrypt(s,k):
    pl = (ord(k[-1]) - 97)
    key = PBKDF2(k[:-1],salt,count=100000)
    cipher = AES.new(key + padding(key))
    raw = cipher.decrypt(s)
    return raw[:-pl]

#encrypts data, saves it to a path and returns a key
def f_encrypt(path,data):
    msg = encrypt(data)
    n = open(path + '.aes', 'w')
    n.write(msg[0])
    n.close()
    return msg[1]

#decrypts a file and returns the contents
def f_decrypt(path, k):
    f = open(path + '.aes','r')
    data = f.read()
    #it would be more memory efficient to loop over lines or something, but
    #then each line would need to be separately padded to 16 bytes
    f.close()
    return decrypt(data,k)
