import bcrypt

password = input("Ingresa tu contraseña: ")
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
print(f"Contraseña hasheada: \n{hashed.decode()}\nCópiala y pégala en el archivo config_auth.yaml (variable password) para usarla en el sistema.")