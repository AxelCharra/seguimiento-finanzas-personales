import random
import calendar
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import streamlit as st

# 1. Conexión a DB
DB_URI = st.secrets["DB_URI"]
engine = create_engine(DB_URI)
usuario_objetivo = "Usuario"

# 2. Diccionarios (Actualizados con Servicios)
dict_cuentas = {"Efectivo": 1, "Transferencia": 2, "MercadoPago": 3, "Débito": 4, "Crédito": 5}
# Mapeo rápido de categorías
CAT_SUELDO = 1
CAT_OTROS_ING = 4
CAT_SUPER = 5
CAT_ALQUILER = 6
CAT_GYM = 7
CAT_OCIO = 8
CAT_ENTRETENIMIENTO = 9
CAT_GUSTITOS = 10
CAT_OTROS_EGR = 12
CAT_INVERSIONES = 13
CAT_INDUMENTARIA = 15
CAT_SERVICIOS = 16

transacciones = []

# 3. Lógica de generación mes a mes (Ene 2025 a Mar 2026)
meses_totales = 15

print("Fabricando el flujo de fondos realista...")

for mes_idx in range(meses_totales):
    año_actual = 2025 + (mes_idx // 12)
    mes_actual = (mes_idx % 12) + 1
    dias_en_mes = calendar.monthrange(año_actual, mes_actual)[1]
    
    # Factor de inflación ficticio (aprox 3.5% mensual acumulativo)
    inflacion = 1.0 + (mes_idx * 0.035)
    
    # --- INGRESOS ---
    # Sueldo (Días 1 al 5)
    dia_cobro = random.randint(1, 5)
    fecha_sueldo = datetime(año_actual, mes_actual, dia_cobro).date()
    sueldo_base = random.randint(1200000, 1500000) * inflacion
    transacciones.append({"fecha": fecha_sueldo, "id_cuenta": 2, "id_categoria": CAT_SUELDO, "monto": sueldo_base, "detalle": "Sueldo mensual", "usuario_actual": usuario_objetivo})
    
    # Aguinaldo (Junio y Diciembre)
    if mes_actual in [6, 12]:
        transacciones.append({"fecha": fecha_sueldo, "id_cuenta": 2, "id_categoria": CAT_SUELDO, "monto": sueldo_base / 2, "detalle": "Medio Aguinaldo", "usuario_actual": usuario_objetivo})
        
    # Freelance / Changas digitales (No todos los meses, probabilidad del 70%)
    if random.random() < 0.7:
        fecha_free = datetime(año_actual, mes_actual, random.randint(10, 25)).date()
        monto_free = random.randint(200000, 350000) * inflacion
        transacciones.append({"fecha": fecha_free, "id_cuenta": 3, "id_categoria": CAT_OTROS_ING, "monto": monto_free, "detalle": "Ingreso Freelance", "usuario_actual": usuario_objetivo})

    # --- GASTOS FIJOS (Principios de mes) ---
    # Inversión automática (Días 1 al 5)
    monto_inv = random.randint(200000, 400000) * inflacion
    transacciones.append({"fecha": fecha_sueldo + timedelta(days=1), "id_cuenta": 2, "id_categoria": CAT_INVERSIONES, "monto": monto_inv, "detalle": "Dólar MEP / CEDEARs", "usuario_actual": usuario_objetivo})
    
    # Alquiler y Expensas
    fecha_alq = datetime(año_actual, mes_actual, random.randint(1, 10)).date()
    monto_alq = random.randint(450000, 580000) * inflacion
    transacciones.append({"fecha": fecha_alq, "id_cuenta": 2, "id_categoria": CAT_ALQUILER, "monto": monto_alq, "detalle": "Alquiler + Expensas", "usuario_actual": usuario_objetivo})

    # Servicios
    fecha_serv = datetime(año_actual, mes_actual, random.randint(5, 15)).date()
    monto_serv = random.randint(90000, 140000) * inflacion
    transacciones.append({"fecha": fecha_serv, "id_cuenta": 4, "id_categoria": CAT_SERVICIOS, "monto": monto_serv, "detalle": "Luz, Internet, Celular", "usuario_actual": usuario_objetivo})

    # Gimnasio
    fecha_gym = datetime(año_actual, mes_actual, random.randint(1, 10)).date()
    monto_gym = random.randint(35000, 60000) * inflacion
    transacciones.append({"fecha": fecha_gym, "id_cuenta": 4, "id_categoria": CAT_GYM, "monto": monto_gym, "detalle": "Cuota Gimnasio", "usuario_actual": usuario_objetivo})

    # --- GASTOS VARIABLES ---
    # Supermercado (3 a 4 veces)
    for _ in range(random.randint(3, 4)):
        fecha_super = datetime(año_actual, mes_actual, random.randint(1, dias_en_mes)).date()
        monto_super = random.randint(70000, 110000) * inflacion
        transacciones.append({"fecha": fecha_super, "id_cuenta": 4, "id_categoria": CAT_SUPER, "monto": monto_super, "detalle": "Compra Supermercado", "usuario_actual": usuario_objetivo})
        
    # Transporte (Lo metemos en Otros Egresos) - 2 a 4 cargas
    for _ in range(random.randint(2, 4)):
        fecha_transp = datetime(año_actual, mes_actual, random.randint(1, dias_en_mes)).date()
        monto_transp = random.randint(30000, 45000) * inflacion
        transacciones.append({"fecha": fecha_transp, "id_cuenta": 3, "id_categoria": CAT_OTROS_EGR, "monto": monto_transp, "detalle": "Transporte / Nafta", "usuario_actual": usuario_objetivo})

    # Ocio y Gustitos (Fines de semana)
    for _ in range(random.randint(6, 8)):
        # Forzamos días típicos de finde (aprox)
        dia_finde = random.choice([5, 6, 12, 13, 19, 20, 26, 27])
        if dia_finde <= dias_en_mes:
            fecha_ocio = datetime(año_actual, mes_actual, dia_finde).date()
            monto_ocio = random.randint(25000, 40000) * inflacion
            cat_ocio = random.choice([CAT_OCIO, CAT_ENTRETENIMIENTO, CAT_GUSTITOS])
            transacciones.append({"fecha": fecha_ocio, "id_cuenta": 3, "id_categoria": cat_ocio, "monto": monto_ocio, "detalle": "Salida / Delivery", "usuario_actual": usuario_objetivo})

    # Indumentaria (Compras cada un par de meses)
    if random.random() > 0.6:
        fecha_ropa = datetime(año_actual, mes_actual, random.randint(10, 25)).date()
        monto_ropa = random.randint(80000, 150000) * inflacion
        detalle_ropa = random.choice(["Outfit temporada", "Zapatillas de entrenamiento", "Ropa de diseño"])
        transacciones.append({"fecha": fecha_ropa, "id_cuenta": 5, "id_categoria": CAT_INDUMENTARIA, "monto": monto_ropa, "detalle": detalle_ropa, "usuario_actual": usuario_objetivo})

# 4. Inyección masiva a PostgreSQL
print(f"Inyectando {len(transacciones)} registros calibrados en la cuenta de '{usuario_objetivo}'...")
query_insert = text("""
    INSERT INTO Fact_Transacciones (Fecha, ID_Cuenta_Origen, ID_Categoria, Monto, Detalle, usuario)
    VALUES (:fecha, :id_cuenta, :id_categoria, :monto, :detalle, :usuario_actual)
""")

try:
    with engine.connect() as conn:
        conn.execute(query_insert, transacciones)
        conn.commit()
    print("¡Éxito total! Perfil financiero creado con precisión de relojero.")
except Exception as e:
    print(f"Error al inyectar: {e}")