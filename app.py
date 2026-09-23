import os
import json
import random
from flask import Flask, render_template, jsonify, request
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Conectar a Supabase vía API REST
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("❌ Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Conectado a Supabase vía API REST")

# ==========================================
# 1. RUTAS DE VISTAS (Frontend)
# ==========================================

@app.route('/')
def home():
    return render_template('index.html', modo='cliente', token='')

@app.route('/admin')
def admin_panel():
    return render_template('index.html', modo='admin', token='')

@app.route('/repartidor')
def repartidor_panel():
    return render_template('index.html', modo='repartidor', token='')

@app.route('/rastreo/<token>')
def rastreo_publico(token):
    return render_template('index.html', modo='rastreo', token=token)

# ==========================================
# 2. APIs DEL SISTEMA
# ==========================================

@app.route('/test-db')
def test_db():
    try:
        response = supabase.table('marcas').select('id', count='exact').limit(1).execute()
        return jsonify({"status": "success", "message": f"¡Conectado a Supabase! Total de marcas: {response.count}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/getMunicipios', methods=['GET'])
def api_get_municipios():
    try:
        response = supabase.table('zonas_postales').select('municipio').execute()
        municipios = sorted(list(set([row['municipio'] for row in response.data if row.get('municipio')])))
        return jsonify({"result": municipios})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getCPs', methods=['GET'])
def api_get_cps():
    municipio = request.args.get('arg0', '')
    try:
        response = supabase.table('zonas_postales').select('cp').eq('municipio', municipio).execute()
        cps = sorted(list(set([row['cp'] for row in response.data if row.get('cp')])))
        return jsonify({"result": cps})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getColonias', methods=['GET'])
def api_get_colonias():
    cp = request.args.get('arg0', '')
    try:
        response = supabase.table('zonas_postales').select('colonia').eq('cp', cp).execute()
        colonias = sorted(list(set([row['colonia'] for row in response.data if row.get('colonia')])))
        return jsonify({"result": colonias})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/validarAccAccess', methods=['GET'])
def api_validar_acc_access():
    marca = request.args.get('arg0', '')
    password = request.args.get('arg1', '')
    
    print(f"🔍 Intento de login - Marca: '{marca}', Password: '{password}'")
    if not marca or not password:
        return jsonify({"result": False})
    
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data and len(response.data) > 0:
            stored_password = response.data[0].get('password_hash')
            if str(stored_password).strip() == str(password).strip():
                print("✅ Login exitoso")
                return jsonify({"result": True})
        print("❌ Credenciales incorrectas")
        return jsonify({"result": False})
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return jsonify({"result": False})

@app.route('/api/registrarMarca', methods=['GET'])
def api_registrar_marca():
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        supabase.table('marcas').insert({
            "nombre": data.get('m'), "municipio": data.get('mun'), "colonia": data.get('col'),
            "calle": data.get('calle'), "telefono": data.get('tel'), "password_hash": data.get('pass')
        }).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getPedidos', methods=['GET'])
def api_get_pedidos():
    marca = request.args.get('arg0', '')
    modo = request.args.get('arg1', 'cliente')
    
    try:
        if modo == 'admin':
            # 1. Obtener todos los pedidos
            response = supabase.table('pedidos').select('*').order('creado_en', desc=True).execute()
            pedidos_raw = response.data
            
            # 2. Obtener todas las marcas para hacer el "cruce" de datos
            marcas_response = supabase.table('marcas').select('id, nombre').execute()
            marcas_dict = {str(m['id']): m['nombre'] for m in marcas_response.data}
            
            pedidos = []
            for row in pedidos_raw:
                # 3. Aquí está la clave: usamos el nombre real de la marca
                nombre_marca = marcas_dict.get(str(row.get('marca_id')), 'Desconocida')
                
                pedidos.append({
                    "id": row.get('id'),
                    "token": row.get('token'),
                    "marca": nombre_marca, # <-- Ahora sí mostrará "VS Beauty", "Luna", etc.
                    "origen": row.get('origen', ''),
                    "destino": row.get('destino', ''),
                    "precio": float(row.get('precio', 0) or 0),
                    "recibe": row.get('recibe_nombre', ''),
                    "celular": row.get('recibe_celular', ''),
                    "coments": row.get('comentarios', ''),
                    "status": row.get('status', 'Pendiente'),
                    "dia": row.get('dia_programado', ''),
                    "diaLetra": (row.get('dia_programado', '') or '')[:2],
                    "km": float(row.get('km', 0) or 0),
                    "prioridad": row.get('prioridad', 999) or 999,
                    "estadoPago": row.get('estado_pago', 'Pendiente'),
                    "tipoServicio": row.get('tipo_servicio', 'enviar'),
                    "direccionProveedor": row.get('direccion_proveedor', ''),
                    "repartidor": row.get('repartidor_id', ''),
                    "ordenEntrega": row.get('orden_entrega'),
                    "fila": row.get('id'),
                    "fecha": row.get('creado_en')
                })
            return jsonify({"result": pedidos})
            
        else:
            # Lógica normal para cuando entra una marca (cliente)
            marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
            if not marca_response.data:
                return jsonify({"result": []})
            marca_id = marca_response.data[0]['id']
            response = supabase.table('pedidos').select('*').eq('marca_id', marca_id).order('creado_en', desc=True).execute()
            
            pedidos = []
            for row in response.data:
                pedidos.append({
                    "id": row.get('id'), "token": row.get('token'), "marca": marca,
                    "origen": row.get('origen', ''), "destino": row.get('destino', ''),
                    "precio": float(row.get('precio', 0) or 0), "recibe": row.get('recibe_nombre', ''),
                    "celular": row.get('recibe_celular', ''), "coments": row.get('comentarios', ''),
                    "status": row.get('status', 'Pendiente'), "dia": row.get('dia_programado', ''),
                    "diaLetra": (row.get('dia_programado', '') or '')[:2], "km": float(row.get('km', 0) or 0),
                    "prioridad": row.get('prioridad', 999) or 999, "estadoPago": row.get('estado_pago', 'Pendiente'),
                    "tipoServicio": row.get('tipo_servicio', 'enviar'), "direccionProveedor": row.get('direccion_proveedor', ''),
                    "repartidor": row.get('repartidor_id', ''), "ordenEntrega": row.get('orden_entrega'),
                    "fila": row.get('id'), "fecha": row.get('creado_en')
                })
            return jsonify({"result": pedidos})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/guardarPedido', methods=['GET'])
def api_guardar_pedido():
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        marca_response = supabase.table('marcas').select('id').ilike('nombre', data.get('marca', '')).execute()
        marca_id = marca_response.data[0]['id'] if marca_response.data else None
        prefijo = data.get('marca', 'PED')[:3].upper()
        token = prefijo + str(random.randint(1000, 9999))
        
        supabase.table('pedidos').insert({
            "token": token, "marca_id": marca_id, "tipo_servicio": data.get('tipoServicio', 'enviar'),
            "origen": data.get('origen'), "destino": data.get('destino'), "precio": data.get('precio'),
            "recibe_nombre": data.get('recibe'), "recibe_celular": data.get('celular'),
            "comentarios": data.get('coments'), "km": data.get('km'), "estado_pago": "Pendiente", "dia_programado": "Por asignar"
        }).execute()
        return jsonify({"result": token})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerPerfilMarca', methods=['GET'])
def api_obtener_perfil():
    marca = request.args.get('arg0', '')
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data and len(response.data) > 0:
            row = response.data[0]
            return jsonify({"result": {"exito": True, "marca": row.get('nombre'), "municipio": row.get('municipio'),
                "colonia": row.get('colonia'), "calle": row.get('calle'), "telefono": row.get('telefono'),
                "logo": row.get('logo_url') or "", "slogan": row.get('slogan') or ""}})
        return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerDeudaCliente', methods=['GET'])
def api_obtener_deuda():
    marca = request.args.get('arg0', '')
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data:
            return jsonify({"result": {"pedidosPendientes": 0, "deuda": 0}})
        marca_id = marca_response.data[0]['id']
        response = supabase.table('pedidos').select('precio').eq('marca_id', marca_id).eq('estado_pago', 'Pendiente').neq('status', 'Cancelado').execute()
        deuda = sum(float(p.get('precio', 0) or 0) for p in response.data)
        return jsonify({"result": {"pedidosPendientes": len(response.data), "deuda": deuda}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getListaRepartidores', methods=['GET'])
def api_get_lista_repartidores():
    try:
        response = supabase.table('repartidores').select('id, nombre, telefono, activo').eq('activo', True).execute()
        return jsonify({"result": response.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getProveedoresFrecuentes', methods=['GET'])
def api_get_proveedores():
    marca = request.args.get('arg0', '')
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": []})
        response = supabase.table('proveedores').select('*').eq('marca_id', marca_response.data[0]['id']).order('nombre').execute()
        return jsonify({"result": response.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getDireccionTienda', methods=['GET'])
def api_get_direccion_tienda():
    marca = request.args.get('arg0', '')
    try:
        response = supabase.table('marcas').select('calle, colonia, municipio').ilike('nombre', marca).execute()
        if response.data:
            row = response.data[0]
            return jsonify({"result": {"exito": True, "direccionCompleta": f"{row.get('calle', '')}, {row.get('colonia', '')}, {row.get('municipio', '')}, Jalisco, Mexico"}})
        return jsonify({"result": {"exito": False}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerUrlApp', methods=['GET'])
def api_obtener_url():
    return jsonify({"result": request.host_url})

@app.route('/api/marcarPago', methods=['GET'])
def api_marcar_pago():
    fila = request.args.get('arg0', '')
    estado = request.args.get('arg1', 'Pagado')
    try:
        supabase.table('pedidos').update({"estado_pago": estado}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": f"Estado actualizado a {estado}"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerDatosRastreoCliente', methods=['GET'])
def api_obtener_datos_rastreo():
    token = request.args.get('arg0', '')
    try:
        response = supabase.table('pedidos').select('status, recibe_nombre, destino, dia_programado, lat, lng, marca_id').eq('token', token).execute()
        if response.data:
            row = response.data[0]
            marca_response = supabase.table('marcas').select('nombre').eq('id', row.get('marca_id')).execute()
            return jsonify({"result": {
                "status": row.get('status'), "recibe": row.get('recibe_nombre'), "marca": marca_response.data[0]['nombre'] if marca_response.data else '',
                "destino": row.get('destino'), "dia": row.get('dia_programado'),
                "mostrarMapa": row.get('status') == "En Entrega" and row.get('lat') and row.get('lng'),
                "moto": {"lat": float(row.get('lat', 0) or 0), "lng": float(row.get('lng', 0) or 0)}
            }})
        return jsonify({"result": {"error": "Pedido no encontrado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/iniciarEntregaConGPS', methods=['GET'])
def api_iniciar_entrega_gps():
    fila = request.args.get('arg0', '')
    lat = request.args.get('arg1')
    lng = request.args.get('arg2')
    try:
        supabase.table('pedidos').update({"status": "En Entrega", "lat": float(lat) if lat else None, "lng": float(lng) if lng else None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Entrega iniciada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getDestinatariosFrecuentes', methods=['GET'])
def api_get_destinatarios():
    marca = request.args.get('arg0', '')
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": []})
        response = supabase.table('pedidos').select('recibe_nombre, recibe_celular, destino').eq('marca_id', marca_response.data[0]['id']).neq('status', 'Cancelado').execute()
        vistos, destinatarios = set(), []
        for row in response.data:
            if row.get('recibe_nombre') and row['recibe_nombre'] not in vistos:
                vistos.add(row['recibe_nombre'])
                destinatarios.append({"nombre": row['recibe_nombre'], "celular": row.get('recibe_celular'), "destino": row.get('destino')})
        return jsonify({"result": destinatarios})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarPedido', methods=['GET'])
def api_actualizar_pedido():
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        supabase.table('pedidos').update({
            "origen": data.get('origen'), "destino": data.get('destino'), "precio": data.get('precio'),
            "recibe_nombre": data.get('recibe'), "recibe_celular": data.get('celular'), "comentarios": data.get('coments'),
            "km": data.get('km'), "tipo_servicio": data.get('tipoServicio'), "direccion_proveedor": data.get('direccionProveedor')
        }).eq('id', int(data.get('fila'))).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cancelarPedido', methods=['GET'])
def api_cancelar_pedido():
    fila = request.args.get('arg0', '')
    try:
        supabase.table('pedidos').update({"status": "Cancelado"}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Pedido cancelado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarStatus', methods=['GET'])
def api_actualizar_status():
    fila, status = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"status": "Entregado" if status == "Completado" else status}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarDiaUnico', methods=['GET'])
def api_actualizar_dia():
    fila, letra = request.args.get('arg0', ''), request.args.get('arg1', '')
    mapa = {'L': 'Lunes', 'M': 'Martes', 'MI': 'Miércoles', 'J': 'Jueves', 'V': 'Viernes', 'S': 'Sábado'}
    try:
        supabase.table('pedidos').update({"dia_programado": mapa.get(letra.upper(), 'Por asignar')}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarPrioridad', methods=['GET'])
def api_actualizar_prioridad():
    fila, valor = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"prioridad": int(valor) if valor else 999}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerFilasEnEntrega', methods=['GET'])
def api_obtener_filas_en_entrega():
    try:
        response = supabase.table('pedidos').select('id').eq('status', 'En Entrega').execute()
        return jsonify({"result": [row['id'] for row in response.data]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarGPSGlobal', methods=['GET'])
def api_actualizar_gps_global():
    try:
        filas = json.loads(request.args.get('arg0', '[]'))
        lat, lng = request.args.get('arg1'), request.args.get('arg2')
        for fila in filas:
            supabase.table('pedidos').update({"lat": float(lat), "lng": float(lng)}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "cantidad": len(filas)}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/asignarPedidoRepartidor', methods=['GET'])
def api_asignar_pedido_repartidor():
    fila, id_repartidor = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"repartidor_id": id_repartidor if id_repartidor else None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Pedido asignado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/quitarAsignacionRepartidor', methods=['GET'])
def api_quitar_asignacion():
    fila = request.args.get('arg0', '')
    try:
        supabase.table('pedidos').update({"repartidor_id": None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Asignación quitada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 3. INICIAR SERVIDOR
# ==========================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 LUNA DELIVERY BACKEND")
    print("📍 URLs disponibles:")
    print("   👤 Cliente:    http://127.0.0.1:5000/")
    print("   🔐 Admin:      http://127.0.0.1:5000/admin")
    print("   🚗 Repartidor: http://127.0.0.1:5000/repartidor")
    print("   📍 Rastreo:    http://127.0.0.1:5000/rastreo/<TOKEN>")
    print("=" * 50)
    # host='0.0.0.0' permite que tu celular acceda si está en la misma red Wi-Fi
    port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port, debug=False)