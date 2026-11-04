import base64
from cryptography.hazmat.primitives.asymmetric import ec

# 1. Generar clave privada
private_key = ec.generate_private_key(ec.SECP256R1())

# 2. Obtener clave pública en formato no comprimido (0x04 + x + y)
public_numbers = private_key.public_key().public_numbers()
x = public_numbers.x.to_bytes(32, byteorder='big')
y = public_numbers.y.to_bytes(32, byteorder='big')
uncompressed_public_key = b'\x04' + x + y

# 3. Codificar en base64url (sin padding) para el frontend
public_key_b64 = base64.urlsafe_b64encode(uncompressed_public_key).rstrip(b'=').decode('utf-8')

# 4. Obtener clave privada en formato base64url para el backend
private_key_int = private_key.private_numbers().private_value
private_key_bytes = private_key_int.to_bytes(32, byteorder='big')
private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).rstrip(b'=').decode('utf-8')

print("=" * 60)
print("✅ CLAVES VAPID GENERADAS CORRECTAMENTE")
print("=" * 60)
print("\n📱 === CLAVE PÚBLICA (para index.html) ===")
print(public_key_b64)
print("\n🔒 === CLAVE PRIVADA (para app.py) ===")
print(private_key_b64)
print("=" * 60)