import streamlit as st
import gspread
import pandas as pd
import json
from logic import SheetInventory

st.set_page_config(page_title="Gestión de Chapas", layout="wide")

# Conexión Segura
def conectar_google_sheets():
    try:
        info_json = st.secrets["gcp_service_account"]["json_data"]
        credentials = json.loads(info_json)
        gc = gspread.service_account_from_dict(credentials)
        return gc.open('Inventario Chapas').sheet1
    except:
        return None

# Inicialización
if 'inventory' not in st.session_state:
    st.session_state.inventory = {
        "T101 galvanizada": SheetInventory("T101 galvanizada"),
        "T101 zincalum": SheetInventory("T101 zincalum"),
        "Acanalada galvanizada": SheetInventory("Acanalada galvanizada"),
        "Acanalada zincalum": SheetInventory("Acanalada zincalum")
    }
if 'history' not in st.session_state:
    st.session_state.history = []

# --- MENÚ LATERAL ---
st.sidebar.title("Menú de Gestión")
opcion = st.sidebar.radio("Operaciones:", [
    "1. Mostrar Inventario", 
    "2. Añadir Stock", 
    "3. Tomar Material",
    "4. Deshacer Pedido",
    "5. Historial y Reporte"
])

# PASO 1: INVENTARIO
if opcion == "1. Mostrar Inventario":
    st.header("📦 Stock en Depósito")
    for name, obj in st.session_state.inventory.items():
        with st.expander(f"Ver {name}", expanded=True):
            c1, c2 = st.columns(2)
            c1.metric("Chapas (13m)", f"{obj.full_sheets_count} un.")
            c2.write(f"**Recortes Disponibles:** {obj.cuts if obj.cuts else 'Sin recortes'}")

# PASO 2: AÑADIR STOCK
elif opcion == "2. Añadir Stock":
    st.header("➕ Ingreso de Material")
    with st.form("add_form"):
        tipo_add = st.selectbox("Tipo de chapa", list(st.session_state.inventory.keys()))
        cantidad_add = st.number_input("Cantidad de chapas de 13m", min_value=1, step=1)
        if st.form_submit_button("Añadir al Inventario"):
            st.session_state.inventory[tipo_add].add_full_sheets(cantidad_add)
            st.success(f"Se agregaron {cantidad_add} chapas a {tipo_add}")

# PASO 3: TOMAR MATERIAL
elif opcion == "3. Tomar Material":
    st.header("✂️ Registro de Corte")
    st.warning("Reglas: No cortes ≥ 12m. Sobrantes < 1.50m se descartan.")
    with st.form("corte_form"):
        tipo = st.selectbox("Chapa", list(st.session_state.inventory.keys()))
        largo = st.number_input("Largo (m)", min_value=0.5, max_value=11.9, step=0.1)
        cant = st.number_input("Cantidad de piezas", min_value=1, step=1)
        if st.form_submit_button("Procesar"):
            exito, registros = st.session_state.inventory[tipo].take_material(largo, cant)
            if exito:
                for r in registros:
                    msg = f"Pieza sacada de: **{r['source']}**."
                    if r['remnant'] < 1.5 and r['remnant'] > 0:
                        msg += f" (Sobrante de {r['remnant']}m descartado)"
                    st.info(msg)
                st.session_state.history.extend(registros)
                st.success("¡Pedido registrado!")
            else:
                st.error("Stock insuficiente.")

# PASO 4: DESHACER
elif opcion == "4. Deshacer Pedido":
    st.header("↩️ Deshacer Último Movimiento")
    if st.session_state.history:
        ultimo = st.session_state.history[-1]
        st.write(f"Último registro: **{ultimo['sheet_type']}** de **{ultimo['length_requested']}m**")
        if st.button("Confirmar y Restaurar Stock"):
            st.session_state.inventory[ultimo['sheet_type']].undo_cut(ultimo['source'], ultimo['length_requested'], ultimo['remnant'])
            st.session_state.history.pop()
            st.success("Operación deshecha.")
    else:
        st.info("No hay nada para deshacer.")

# PASO 5: HISTORIAL
elif opcion == "5. Historial y Reporte":
    st.header("📜 Historial")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.table(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar CSV", csv, "historial.csv", "text/csv")


# PASO 6: SINCRONIZACIÓN MANUAL
elif opcion == "6. Sincronizar Google Sheets":
    st.header("🔄 Sincronización de Datos")
    st.info("Desde aquí puedes forzar la carga de datos desde la planilla o guardar el estado actual.")
    
    col_sync1, col_sync2 = st.columns(2)
    
    with col_sync1:
        if st.button("📥 Cargar desde Sheets", help="Trae el stock actual de la planilla de Google"):
            wks = conectar_google_sheets()
            if wks:
                data = wks.get_all_records()
                for row in data:
                    nombre = row.get('TIPO_CHAPA')
                    if nombre in st.session_state.inventory:
                        obj = st.session_state.inventory[nombre]
                        obj.full_sheets_count = int(row.get('CHAPAS_COMPLETAS', 0))
                        cuts_str = str(row.get('RECORTES', ""))
                        # Limpiamos y convertimos los recortes
                        obj.cuts = [float(x.strip()) for x in cuts_str.split(',') if x.strip()]
                st.success("✅ Datos cargados correctamente.")
                st.rerun() # Refresca la app para mostrar los nuevos números

    with col_sync2:
        if st.button("📤 Guardar en Sheets", help="Sube el stock actual a la planilla de Google"):
            wks = conectar_google_sheets()
            if wks:
                # Preparamos la cabecera y las filas
                rows = [["TIPO_CHAPA", "CHAPAS_COMPLETAS", "RECORTES"]]
                for name, obj in st.session_state.inventory.items():
                    cuts_str = ",".join(map(str, obj.cuts))
                    rows.append([name, obj.full_sheets_count, cuts_str])
                
                # Limpiamos la hoja y subimos todo de nuevo
                wks.clear()
                wks.update('A1', rows)
                st.success("💾 Datos guardados en la nube.")
