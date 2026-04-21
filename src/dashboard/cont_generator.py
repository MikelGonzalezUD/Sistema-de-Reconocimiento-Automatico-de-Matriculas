import bcrypt

password = 'tu_password'
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
print(hashed.decode())