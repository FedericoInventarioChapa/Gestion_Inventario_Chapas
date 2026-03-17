import streamlit as st
import gspread
import pandas as pd
import json
from logic import SheetInventory

st.set_page_config(page_title="Gestión de Chapas", layout="wide")

def obtener_contactos_sheets():
    try:
        doc = conectar_google_sheets()
        if doc:
            # Intentamos abrir la pestaña 'Contactos'
            wks_contactos = doc.worksheet('Contactos')
            datos = wks_contactos.get_all_records()
            # Convertimos a un diccionario {Nombre: Telefono}
            return {str(fila['NOMBRE']): str(fila['TELEFONO']) for fila in datos if fila['NOMBRE']}
    except Exception as e:
        st.error(f"No se pudo cargar la agenda: {e}")
    return {"Sin Contactos": ""}

# --- CONEXIÓN SEGURA ---
def conectar_google_sheets():
    try:
        info_json = st.secrets["gcp_service_account"]["json_data"]
        credentials = json.loads(info_json)
        gc = gspread.service_account_from_dict(credentials)
        return gc.open('Inventario Chapas')
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- FUNCIONES DE GUARDADO AUTOMÁTICO ---
def guardar_stock_actual():
    doc = conectar_google_sheets()
    if doc:
        wks = doc.sheet1
        rows = [["TIPO_CHAPA", "CHAPAS_COMPLETAS", "RECORTES"]]
        for name, obj in st.session_state.inventory.items():
            cuts_str = ",".join(map(str, obj.cuts))
            rows.append([name, obj.full_sheets_count, cuts_str])
        
        wks.clear()
        wks.update('A1', rows)

def registrar_en_historial_sheets(registros):
    try:
        doc = conectar_google_sheets()
        if doc:
            try:
                wks_historial = doc.worksheet('Historial')
            except:
                wks_historial = doc.add_worksheet(title="Historial", rows="1000", cols="10")
                wks_historial.append_row(["Fecha", "Cliente", "Chapa", "Largo", "Origen", "Sobrante"])

            filas_nuevas = []
            for r in registros:
                filas_nuevas.append([
                    r['timestamp'], 
                    r.get('cliente', 'S/N'), 
                    r['sheet_type'], 
                    r['length_requested'], 
                    r['source'], 
                    r['remnant']
                ])
            wks_historial.append_rows(filas_nuevas)
    except Exception as e:
        st.error(f"Error al guardar historial: {e}")

# --- INICIALIZACIÓN ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = {
        "T101 galvanizada": SheetInventory("T101 galvanizada"),
        "T101 zincalum": SheetInventory("T101 zincalum"),
        "Acanalada galvanizada": SheetInventory("Acanalada galvanizada"),
        "Acanalada zincalum": SheetInventory("Acanalada zincalum")
    }
if 'history' not in st.session_state:
    st.session_state.history = []

opcion = st.sidebar.radio("Operaciones:", [
    "1. Mostrar Inventario", 
    "2. Añadir Stock", 
    "3. Tomar Material",
    "4. Deshacer Pedido",
    "5. Historial y Reporte",
    "6. Sincronizar Google Sheets",
    "7. Buscador de Retazos"  # <-- Nueva opción añadida
])

# PASO 1: INVENTARIO con Alertas Visuales
if opcion == "1. Mostrar Inventario":
    st.header("📦 Stock en Depósito")
    
    for name, obj in st.session_state.inventory.items():
        # Lógica del semáforo
        cantidad = obj.full_sheets_count
        if cantidad <= 2:
            estado = "🚨 CRÍTICO"
            color_delta = "inverse"
        elif cantidad <= 5:
            estado = "⚠️ BAJO"
            color_delta = "normal"
        else:
            estado = "✅ OK"
            color_delta = "off"

        with st.expander(f"Ver {name}", expanded=True):
            col1, col2, col3 = st.columns([1, 1, 2])
            
            # Métrica principal con indicador de estado
            col1.metric("Chapas (13m)", f"{cantidad} un.", delta=estado, delta_color=color_delta)
            
            # Resumen de recortes
            clean_cuts = [round(c, 2) for c in obj.cuts]
            col2.metric("Recortes", f"{len(clean_cuts)} pzs")
            
            # Lista detallada
            col3.write(f"**Medidas disponibles (m):**")
            if clean_cuts:
                st.info(", ".join(map(str, sorted(clean_cuts, reverse=True))))
            else:
                st.caption("No hay recortes disponibles.")
            
# PASO 2: AÑADIR STOCK
elif opcion == "2. Añadir Stock":
    st.header("➕ Ingreso de Material")
    with st.form("add_form"):
        tipo_add = st.selectbox("Tipo de chapa", list(st.session_state.inventory.keys()))
        cantidad_add = st.number_input("Cantidad de chapas de 13m", min_value=1, step=1)
        if st.form_submit_button("Añadir al Inventario"):
            st.session_state.inventory[tipo_add].add_full_sheets(cantidad_add)
            guardar_stock_actual() 
            st.success(f"Se agregaron {cantidad_add} chapas a {tipo_add} y se guardó en la nube.")

# PASO 3: TOMAR MATERIAL (Versión Limpia)
elif opcion == "3. Tomar Material":
    st.header("✂️ Registro de Corte")
    st.warning("⚠️ Regla: Sobrantes menores a 1.50m serán bloqueados o descartados.")
    
    with st.form("corte_form"):
        cliente = st.text_input("Nombre del Cliente / Orden #", placeholder="Ej: Juan Pérez")
        tipo = st.selectbox("Chapa", list(st.session_state.inventory.keys()))
        largo = st.number_input("Largo del corte (m)", min_value=0.5, max_value=11.5, step=0.1)
        cant = st.number_input("Cantidad de piezas", min_value=1, step=1)
        
        if st.form_submit_button("Procesar y Generar Orden"):
            if not cliente:
                st.error("Por favor, ingresa el nombre del cliente.")
            else:
                exito, registros = st.session_state.inventory[tipo].take_material(largo, cant)
                if exito:
                    for r in registros:
                        r['cliente'] = cliente
                    
                    st.session_state.history.extend(registros)
                    registrar_en_historial_sheets(registros)
                    guardar_stock_actual()

                    st.success(f"✅ Pedido registrado para {cliente}")
                    
                    # --- HOJA DE CORTE VISUAL EN PANTALLA ---
                    st.markdown("### 📝 Instrucciones para el Operario")
                    resumen_texto = f"ORDEN: {cliente} | CHAPA: {tipo}\n"
                    resumen_texto += "="*35 + "\n"

                    for i, r in enumerate(registros):
                        origen = r['source']
                        # Calculamos el largo de donde tiene que sacar la pieza
                        largo_original = round(r['length_requested'] + r['remnant'], 2) if origen == 'Recorte' else 13.0
                        
                        detalle = f"PIEZA {i+1}: Cortar a {largo}m\n📍 BUSCAR EN: {origen} de {largo_original}m\n"
                        st.info(detalle)
                        resumen_texto += detalle + "\n"
                    
                    # El cuadro de texto para copiar rápido si hiciera falta
                    st.code(resumen_texto, language="text")
                else:
                    if registros and "error" in registros[0]:
                        st.error(registros[0]["error"])
                    else:
                        st.error("No hay stock suficiente que cumpla la regla de los 1.50m.")
# PASO 4: DESHACER
elif opcion == "4. Deshacer Pedido":
    st.header("↩️ Deshacer Último Movimiento")
    if st.session_state.history:
        ultimo = st.session_state.history[-1]
        st.write(f"Último registro: **{ultimo['sheet_type']}** de **{ultimo['length_requested']}m** para **{ultimo.get('cliente','S/N')}**")
        if st.button("Confirmar y Restaurar Stock"):
            st.session_state.inventory[ultimo['sheet_type']].undo_cut(ultimo['source'], ultimo['length_requested'], ultimo['remnant'])
            st.session_state.history.pop()
            guardar_stock_actual() 
            st.success("Operación deshecha y stock restaurado.")
            st.rerun()
    else:
        st.info("No hay nada para deshacer.")

# PASO 5: HISTORIAL, REPORTES Y ELIMINACIÓN
elif opcion == "5. Historial y Reporte":
    st.header("📊 Análisis y Gestión de Registros")
    
    if st.session_state.history:
        import pandas as pd
        df = pd.DataFrame(st.session_state.history)
        
        # --- MÉTRICAS (Igual que antes) ---
        col1, col2, col3 = st.columns(3)
        total_metros = df[df['success'] == True]['length_requested'].sum()
        col1.metric("Metros Cortados", f"{total_metros:.2f} m")
        col2.metric("Total Pedidos", f"{len(df)}")
        col3.metric("Chapa Estrella", df['sheet_type'].mode()[0])

        st.divider()

        tab1, tab2 = st.tabs(["📈 Gráficos", "🛠️ Gestionar Historial"])

       with tab1:
            c1, c2 = st.columns(2)
            
            with c1:
                st.write("**Ventas por Tipo (m)**")
                # Agrupamos y convertimos a DataFrame explícito para evitar el AttributeError
                chart_data = df.groupby('sheet_type')['length_requested'].sum().reset_index()
                # Usamos st.bar_chart si pie_chart falla, o forzamos el formato:
                st.dataframe(chart_data, hide_index=True) # Tabla rápida de auxilio
                try:
                    st.pie_chart(data=chart_data, themes=None, x="sheet_type", y="length_requested")
                except:
                    st.bar_chart(data=chart_data, x="sheet_type", y="length_requested")
            
            with c2:
                st.write("**Origen del Material (Cantidad)**")
                uso_data = df['source'].value_counts().reset_index()
                st.bar_chart(data=uso_data, x="source", y="count")

        with tab2:
            st.subheader("Eliminar o Corregir Pedidos")
            st.write("⚠️ Al eliminar un pedido, el material se devolverá automáticamente al stock.")
            
            # Mostramos la tabla con un índice para poder elegir
            for i, row in df.iterrows():
                with st.expander(f"Pedido #{i} - {row['cliente']} ({row['length_requested']}m de {row['sheet_type']})"):
                    col_info, col_btn = st.columns([3, 1])
                    col_info.write(f"**Origen:** {row['source']} | **Sobrante generado:** {row['remnant']}m")
                    col_info.write(f"**Fecha:** {row['timestamp']}")
                    
                    if col_btn.button("🗑️ Eliminar este pedido", key=f"del_{i}"):
                        # 1. Devolvemos el stock físicamente
                        tipo = row['sheet_type']
                        st.session_state.inventory[tipo].undo_cut(
                            row['source'], 
                            row['length_requested'], 
                            row['remnant']
                        )
                        
                        # 2. Lo borramos de la lista de Python
                        st.session_state.history.pop(i)
                        
                        # 3. Guardamos los cambios en Google Sheets (Stock y limpiar historial si fuera necesario)
                        guardar_stock_actual()
                        
                        st.success("✅ Pedido eliminado y stock restaurado.")
                        st.rerun() # Recargamos la app para que desaparezca de la lista
            
            # Botón de descarga al final
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar a Excel (CSV)", csv, "historial.csv", "text/csv")
    else:
        st.info("No hay historial para mostrar.")
        
# PASO 6: SINCRONIZACIÓN MANUAL
elif opcion == "6. Sincronizar Google Sheets":
    st.header("🔄 Sincronización Manual")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Cargar desde Sheets"):
            doc = conectar_google_sheets()
            if doc:
                data = doc.sheet1.get_all_records()
                for row in data:
                    nombre = row.get('TIPO_CHAPA')
                    if nombre in st.session_state.inventory:
                        obj = st.session_state.inventory[nombre]
                        obj.full_sheets_count = int(row.get('CHAPAS_COMPLETAS', 0))
                        cuts_str = str(row.get('RECORTES', ""))
                        obj.cuts = [float(x.strip()) for x in cuts_str.split(',') if x.strip()]
                st.success("✅ Stock cargado.")
                st.rerun()
    with col2:
        if st.button("📤 Guardar en Sheets"):
            guardar_stock_actual()
            st.success("💾 Stock guardado.")

# PASO 7: BUSCADOR DE RETAZOS
elif opcion == "7. Buscador de Retazos":
    st.header("🔍 Buscador de Piezas Sueltas")
    st.info("Usá esta herramienta para aprovechar sobrantes antes de tocar una chapa nueva.")
    
    c1, c2 = st.columns(2)
    with c1:
        tipo_b = st.selectbox("¿Qué chapa busca el cliente?", list(st.session_state.inventory.keys()))
    with c2:
        largo_b = st.number_input("Largo necesario (m)", min_value=0.5, step=0.1)

    lista_cortes = st.session_state.inventory[tipo_b].cuts
    min_reserva = 1.5
    
    candidatos = [
        c for c in lista_cortes 
        if c >= largo_b and (round(c - largo_b, 2) == 0 or round(c - largo_b, 2) >= min_reserva)
    ]
    candidatos.sort() 

    if candidatos:
        st.success(f"¡Encontramos {len(candidatos)} piezas que sirven!")
        for rec in candidatos[:3]: # <-- Corregido: 'in' en lugar de 'en'
            sobra = round(rec - largo_b, 2)
            st.warning(f"📏 **Pieza de {rec}m**: Si la cortás a {largo_b}m, te queda un sobrante de **{sobra}m**.")
            # Un pequeño aviso informativo
            st.caption(f"Si usás esta pieza, recordá cargar el pedido en 'Tomar Material' para descontarla.")
    else:
        st.error("No hay recortes que cumplan la regla de los 1.5m. Deberás usar una chapa de 13m.")
