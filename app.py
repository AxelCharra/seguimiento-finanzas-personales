import streamlit as st
import pandas as pd
import plotly.express as px
import extra_streamlit_components as stx
import datetime
from sqlalchemy import create_engine, text
import time

# --- FUNCIÓN TRADUCTORA DE FORMATO ---
def formato_ars(numero):
    # Toma el numero, lo formatea a US (1,234.56) y luego invierte los signos
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- 1. CONFIGURACIÓN DE STREAMLIT ---
st.set_page_config(page_title="Mis Finanzas", page_icon="💰", layout="wide")

# --- 1.1. CONFIGURACIÓN DE LA BASE DE DATOS ---
DB_URI = st.secrets["DB_URI"]
engine = create_engine(DB_URI)

# --- 2. Diccionario
dict_cuentas = {"Efectivo": 1, "Transferencia": 2, "MercadoPago": 3, "Débito": 4, "Crédito": 5}
dict_categorias = {
    "Sueldo": 1, "Rendimientos": 2, "Ventas": 3, "Otros Ingresos": 4,
    "Supermercado": 5, "Alquiler": 6, "Gimnasio": 7, "Ocio": 8, 
    "Entretenimiento": 9, "Gustitos": 10, "Bolucompras": 11,
    "Otros Egresos": 12, "Inversiones": 13, "Verdulería": 14, "Indumentaria": 15,
    "Servicios": 16, "Alimentos": 17
}

# --- 3. SISTEMA DE LOGIN (GATEKEEPER OPTIMIZADO) ---
cookie_manager = stx.CookieManager()

# Solo leemos la cookie del usuario
usuario_cookie = cookie_manager.get(cookie="usuario_finanzas")

# Si la cookie existe y tiene un nombre, automáticamente está logueado
if usuario_cookie is not None and usuario_cookie != "":
    st.session_state['logeado'] = True
    st.session_state['usuario_actual'] = usuario_cookie

if 'logeado' not in st.session_state or not st.session_state['logeado']:
    # Creamos las columnas primero
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Usamos Markdown con HTML para forzar el centrado
        st.markdown("<h2 style='text-align: center;'>🔒 Acceso Restringido</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #FF4B4B;'>Por favor, iniciá sesión para ver tus Finanzas.</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Entrar")
            
            if submit:
                if usuario in st.secrets["credenciales"] and st.secrets["credenciales"][usuario] == password:
                    st.session_state['logeado'] = True
                    st.session_state['usuario_actual'] = usuario 
                    
                    vencimiento = datetime.datetime.now() + datetime.timedelta(days=30)
                    
                    # MAGIA: Usamos UNA SOLA cookie que cumple ambas funciones
                    cookie_manager.set("usuario_finanzas", usuario, expires_at=vencimiento) 
                    
                    st.success(f"¡Bienvenido/a {usuario}! Cargando tus finanzas...")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    
    st.stop() # 🛑 El escudo final

# --- APP PRINCIPAL ---

st.sidebar.title(f"Bienvenido/a 👋 {st.session_state['usuario_actual'].capitalize()}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['logeado'] = False
    cookie_manager.delete("usuario_finanzas") # Borramos la única cookie al salir
    st.rerun()

st.title("💸 Seguimiento de Finanzas Personales")

st.divider() 

# --- 4. FORMULARIO DE CARGA ---
st.subheader("Carga una nueva transacción")
opcion_seleccionada = st.radio("Tipo de Movimiento", ["🔴 Egreso", "🟢 Ingreso"], horizontal=True)
tipo_movimiento = "Ingreso" if "Ingreso" in opcion_seleccionada else "Egreso"

if tipo_movimiento == "Ingreso":
    st.markdown("<h4 style='color: #28a745;'>📈 Registrando un Ingreso</h4>", unsafe_allow_html=True)
    categorias_disponibles = ["Sueldo", "Rendimientos", "Ventas", "Otros Ingresos"]
else:
    st.markdown("<h4 style='color: #dc3545;'>📉 Registrando un Egreso</h4>", unsafe_allow_html=True)
    categorias_disponibles = ["Supermercado", "Alimentos", "Alquiler", "Servicios", "Gimnasio", "Ocio", "Entretenimiento", "Gustitos", "Bolucompras", "Otros Egresos", "Inversiones", "Verdulería", "Indumentaria"]

with st.form("formulario_transacciones", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        # 1. Definimos el huso horario de Argentina (UTC-3)
        zona_ar = datetime.timezone(datetime.timedelta(hours=-3))
        # 2. Calculamos el "hoy" pero forzando esa zona horaria
        hoy_arg = datetime.datetime.now(zona_ar).date()
        # 3. Le pasamos ese "hoy_arg" como valor (value) por defecto al calendario
        fecha = st.date_input("Fecha de la transacción", value=hoy_arg, format="DD/MM/YYYY")
        cuenta = st.selectbox("Cuenta", list(dict_cuentas.keys()))
        categoria = st.selectbox("Categoría", categorias_disponibles)
    with col2:
        monto = st.number_input("Monto ($)", min_value=0.0, value=None, format="%.2f")
        detalle = st.text_input("Detalle (Opcional)", placeholder="Ej: Cena con amigos")
    boton_guardar = st.form_submit_button("Guardar Transacción")

# --- 5. LÓGICA DE INYECCIÓN A SQL ---
if boton_guardar:
    if monto is None or monto <= 0:
        st.error("Error: Por favor, ingresá un monto mayor a cero.")
    else:
        id_cuenta = dict_cuentas[cuenta]
        id_categoria = dict_categorias[categoria]
        
        query_insert = text("""
            INSERT INTO Fact_Transacciones (Fecha, ID_Cuenta_Origen, ID_Categoria, Monto, Detalle, usuario)
            VALUES (:fecha, :id_cuenta, :id_categoria, :monto, :detalle, :usuario_actual)
        """)
        try:
            with engine.connect() as conn:
                conn.execute(query_insert, {
                    "fecha": fecha, "id_cuenta": id_cuenta, "id_categoria": id_categoria, 
                    "monto": monto, "detalle": detalle, "usuario_actual": st.session_state['usuario_actual']
                })
                conn.commit()
            st.success(f"¡Éxito! Transacción guardada en tu cuenta.")
        except Exception as e:
            st.error(f"Error al guardar: {e}")

st.divider()

# --- 6. DASHBOARD ---
st.subheader("📊 Resumen Financiero")

query_lectura = text("""
    SELECT 
        f.ID_Transaccion AS "ID", f.Fecha AS "Fecha", c.Tipo_Movimiento AS "Tipo_Movimiento", 
        c.Categoria_Principal AS "Categoria", cu.Nombre_Cuenta AS "Cuenta", 
        f.Monto AS "Monto", f.Detalle AS "Detalle"
    FROM Fact_Transacciones f
    JOIN Dim_Categorias c ON f.ID_Categoria = c.ID_Categoria
    LEFT JOIN Dim_Cuentas cu ON f.ID_Cuenta_Origen = cu.ID_Cuenta
    WHERE f.usuario = :usuario_actual
    ORDER BY f.Fecha DESC
""")

try:
    df_historial = pd.read_sql(query_lectura, engine, params={"usuario_actual": st.session_state['usuario_actual']})
    
    if not df_historial.empty:
        df_historial["Fecha"] = pd.to_datetime(df_historial["Fecha"]).dt.date
        
        st.sidebar.header("🔍 Filtros de Análisis")
        fecha_min = df_historial["Fecha"].min()
        fecha_max = df_historial["Fecha"].max()
        rango_fechas = st.sidebar.date_input("Seleccionar período", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max, format="DD/MM/YYYY")
        
        if len(rango_fechas) == 2:
            mask = (df_historial["Fecha"] >= rango_fechas[0]) & (df_historial["Fecha"] <= rango_fechas[1])
            df_filtrado = df_historial.loc[mask]
        else:
            df_filtrado = df_historial[df_historial["Fecha"] == rango_fechas[0]]

        if not df_filtrado.empty:
            df_ingresos = df_filtrado[df_filtrado["Tipo_Movimiento"] == "Ingreso"]
            df_egresos = df_filtrado[df_filtrado["Tipo_Movimiento"] == "Egreso"]
            total_ingresos = df_ingresos["Monto"].sum()
            total_egresos = df_egresos["Monto"].sum()
            saldo_actual = total_ingresos - total_egresos

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric(label="Ingresos (Período)", value=f"${formato_ars(total_ingresos)}")
            kpi2.metric(label="Egresos (Período)", value=f"${formato_ars(total_egresos)}")
            kpi3.metric(label="Flujo de Caja", value=f"${formato_ars(saldo_actual)}")
            
            st.divider()
            st.subheader("📉 Análisis de Gastos")
            if not df_egresos.empty:
                gastos_por_categoria = df_egresos.groupby("Categoria")["Monto"].sum().reset_index()
                col_graf1, col_graf2 = st.columns(2)
                with col_graf1:
                    fig_bar = px.bar(gastos_por_categoria, x="Categoria", y="Monto", color="Categoria", title="Volumen de Gastos")
                    st.plotly_chart(fig_bar, width="stretch")
                with col_graf2:
                    fig_pie = px.pie(gastos_por_categoria, names="Categoria", values="Monto", color="Categoria", title="Distribución (%)", hole=0.4)
                    st.plotly_chart(fig_pie, width="stretch")
            else:
                st.info("No hay egresos en el período seleccionado.")

            st.divider()
            st.subheader("📝 Historial de Transacciones")
            # Le pasamos el formato argentino a la columna Monto
            st.dataframe(df_filtrado.style.format({"Monto": lambda x: f"${formato_ars(x)}"}), width="stretch")
        else:
            st.warning("No hay transacciones para el rango de fechas seleccionado.")
            
        # --- 7. PANEL DE GESTIÓN DE REGISTROS (CRUD) ---
        st.divider()
        st.subheader("⚙️ Gestión de Registros")
        
        # Creamos dos pestañas para separar la lógica
        tab_editar, tab_borrar = st.tabs(["✏️ Editar Registro", "🗑️ Eliminar Registro"])
        
       # --- PESTAÑA: EDITAR ---
        with tab_editar:
            st.markdown("Reescribí un registro completo. Ingresá el ID y los datos correctos.")
            with st.form("form_editar", clear_on_submit=True):
                st.markdown("**1. Indicá el ID a modificar:**")
                id_editar = st.number_input("ID de la transacción", min_value=1, step=1, value=None)
                
                st.markdown("**2. Ingresá los datos corregidos:**")
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    nueva_fecha = st.date_input("Nueva Fecha", format="DD/MM/YYYY")
                    nueva_cuenta = st.selectbox("Nueva Cuenta", list(dict_cuentas.keys()))
                    nueva_categoria = st.selectbox("Nueva Categoría", list(dict_categorias.keys()))
                with col_e2:
                    nuevo_monto = st.number_input("Nuevo Monto ($)", min_value=0.0, value=None, format="%.2f")
                    nuevo_detalle = st.text_input("Nuevo Detalle", placeholder="Ej: Compra corregida")
                
                btn_actualizar = st.form_submit_button("🔄 Actualizar Registro Completo")
                
                if btn_actualizar:
                    if id_editar is None or nuevo_monto is None:
                        st.error("⚠️ Por favor completá el ID y el nuevo monto como mínimo.")
                    else:
                        id_cta_nueva = dict_cuentas[nueva_cuenta]
                        id_cat_nueva = dict_categorias[nueva_categoria]
                        
                        # Expandimos el UPDATE a todas las columnas
                        query_update = text("""
                            UPDATE Fact_Transacciones 
                            SET Fecha = :fecha,
                                ID_Cuenta_Origen = :id_cuenta,
                                ID_Categoria = :id_cat, 
                                Monto = :monto,
                                Detalle = :detalle
                            WHERE ID_Transaccion = :id AND usuario = :usuario_actual
                        """)
                        try:
                            with engine.connect() as conn:
                                resultado = conn.execute(query_update, {
                                    "fecha": nueva_fecha,
                                    "id_cuenta": id_cta_nueva,
                                    "id_cat": id_cat_nueva, 
                                    "monto": nuevo_monto, 
                                    "detalle": nuevo_detalle,
                                    "id": id_editar, 
                                    "usuario_actual": st.session_state['usuario_actual']
                                })
                                conn.commit()
                                
                                if resultado.rowcount > 0:
                                    st.success(f"¡Éxito! Registro {id_editar} actualizado por completo. Recargá la página (F5).")
                                else:
                                    st.error("No se encontró ese ID o no te pertenece.")
                        except Exception as e:
                            st.error(f"Error al actualizar: {e}")

        # --- PESTAÑA: BORRAR (Tu código original blindado) ---
        with tab_borrar:
            col_b1, col_b2 = st.columns([3, 1])
            with col_b1:
                id_a_borrar = st.number_input("Ingresá el ID a eliminar:", min_value=1, step=1, value=None)
            with col_b2:
                st.write("") 
                st.write("")
                btn_eliminar = st.button("🚨 Eliminar")
                
            if btn_eliminar:
                if id_a_borrar is None:
                    st.error("Ingresá un ID válido.")
                else:
                    query_delete = text("DELETE FROM Fact_Transacciones WHERE ID_Transaccion = :id AND usuario = :usuario_actual")
                    try:
                        with engine.connect() as conn:
                            resultado = conn.execute(query_delete, {"id": id_a_borrar, "usuario_actual": st.session_state['usuario_actual']})
                            conn.commit()
                            
                            if resultado.rowcount > 0:
                                st.success(f"¡Registro {id_a_borrar} eliminado! Recargá la página (F5).")
                            else:
                                st.error("No se encontró ese ID o no tenés permiso para borrarlo.")
                    except Exception as e:
                        st.error(f"Error al intentar borrar: {e}")
    else:
        st.info(f"Hola {st.session_state['usuario_actual'].capitalize()}, aún no tenés transacciones. ¡Cargá la primera!")

except Exception as e:
    st.error(f"No se pudo conectar a la base de datos. Detalles: {e}")