import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

# --- 3. CONFIGURACIÓN DE STREAMLIT (Debe ser el primer comando siempre) ---
st.set_page_config(page_title="Mis Finanzas", page_icon="💰", layout="wide")

# --- 1. CONFIGURACIÓN DE LA BASE DE DATOS (EL PUENTE) ---
DB_URI = st.secrets["DB_URI"]
engine = create_engine(DB_URI)

# --- 2. LOS DICCIONARIOS TRADUCTORES ---
dict_cuentas = {
    "Efectivo": 1, "Transferencia": 2, "MercadoPago": 3, 
    "Débito": 4, "Crédito": 5
}

dict_categorias = {
    "Sueldo": 1, "Rendimientos": 2, "Ventas": 3, "Otros Ingresos": 4,
    "Supermercado": 5, "Alquiler": 6, "Gimnasio": 7, "Ocio": 8, 
    "Entretenimiento": 9, "Gustitos": 10, "Bolucompras": 11,
    "Otros Egresos": 12, "Inversiones": 13, "Verdulería": 14, "Indumentaria": 15
}

# --- SISTEMA DE LOGIN (GATEKEEPER) ---
# Inicializamos la "libretita" de Streamlit
if "logeado" not in st.session_state:
    st.session_state.logeado = False

# PANTALLA DE ACCESO
if not st.session_state.logeado:
    st.title("🔒 Acceso Restringido")
    st.subheader("Por favor, iniciá sesión para continuar")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Entrar")
            
            if btn_login:
                if usuario == st.secrets["admin_user"] and password == st.secrets["admin_password"]:
                    st.session_state.logeado = True
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")

# --- APP PRINCIPAL (SOLO SE EJECUTA SI EL USUARIO ESTÁ LOGEADO) ---
else:
    # Botón de cierre de sesión en la barra lateral
    st.sidebar.title("Bienvenido/a 👋")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logeado = False
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
        categorias_disponibles = ["Supermercado", "Alquiler", "Gimnasio", "Ocio", "Entretenimiento", "Gustitos", "Bolucompras", "Otros Egresos", "Inversiones", "Verdulería", "Indumentaria"]

    with st.form("formulario_transacciones", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            fecha = st.date_input("Fecha de la transacción", format="DD/MM/YYYY")
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
                INSERT INTO Fact_Transacciones (Fecha, ID_Cuenta_Origen, ID_Categoria, Monto, Detalle)
                VALUES (:fecha, :id_cuenta, :id_categoria, :monto, :detalle)
            """)
            
            try:
                with engine.connect() as conn:
                    conn.execute(query_insert, {
                        "fecha": fecha, 
                        "id_cuenta": id_cuenta, 
                        "id_categoria": id_categoria, 
                        "monto": monto, 
                        "detalle": detalle
                    })
                    conn.commit()
                st.success(f"¡Éxito! Transacción guardada directamente en PostgreSQL.")
            except Exception as e:
                st.error(f"Error al guardar en la base de datos: {e}")

    st.divider()

    # --- 6. DASHBOARD (LEYENDO DESDE SQL) ---
    st.subheader("📊 Resumen Financiero")

    query_lectura = """
        SELECT 
            f.ID_Transaccion AS "ID",
            f.Fecha AS "Fecha", 
            c.Tipo_Movimiento AS "Tipo_Movimiento", 
            c.Categoria_Principal AS "Categoria", 
            cu.Nombre_Cuenta AS "Cuenta", 
            f.Monto AS "Monto", 
            f.Detalle AS "Detalle"
        FROM Fact_Transacciones f
        JOIN Dim_Categorias c ON f.ID_Categoria = c.ID_Categoria
        LEFT JOIN Dim_Cuentas cu ON f.ID_Cuenta_Origen = cu.ID_Cuenta
        ORDER BY f.Fecha DESC
    """

    try:
        df_historial = pd.read_sql(query_lectura, engine)
        
        if not df_historial.empty:
            df_historial["Fecha"] = pd.to_datetime(df_historial["Fecha"]).dt.date
            
            st.sidebar.header("🔍 Filtros de Análisis")
            
            fecha_min = df_historial["Fecha"].min()
            fecha_max = df_historial["Fecha"].max()
            
            rango_fechas = st.sidebar.date_input(
                "Seleccionar período",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max,
                format="DD/MM/YYYY"
            )
            
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
                mask = (df_historial["Fecha"] >= fecha_inicio) & (df_historial["Fecha"] <= fecha_fin)
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
                kpi1.metric(label="Ingresos (Período)", value=f"${total_ingresos:,.2f}")
                kpi2.metric(label="Egresos (Período)", value=f"${total_egresos:,.2f}")
                kpi3.metric(label="Flujo de Caja", value=f"${saldo_actual:,.2f}")
                
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
                st.dataframe(df_filtrado, width="stretch")
            else:
                st.warning("No hay transacciones para el rango de fechas seleccionado.")
                
            # --- 7. ZONA DE PELIGRO (BORRAR REGISTROS) ---
            st.divider()
            st.subheader("🗑️ Gestión de Errores")
            st.info("💡 Si cargaste algo mal, buscá su número de 'ID' en la tabla de arriba y eliminalo acá.")
            
            with st.expander("Abrir panel de eliminación"):
                col_borrar1, col_borrar2 = st.columns([3, 1])
                
                with col_borrar1:
                    id_a_borrar = st.number_input("Ingresá el ID a eliminar:", min_value=1, step=1, value=None)
                
                with col_borrar2:
                    st.write("") 
                    st.write("")
                    btn_eliminar = st.button("🚨 Eliminar")
                    
                if btn_eliminar:
                    if id_a_borrar is None:
                        st.error("Ingresá un ID válido.")
                    else:
                        query_delete = text("DELETE FROM Fact_Transacciones WHERE ID_Transaccion = :id")
                        try:
                            with engine.connect() as conn:
                                conn.execute(query_delete, {"id": id_a_borrar})
                                conn.commit()
                            st.success(f"¡Registro {id_a_borrar} fulminado! Recargá la página (F5) para actualizar los saldos.")
                        except Exception as e:
                            st.error(f"Error al intentar borrar: {e}")

        else:
            st.info("La base de datos PostgreSQL está conectada, pero aún no tiene transacciones. ¡Cargá la primera!")

    except Exception as e:
        st.error(f"No se pudo conectar a PostgreSQL para leer los datos. Revisá la contraseña. Detalles: {e}")