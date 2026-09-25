import os
import json
import random
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='templates')

# ==========================================
# 1. CONFIGURACIÓN DE SUPABASE
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://kcwkyhfargaijkvucpeh.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtjd2t5aGZhcmdhaWprdnVjcGVoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAwODkwMjEsImV4cCI6MjEwNTY2NTAyMX0.1R2rirPSit6I-YqO2tBN2FBgSxp5Iq31fDkXVbbTCNg"

print(f"🔍 SUPABASE_URL detectada: {'✅ SÍ' if SUPABASE_URL else '❌ NO'}")
print(f"🔑 SUPABASE_KEY detectada: {'✅ SÍ' if SUPABASE_KEY else '❌ NO'}")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Conectado a Supabase exitosamente")
    except Exception as e:
        print(f"⚠️ Error conectando a Supabase: {e}")
else:
    print("⚠️ Supabase no configurado. La app iniciará pero sin base de datos.")

# ==========================================
# 1.5 CONFIGURACIÓN DE TARIFAS ESPECIALES
# ==========================================
MARCAS_PREMIUM = ['VS Beauty', 'VS Beauty 2', 'Ale Joyería', 'Alicia Aranda']
MARCAS_PRECIO_FIJO = {'Hane & beauty': 90}

# ==========================================
# 2. RUTAS DE VISTAS (Frontend)
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

@app.route('/test-db')
def test_db():
    if not supabase:
        return jsonify({"status": "error", "message": "Supabase no configurado."}), 500
    try:
        response = supabase.table('marcas').select('id', count='exact').limit(1).execute()
        return jsonify({"status": "success", "message": f"¡Conectado! Total marcas: {response.count}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 3. APIs DE AUTENTICACIÓN Y REGISTRO
# ==========================================
@app.route('/api/validarAccAccess', methods=['GET'])
def api_validar_acc_access():
    if not supabase: return jsonify({"result": False, "error": "Supabase no configurado"}), 500
    marca = request.args.get('arg0', '')
    password = request.args.get('arg1', '')
    if not marca or not password: return jsonify({"result": False})
    
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data and len(response.data) > 0:
            stored_password = response.data[0].get('password_hash')
            if str(stored_password).strip() == str(password).strip():
                return jsonify({"result": True})
        return jsonify({"result": False})
    except Exception as e:
        print(f"Error login: {e}")
        return jsonify({"result": False})

@app.route('/api/registrarMarca', methods=['GET'])
def api_registrar_marca():
    if not supabase: return jsonify({"result": False}), 500
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        supabase.table('marcas').insert({
            "nombre": data.get('m'), "municipio": data.get('mun'), "colonia": data.get('col'),
            "calle": data.get('calle'), "telefono": data.get('tel'), "password_hash": data.get('pass')
        }).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 4. APIs DE PEDIDOS
# ==========================================
@app.route('/api/getPedidos', methods=['GET'])
def api_get_pedidos():
    if not supabase: return jsonify({"result": [], "error": "Supabase no configurado"}), 500
    marca = request.args.get('arg0', '')
    modo = request.args.get('arg1', 'cliente')
    
    try:
        if modo == 'admin':
            response = supabase.table('pedidos').select('*').order('creado_en', desc=True).execute()
            marcas_response = supabase.table('marcas').select('id, nombre').execute()
            marcas_dict = {str(m['id']): m['nombre'] for m in marcas_response.data}
        else:
            marca_response = supabase.table('marcas').select('id, nombre').ilike('nombre', marca).execute()
            if not marca_response.data: return jsonify({"result": []})
            marca_id = marca_response.data[0]['id']
            response = supabase.table('pedidos').select('*').eq('marca_id', marca_id).order('creado_en', desc=True).execute()
            marcas_dict = {str(marca_id): marca_response.data[0]['nombre']}
        
        pedidos = []
        for row in response.data:
            nombre_marca = marcas_dict.get(str(row.get('marca_id')), 'Desconocida')
            pedidos.append({
                "id": row.get('id'), "token": row.get('token'), "marca": nombre_marca,
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
    if not supabase: return jsonify({"error": "Supabase no configurado"}), 500
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

@app.route('/api/actualizarPedido', methods=['GET'])
def api_actualizar_pedido():
    if not supabase: return jsonify({"result": False}), 500
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
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila = request.args.get('arg0', '')
    try:
        supabase.table('pedidos').update({"status": "Cancelado"}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Pedido cancelado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarStatus', methods=['GET'])
def api_actualizar_status():
    if not supabase: return jsonify({"result": False}), 500
    fila, status = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"status": "Entregado" if status == "Completado" else status}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarDiaUnico', methods=['GET'])
def api_actualizar_dia():
    if not supabase: return jsonify({"result": False}), 500
    fila, letra = request.args.get('arg0', ''), request.args.get('arg1', '')
    mapa = {'L': 'Lunes', 'M': 'Martes', 'MI': 'Miércoles', 'J': 'Jueves', 'V': 'Viernes', 'S': 'Sábado'}
    try:
        supabase.table('pedidos').update({"dia_programado": mapa.get(letra.upper(), 'Por asignar')}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarPrioridad', methods=['GET'])
def api_actualizar_prioridad():
    if not supabase: return jsonify({"result": False}), 500
    fila, valor = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"prioridad": int(valor) if valor else 999}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 5. APIs DE RASTREO Y GPS
# ==========================================
@app.route('/api/obtenerDatosRastreoCliente', methods=['GET'])
def api_obtener_datos_rastreo():
    if not supabase: return jsonify({"result": {"error": "Supabase no configurado"}}), 500
    token = request.args.get('arg0', '')
    try:
        response = supabase.table('pedidos').select('status, recibe_nombre, destino, dia_programado, lat, lng, marca_id').eq('token', token).execute()
        if response.data:
            row = response.data[0]
            marca_response = supabase.table('marcas').select('nombre').eq('id', row.get('marca_id')).execute()
            return jsonify({"result": {
                "status": row.get('status'), "recibe": row.get('recibe_nombre'), 
                "marca": marca_response.data[0]['nombre'] if marca_response.data else '',
                "destino": row.get('destino'), "dia": row.get('dia_programado'),
                "mostrarMapa": row.get('status') == "En Entrega" and row.get('lat') and row.get('lng'),
                "moto": {"lat": float(row.get('lat', 0) or 0), "lng": float(row.get('lng', 0) or 0)}
            }})
        return jsonify({"result": {"error": "Pedido no encontrado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/iniciarEntregaConGPS', methods=['GET'])
def api_iniciar_entrega_gps():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila, lat, lng = request.args.get('arg0', ''), request.args.get('arg1'), request.args.get('arg2')
    try:
        supabase.table('pedidos').update({
            "status": "En Entrega", "lat": float(lat) if lat else None, "lng": float(lng) if lng else None
        }).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Entrega iniciada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerFilasEnEntrega', methods=['GET'])
def api_obtener_filas_en_entrega():
    if not supabase: return jsonify({"result": []}), 500
    try:
        response = supabase.table('pedidos').select('id').eq('status', 'En Entrega').execute()
        return jsonify({"result": [row['id'] for row in response.data]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarGPSGlobal', methods=['GET'])
def api_actualizar_gps_global():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        filas = json.loads(request.args.get('arg0', '[]'))
        lat, lng = request.args.get('arg1'), request.args.get('arg2')
        for fila in filas:
            supabase.table('pedidos').update({"lat": float(lat), "lng": float(lng)}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "cantidad": len(filas)}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 6. APIs DE REPARTIDORES
# ==========================================
@app.route('/api/getListaRepartidores', methods=['GET'])
def api_get_lista_repartidores():
    if not supabase: return jsonify({"result": []}), 500
    try:
        response = supabase.table('repartidores').select('id, nombre, telefono, activo').eq('activo', True).execute()
        return jsonify({"result": response.data})
    except Exception as e:
        return jsonify({"result": []})

@app.route('/api/asignarPedidoRepartidor', methods=['GET'])
def api_asignar_pedido_repartidor():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila, id_repartidor = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"repartidor_id": id_repartidor if id_repartidor else None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Pedido asignado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/quitarAsignacionRepartidor', methods=['GET'])
def api_quitar_asignacion():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila = request.args.get('arg0', '')
    try:
        supabase.table('pedidos').update({"repartidor_id": None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Asignación quitada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 7. APIs DE FINANZAS Y COBROS
# ==========================================
@app.route('/api/obtenerDeudaCliente', methods=['GET'])
def api_obtener_deuda():
    if not supabase: return jsonify({"result": {"pedidosPendientes": 0, "deuda": 0}}), 500
    marca = request.args.get('arg0', '')
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": {"pedidosPendientes": 0, "deuda": 0}})
        marca_id = marca_response.data[0]['id']
        response = supabase.table('pedidos').select('precio').eq('marca_id', marca_id).eq('estado_pago', 'Pendiente').neq('status', 'Cancelado').execute()
        deuda = sum(float(p.get('precio', 0) or 0) for p in response.data)
        return jsonify({"result": {"pedidosPendientes": len(response.data), "deuda": deuda}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marcarPago', methods=['GET'])
def api_marcar_pago():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila, estado = request.args.get('arg0', ''), request.args.get('arg1', 'Pagado')
    try:
        supabase.table('pedidos').update({"estado_pago": estado}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": f"Estado actualizado a {estado}"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerPedidosPendientes', methods=['GET'])
def api_obtener_pedidos_pendientes():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    filtro_marca = request.args.get('arg0', 'todas')
    try:
        query = supabase.table('pedidos').select('*').eq('estado_pago', 'Pendiente').neq('status', 'Cancelado')
        if filtro_marca != 'todas':
            marca_response = supabase.table('marcas').select('id').ilike('nombre', filtro_marca).execute()
            if marca_response.data: query = query.eq('marca_id', marca_response.data[0]['id'])
        
        response = query.execute()
        marcas_response = supabase.table('marcas').select('id, nombre, telefono').execute()
        marcas_dict = {str(m['id']): {'nombre': m['nombre'], 'telefono': m.get('telefono', '')} for m in marcas_response.data}
        
        pedidos_lista = []
        for p in response.data:
            marca_info = marcas_dict.get(str(p.get('marca_id')), {'nombre': 'Desconocida', 'telefono': ''})
            pedidos_lista.append({
                'fila': p.get('id'), 'id': p.get('token', ''), 'marca': marca_info['nombre'],
                'recibe': p.get('recibe_nombre', ''), 'celular': p.get('recibe_celular', ''),
                'celularMarca': marca_info['telefono'], 'destino': p.get('destino', ''),
                'precio': float(p.get('precio', 0) or 0), 'fecha': p.get('creado_en', ''), 'status': p.get('status', 'Pendiente')
            })
        
        return jsonify({"result": {"exito": True, "total": len(pedidos_lista), "montoTotal": sum(p['precio'] for p in pedidos_lista), "pedidos": pedidos_lista}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marcarPagosMasivo', methods=['GET'])
def api_marcar_pagos_masivo():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    filas_str = request.args.get('arg0', '[]')
    try:
        filas = json.loads(filas_str)
        for fila in filas:
            supabase.table('pedidos').update({"estado_pago": "Pagado"}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": f"{len(filas)} pedido(s) marcado(s) como pagado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerResumenSemana', methods=['GET'])
def api_obtener_resumen_semana():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        response = supabase.table('pedidos').select('*').execute()
        pedidos = response.data
        total_pedidos = len(pedidos)
        total_ingresos = sum(float(p.get('precio', 0) or 0) for p in pedidos)
        total_pagado = sum(float(p.get('precio', 0) or 0) for p in pedidos if p.get('estado_pago') == 'Pagado')
        total_pendiente = sum(float(p.get('precio', 0) or 0) for p in pedidos if p.get('estado_pago') == 'Pendiente')
        
        return jsonify({"result": {"exito": True, "totalPedidos": total_pedidos, "totalIngresos": total_ingresos, "totalPagado": total_pagado, "totalPendiente": total_pendiente, "rangoTexto": "Semana actual", "porDia": {}}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerResumenRango', methods=['GET'])
def api_obtener_resumen_rango():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fecha_inicio, fecha_fin = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        response = supabase.table('pedidos').select('*').gte('creado_en', fecha_inicio).lte('creado_en', fecha_fin).execute()
        pedidos = response.data
        return jsonify({"result": {"exito": True, "totalPedidos": len(pedidos), "totalIngresos": sum(float(p.get('precio', 0) or 0) for p in pedidos), "totalPagado": sum(float(p.get('precio', 0) or 0) for p in pedidos if p.get('estado_pago') == 'Pagado'), "totalPendiente": sum(float(p.get('precio', 0) or 0) for p in pedidos if p.get('estado_pago') == 'Pendiente'), "rangoTexto": f"{fecha_inicio} a {fecha_fin}", "pedidos": []}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 8. APIs DE PERFIL, ZONAS Y CALCULO DE PRECIOS
# ==========================================

@app.route('/api/calcularPrecio', methods=['GET'])
def api_calcular_precio():
    if not supabase: return jsonify({"error": "Supabase no configurado"}), 500
    try:
        direccion = request.args.get('arg0', '')
        marca = request.args.get('arg1', '')
        tipo_origen = request.args.get('arg2', 'marca')
        cp = request.args.get('arg3', '')
        
        # 1. Verificar precio fijo
        if marca in MARCAS_PRECIO_FIJO:
            return jsonify({"precio": MARCAS_PRECIO_FIJO[marca], "km": 0, "origen": "Fijo", "tarifaEspecial": True})
        
        # 2. Extraer municipio de la dirección (formato esperado: "Calle, Colonia, Municipio")
        partes = direccion.split(',')
        municipio_destino = partes[-1].strip() if len(partes) >= 3 else ""
        
        # Si no se pudo extraer, intentar con el CP
        if not municipio_destino and cp:
            cp_response = supabase.table('colonias').select('municipio').eq('cp', cp).limit(1).execute()
            if cp_response.data:
                municipio_destino = cp_response.data[0]['municipio']
        
        # 3. Determinar tabla de tarifas según la marca
        tabla_tarifas = 'tarifa_premium' if marca in MARCAS_PREMIUM else 'tarifa_general'
        
        # 4. Calcular KM (⚠️ SIMULADO: Reemplaza esto con tu lógica real de Google Maps Distance Matrix si la tienes)
        km_estimado = 10 
        
        # 5. Buscar tarifa en Supabase
        response = supabase.table(tabla_tarifas).select('km, precio').eq('municipio_origen', municipio_destino).execute()
        
        if response.data:
            # Ordenar tarifas por KM ascendente
            tarifas = sorted(response.data, key=lambda x: x['km'])
            precio_encontrado = tarifas[-1]['precio'] # Precio máximo por defecto
            
            # Buscar la tarifa que corresponda al KM estimado
            for t in tarifas:
                if t['km'] >= km_estimado:
                    precio_encontrado = t['precio']
                    break
                    
            return jsonify({
                "precio": precio_encontrado, 
                "km": km_estimado, 
                "origen": municipio_destino,
                "tarifaEspecial": False
            })
        else:
            # Fallback si no se encuentra el municipio en la tabla
            return jsonify({"precio": 90, "km": km_estimado, "origen": municipio_destino or "Desconocido", "tarifaEspecial": True})
            
    except Exception as e:
        print(f"Error calcularPrecio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/getMunicipios', methods=['GET'])
def api_get_municipios():
    if not supabase: return jsonify({"result": []}), 500
    try:
        # Consultamos la tabla 'colonias' que acabamos de crear
        response = supabase.table('colonias').select('municipio').execute()
        municipios = sorted(list(set([row['municipio'] for row in response.data if row.get('municipio')])))
        return jsonify({"result": municipios})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getCPs', methods=['GET'])
def api_get_cps():
    if not supabase: return jsonify({"result": []}), 500
    municipio = request.args.get('arg0', '')
    try:
        response = supabase.table('colonias').select('cp').eq('municipio', municipio).execute()
        cps = sorted(list(set([row['cp'] for row in response.data if row.get('cp')])))
        return jsonify({"result": cps})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getColonias', methods=['GET'])
def api_get_colonias():
    if not supabase: return jsonify({"result": []}), 500
    cp = request.args.get('arg0', '')
    try:
        response = supabase.table('colonias').select('colonia').eq('cp', cp).execute()
        colonias = sorted(list(set([row['colonia'] for row in response.data if row.get('colonia')])))
        return jsonify({"result": colonias})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerPerfilMarca', methods=['GET'])
def api_obtener_perfil():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    marca = request.args.get('arg0', '')
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data and len(response.data) > 0:
            row = response.data[0]
            return jsonify({"result": {"exito": True, "marca": row.get('nombre'), "municipio": row.get('municipio'), "colonia": row.get('colonia'), "calle": row.get('calle'), "telefono": row.get('telefono'), "logo": row.get('logo_url') or "", "slogan": row.get('slogan') or ""}})
        return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getProveedoresFrecuentes', methods=['GET'])
def api_get_proveedores():
    if not supabase: return jsonify({"result": []}), 500
    marca = request.args.get('arg0', '')
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": []})
        response = supabase.table('proveedores').select('*').eq('marca_id', marca_response.data[0]['id']).order('nombre').execute()
        return jsonify({"result": response.data})
    except Exception as e:
        return jsonify({"result": []})

@app.route('/api/getDireccionTienda', methods=['GET'])
def api_get_direccion_tienda():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    marca = request.args.get('arg0', '')
    try:
        response = supabase.table('marcas').select('calle, colonia, municipio').ilike('nombre', marca).execute()
        if response.data:
            row = response.data[0]
            return jsonify({"result": {"exito": True, "direccionCompleta": f"{row.get('calle', '')}, {row.get('colonia', '')}, {row.get('municipio', '')}, Jalisco, Mexico"}})
        return jsonify({"result": {"exito": False}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getDestinatariosFrecuentes', methods=['GET'])
def api_get_destinatarios():
    if not supabase: return jsonify({"result": []}), 500
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

@app.route('/api/obtenerUrlApp', methods=['GET'])
def api_obtener_url():
    return jsonify({"result": request.host_url})

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('.', 'service-worker.js', mimetype='application/javascript')

# ==========================================
# 9. INICIAR SERVIDOR
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 LUNA DELIVERY BACKEND")
    print(f"📍 Puerto: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)