import logging
import toml
from sqlalchemy import create_engine, text
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from datetime import datetime
import pytz

# Configurar logging para ver errores en consola
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# 1. LEER SECRETOS
try:
    with open(".streamlit/secrets.toml", "r", encoding="utf-8") as f:
        secrets = toml.load(f)
        
    DB_URI = secrets["DB_URI"]
    # NOTA: En el proximo paso le diremos al usuario que agregue esto en secrets.toml
    if "TELEGRAM_TOKEN" not in secrets:
        print("ATENCION: Falta agregar TELEGRAM_TOKEN y TELEGRAM_USER_ID en .streamlit/secrets.toml")
        TELEGRAM_TOKEN = "AQUI_IRÁ_EL_TOKEN"
        ALLOWED_USER_ID = 0
    else:
        TELEGRAM_TOKEN = secrets["TELEGRAM_TOKEN"]
        ALLOWED_USER_ID = int(secrets["TELEGRAM_USER_ID"])
        
    # Leemos a qué usuario de la app le corresponden los gastos enviados desde este ID de Telegram
    USUARIO_APP = secrets.get("TELEGRAM_APP_USER", "Usuario")
    
except Exception as e:
    print(f"Error cargando secrets.toml: {e}")
    exit(1)

# Conectar a la BD
engine = create_engine(DB_URI)

# Diccionarios mapeados igual que en la app
dict_cuentas = {"Efectivo": 1, "Transferencia": 2, "MercadoPago": 3, "Débito": 4, "Crédito": 5}
dict_categorias = {
    "Sueldo": 1, "Rendimientos": 2, "Ventas": 3, "Otros Ingresos": 4,
    "Supermercado": 5, "Alquiler": 6, "Gimnasio": 7, "Ocio": 8, 
    "Entretenimiento": 9, "Gustitos": 10, "Bolucompras": 11,
    "Otros Egresos": 12, "Inversiones": 13, "Verdulería": 14, "Indumentaria": 15,
    "Servicios": 16, "Alimentos": 17, "Deudas": 18
}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # SEGURIDAD: Solo responder al dueño
    user_id = update.effective_user.id
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ No estás autorizado para usar este bot.")
        return

    texto = update.message.text.strip().lower()
    
    # Intentar parsear el mensaje. Formato esperado: "monto categoria detalle"
    # Ej: "15000 supermercado coto" o "1500 almuerzo"
    partes = texto.split(" ", 1)
    
    if len(partes) < 2:
        await update.message.reply_text("❌ Formato incorrecto. Usá: `monto detalle`\nEjemplo: `15000 supermercado`", parse_mode='Markdown')
        return
        
    monto_str = partes[0]
    detalle_completo = partes[1].strip()
    
    try:
        monto = float(monto_str.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ El primer dato debe ser un número (el monto).")
        return
        
    # Intentar adivinar la categoría basada en la primera palabra del detalle
    primera_palabra = detalle_completo.split(" ")[0].capitalize()
    
    if primera_palabra in dict_categorias:
        categoria = primera_palabra
        detalle = detalle_completo.replace(detalle_completo.split(" ")[0], "", 1).strip()
    else:
        # Categoría por defecto si no se especificó o no existe
        categoria = "Otros Egresos" 
        detalle = detalle_completo

    # Parámetros por defecto para Telegram
    # Como acordamos, MercadoPago será la cuenta por defecto
    cuenta = "MercadoPago"
    
    id_cuenta = dict_cuentas[cuenta]
    id_categoria = dict_categorias[categoria]
    
    zona_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    fecha_hoy = datetime.now(zona_ar).date()
    
    # Inyectar en SQL
    query_insert = text("""
        INSERT INTO Fact_Transacciones (Fecha, ID_Cuenta_Origen, ID_Categoria, Monto, Detalle, usuario)
        VALUES (:fecha, :id_cuenta, :id_categoria, :monto, :detalle, :usuario_actual)
    """)
    
    try:
        with engine.connect() as conn:
            conn.execute(query_insert, {
                "fecha": fecha_hoy,
                "id_cuenta": id_cuenta, 
                "id_categoria": id_categoria,
                "monto": monto,
                "detalle": detalle if detalle else categoria,
                "usuario_actual": USUARIO_APP
            })
            conn.commit()
            
        await update.message.reply_text(f"✅ Gasto guardado!\nMonto: ${monto}\nCategoría: {categoria}\nCuenta: {cuenta}")
    except Exception as e:
        logging.error(f"Error SQL: {e}")
        await update.message.reply_text("❌ Hubo un error al guardar en la base de datos.")

def main():
    if TELEGRAM_TOKEN == "AQUI_IRÁ_EL_TOKEN":
        print("Falta configurar el Token en secrets.toml")
        return
        
    # Inicializar bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Responder a cualquier mensaje de texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot de Finanzas en funcionamiento. Esperando mensajes...")
    
    # Iniciar "Polling" (escucha activa)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
