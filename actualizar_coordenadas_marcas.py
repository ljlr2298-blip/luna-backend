from supabase import create_client
import requests

SUPABASE_URL = "https://kcwkyhfargaijkvucpeh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Tu key

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def obtener_coordenadas(direccion):
    """Usa Nominatim para geocodificar"""
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={direccion}&countrycodes=mx&limit=1"
    headers = {'User-Agent': 'LunaDeliveryApp/1.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Error: {e}")
    return None, None

# Obtener todas las marcas
marcas = supabase.table('marcas').select('id, nombre, calle, colonia, cp, municipio').execute()

for marca in marcas.data:
    print(f"\n📍 Procesando: {marca['nombre']}")
    
    # Verificar si ya tiene coordenadas
    if marca.get('marca_lat') and marca.get('marca_lng'):
        print(f"✅ Ya tiene coordenadas: {marca['marca_lat']}, {marca['marca_lng']}")
        continue
    
    # Construir dirección completa
    direccion = f"{marca.get('calle', '')}, {marca.get('colonia', '')}, {marca.get('cp', '')}, {marca.get('municipio', '')}, Jalisco, Mexico"
    print(f"🔍 Geocodificando: {direccion}")
    
    lat, lng = obtener_coordenadas(direccion)
    
    if lat and lng:
        print(f"✅ Coordenadas encontradas: {lat}, {lng}")
        # Actualizar en Supabase
        supabase.table('marcas').update({
            "marca_lat": lat,
            "marca_lng": lng
        }).eq('id', marca['id']).execute()
        print(f"💾 Guardado en BD")
    else:
        print(f"❌ No se pudieron obtener coordenadas")