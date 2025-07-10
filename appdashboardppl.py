import streamlit as st
import pandas as pd
import datetime
import os
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import MaxNLocator # Para controlar el número de ticks en el eje Y

# --- Configuración de la página ---
st.set_page_config(
    page_title="Dashboard de Productividad del Profesional",
    page_icon="📊",
    layout="wide"
)

# 1. Configuración de Persistencia de Datos
PERSISTED_DATA_DIR = "../persisted_data"
os.makedirs(PERSISTED_DATA_DIR, exist_ok=True) # Asegúrate de que la carpeta exista

# Nombre de archivo para el DataFrame persistente
PRODUCTIVITY_FILE = os.path.join(PERSISTED_DATA_DIR, "df_productivity.parquet")

# 2. Inicializar st.session_state
if 'productivity_uploaded' not in st.session_state:
    st.session_state.productivity_uploaded = False
if 'df_productivity' not in st.session_state:
    st.session_state.df_productivity = None

# 3. Funciones para guardar y cargar DataFrames con Parquet
def save_dataframe(df, filepath):
    """Guarda un DataFrame en un archivo Parquet."""
    filename = os.path.basename(filepath)
    if df is not None and not df.empty:
        try:
            df.to_parquet(filepath, index=False)
            st.info(f"💾 Guardado exitoso: {filename}")
            return True
        except Exception as e:
            st.error(f"❌ Error al guardar el archivo {filename}: {e}")
            return False
    else:
        st.info(f"ℹ️ No hay datos para guardar en {filename}. (DataFrame vacío o None)")
        return True # Retorna True porque no es un error, simplemente no hay nada que guardar.

def load_dataframe(filepath):
    """Carga un DataFrame desde un archivo Parquet."""
    if os.path.exists(filepath):
        try:
            df_loaded = pd.read_parquet(filepath)
            # Asegura tipos de string al cargar desde Parquet, incluyendo la nueva columna
            string_cols_to_convert_on_load = ['RESPONSABLE DEL REGISTRO', 'IDENTIFICACIÓN DEL PPL', 'CLASIFICACION DE NOVEDAD', 'SEGUNDO APELLIDO', 'PRIMER NOMBRE', 'SEGUNDO NOMBRE', 'PRIMER APELLIDO', 'RESPONSABLE AUDITORIA']
            for col in string_cols_to_convert_on_load:
                if col in df_loaded.columns:
                    df_loaded[col] = df_loaded[col].fillna('').astype(str)
            return df_loaded
        except Exception as e:
            st.warning(f"No se pudo cargar el archivo {os.path.basename(filepath)} previamente guardado. "
                       f"Por favor, súbelo de nuevo o verifica el archivo. Error: {e}")
            return None
    return None

# 4. Función para cargar archivos subidos (con caché para eficiencia)
@st.cache_data
def load_uploaded_data(uploaded_file):
    """
    Carga un archivo CSV o Excel en un DataFrame de Pandas.
    Maneja errores y retorna None si la carga falla.
    """
    if uploaded_file is not None:
        try:
            uploaded_file.seek(0) # Siempre resetear el puntero antes de intentar leer

            # Intentar leer como CSV primero
            try:
                df_loaded = pd.read_csv(uploaded_file, encoding='utf-8', errors='ignore', on_bad_lines='skip')
                return df_loaded
            except Exception as csv_error:
                # Si falla CSV, intentar como Excel, ESPECIFICANDO LA HOJA "NOVEDADES JULIO"
                uploaded_file.seek(0) # Resetear el puntero del archivo para Excel
                try:
                    df_loaded = pd.read_excel(uploaded_file, sheet_name="NOVEDADES JULIO", engine='openpyxl')
                    return df_loaded
                except Exception as excel_error:
                    st.error(f"Error al cargar la hoja 'NOVEDADES JULIO' del archivo Excel. Detalles: {excel_error}")
                    st.error("Asegúrate de que la hoja exista y esté bien escrita.")
                    return None
        except Exception as e:
            st.error(f"Error general al cargar el archivo. Asegúrate de que sea un archivo CSV o Excel válido. Detalles: {e}")
            return None
    return None

# 5. Cargar datos persistentes al inicio si existen
if not st.session_state.productivity_uploaded and os.path.exists(PRODUCTIVITY_FILE):
    st.session_state.df_productivity = load_dataframe(PRODUCTIVITY_FILE)
    if st.session_state.df_productivity is not None:
        # Aseguramos tipos de string y datetime al cargar de persistencia, incluyendo la nueva columna
        string_cols_to_convert_on_load_state = ['RESPONSABLE DEL REGISTRO', 'IDENTIFICACIÓN DEL PPL', 'CLASIFICACION DE NOVEDAD', 'SEGUNDO APELLIDO', 'PRIMER NOMBRE', 'SEGUNDO NOMBRE', 'PRIMER APELLIDO', 'RESPONSABLE AUDITORIA']
        for col in string_cols_to_convert_on_load_state:
            if col in st.session_state.df_productivity.columns:
                st.session_state.df_productivity[col] = st.session_state.df_productivity[col].fillna('').astype(str)

        if 'FECHA DE REGISTRO DE NOVEDAD' in st.session_state.df_productivity.columns:
            st.session_state.df_productivity['FECHA DE REGISTRO DE NOVEDAD'] = pd.to_datetime(st.session_state.df_productivity['FECHA DE REGISTRO DE NOVEDAD'], errors='coerce')

        st.session_state.productivity_uploaded = True
        st.info("Archivo de productividad cargado desde persistencia.")

# 6. Título y encabezados del Dashboard
st.title("📊 Dashboard de Productividad del Profesional")
st.markdown("Sube tu archivo para analizar la productividad de los profesionales por pacientes.")

# 7. Carga del Archivo desde la barra lateral
st.sidebar.header("Cargar Archivo")

if not st.session_state.productivity_uploaded:
    uploaded_file_widget = st.sidebar.file_uploader(
        "Sube tu archivo de Productividad (CSV/Excel)",
        type=["csv", "xlsx"],
        key="productivity_uploader"
    )
    if uploaded_file_widget is not None:
        df_new = load_uploaded_data(uploaded_file_widget)
        if df_new is not None:
            # Convertir todas las columnas del DataFrame a mayúsculas para la comparación y evitar errores
            df_new.columns = df_new.columns.str.upper()

            # Convertir explícitamente a string las columnas problemáticas ANTES de la validación
            # Incluir 'RESPONSABLE AUDITORIA' aquí también
            string_cols_to_convert = ['RESPONSABLE DEL REGISTRO', 'IDENTIFICACIÓN DEL PPL', 'CLASIFICACION DE NOVEDAD', 'SEGUNDO APELLIDO', 'PRIMER NOMBRE', 'SEGUNDO NOMBRE', 'PRIMER APELLIDO', 'RESPONSABLE AUDITORIA']
            for col in string_cols_to_convert:
                if col in df_new.columns:
                    df_new[col] = df_new[col].fillna('').astype(str)

            # CONVERSIÓN DE TIPO DE DATO: columnas críticas a str y datetime
            required_cols_for_check = {
                'RESPONSABLE DEL REGISTRO': str,
                'FECHA DE REGISTRO DE NOVEDAD': 'datetime', # <-- Requerida para el filtro de fecha
                'IDENTIFICACIÓN DEL PPL': str
            }
            # Add 'RESPONSABLE AUDITORIA' to required columns for checking if present in file
            if 'RESPONSABLE AUDITORIA' in df_new.columns:
                required_cols_for_check['RESPONSABLE AUDITORIA'] = str

            if 'CLASIFICACION DE NOVEDAD' in df_new.columns:
                required_cols_for_check['CLASIFICACION DE NOVEDAD'] = str

            # Verificar si todas las columnas requeridas existen
            missing_cols = [col for col in required_cols_for_check if col not in df_new.columns]
            if missing_cols:
                st.error(f"❌ Error: Las siguientes columnas requeridas no se encontraron en la hoja 'NOVEDADES JULIO': **{', '.join(missing_cols)}**.")
                st.error("Por favor, asegúrate de que tu archivo contenga estas columnas en la hoja especificada y vuelve a cargarlo.")
                st.session_state.df_productivity = None
                st.session_state.productivity_uploaded = False
            else:
                if 'FECHA DE REGISTRO DE NOVEDAD' in df_new.columns:
                    df_new['FECHA DE REGISTRO DE NOVEDAD'] = pd.to_datetime(df_new['FECHA DE REGISTRO DE NOVEDAD'], errors='coerce')
                    df_new.dropna(subset=['FECHA DE REGISTRO DE NOVEDAD'], inplace=True)

                st.session_state.productivity_uploaded = True
                st.session_state.df_productivity = df_new
                st.success("Archivo cargado y preprocesado correctamente desde la hoja 'NOVEDADES JULIO'.")
                st.rerun()
        else:
            st.error("Fallo al cargar el archivo.")
else:
    st.sidebar.info("Archivo ya cargado (desde subida o persistencia).")

# 8. Botones de Acción: Guardar y Limpiar
st.sidebar.markdown("---")
st.sidebar.subheader("Acciones de Datos")

if st.sidebar.button("Guardar datos para futura carga", key="save_data_button"):
    if save_dataframe(st.session_state.df_productivity, PRODUCTIVITY_FILE):
        st.sidebar.success("Datos procesados guardados correctamente.")
    else:
        st.sidebar.error("Hubo un error al guardar los datos.")

def clear_uploaded_files():
    st.session_state.productivity_uploaded = False
    st.session_state.df_productivity = None
    if os.path.exists(PRODUCTIVITY_FILE):
        os.remove(PRODUCTIVITY_FILE)
        st.sidebar.info(f"Archivo persistente {os.path.basename(PRODUCTIVITY_FILE)} eliminado.")
    st.cache_data.clear()
    st.rerun()

st.sidebar.button("Limpiar archivo cargado y persistente", on_click=clear_uploaded_files, key="clear_files_button")

# *** VALIDACIÓN REFORZADA DE DATAFRAME ***
df = st.session_state.df_productivity if st.session_state.df_productivity is not None else pd.DataFrame()

if df.empty:
    st.info("Para comenzar el análisis, por favor **sube un archivo** usando el botón en la **barra lateral izquierda**, o **carga los datos guardados** si ya existen.")
    st.stop() # Detiene la ejecución si df está vacío (lo que incluye el caso de ser originalmente None)
# *****************************************

# 10. Filtro de Análisis (GLOBAL)
st.sidebar.subheader("Filtros de Análisis")

# Inicializamos df_filtered_date para que siempre tenga un valor
df_filtered_date = df.copy()

# *** BLOQUE DE FILTRADO DE FECHAS (AHORA DENTRO DE LA COMPROBACIÓN DE COLUMNA) ***
if 'FECHA DE REGISTRO DE NOVEDAD' in df.columns:
    min_date_global = df['FECHA DE REGISTRO DE NOVEDAD'].min().date()
    max_date_global = df['FECHA DE REGISTRO DE NOVEDAD'].max().date()

    date_range_selection = st.sidebar.date_input(
        "Selecciona Rango de Fechas",
        value=(min_date_global, max_date_global),
        min_value=min_date_global,
        max_value=max_date_global,
        key="date_range_filter_global"
    )

    if len(date_range_selection) == 2:
        start_date = min(date_range_selection)
        end_date = max(date_range_selection)
    elif len(date_range_selection) == 1:
        start_date = date_range_selection[0]
        end_date = date_range_selection[0]
    else: # Fallback si la selección está vacía por alguna razón
        start_date = min_date_global
        end_date = max_date_global

    st.markdown(f"**Periodo de Análisis:** Del **{start_date.strftime('%d/%m/%Y')}** al **{end_date.strftime('%d/%m/%Y')}**")

    if start_date > end_date:
        st.sidebar.error("Error: La fecha de inicio no puede ser posterior a la fecha de fin. Por favor, corrige tu selección.")
        st.stop()

    df_filtered_date = df[
        (df['FECHA DE REGISTRO DE NOVEDAD'].dt.date >= start_date) &
        (df['FECHA DE REGISTRO DE NOVEDAD'].dt.date <= end_date)
    ].copy()

    if df_filtered_date.empty:
        st.warning("No hay datos disponibles para el rango de fechas seleccionado. Por favor, ajusta los filtros.")
        st.stop()

else:
    # Si FECHA DE REGISTRO DE NOVEDAD es missing, display an error and stop.
    st.error("❌ Error crítico: La columna 'FECHA DE REGISTRO DE NOVEDAD' no se encontró en el archivo cargado. Asegúrate de que el nombre sea **exacto** y la columna exista.")
    st.stop()
# *** FIN DEL BLOQUE DE FILTRADO DE FECHAS ***


# --- FILTRO DE PROFESIONAL (UNIFICADO PARA REGISTRO Y AUDITORÍA) ---
professional_options_union = []
if 'RESPONSABLE DEL REGISTRO' in df_filtered_date.columns:
    professional_options_union.extend(df_filtered_date['RESPONSABLE DEL REGISTRO'].dropna().astype(str).unique())
if 'RESPONSABLE AUDITORIA' in df_filtered_date.columns:
    professional_options_union.extend(df_filtered_date['RESPONSABLE AUDITORIA'].dropna().astype(str).unique())

if professional_options_union:
    professional_options_union = sorted(list(set(professional_options_union))) # Elimina duplicados y ordena
    professional_options = ['Todos'] + professional_options_union
    professional_seleccionado = st.sidebar.multiselect(
        'Filtrar por Profesional (Registro o Auditoría):',
        options=professional_options,
        default=['Todos'],
        key="filter_professional_unified" # Cambiado el key para evitar conflictos si se crea otro multiselect
    )

    if 'Todos' in professional_seleccionado and len(professional_seleccionado) > 1:
        professional_seleccionado = ['Todos']
        st.sidebar.info("Cuando 'Todos' está seleccionado, se ignoran las otras selecciones de profesional.")
    elif not professional_seleccionado:
        professional_seleccionado = ['Todos']
        st.sidebar.info("No se ha seleccionado ningún profesional. Mostrando datos para todos los profesionales.")
else:
    st.sidebar.info("Carga el archivo para acceder a los filtros de profesional.")
    professional_seleccionado = ['Todos']

# Aplicar el filtro de profesionales a df_filtered
if 'Todos' not in professional_seleccionado:
    # Filtra si el profesional está en la columna de registro O en la columna de auditoría
    df_filtered = df_filtered_date[
        (df_filtered_date['RESPONSABLE DEL REGISTRO'].isin(professional_seleccionado)) |
        (df_filtered_date['RESPONSABLE AUDITORIA'].isin(professional_seleccionado))
    ].copy()
else:
    df_filtered = df_filtered_date.copy()

if df_filtered.empty:
    st.warning("No hay datos disponibles para la combinación de filtros seleccionada. Por favor, ajusta los filtros.")
    st.stop()
# --- FIN FILTRO DE PROFESIONAL ---


# --- ANÁLISIS DE PRODUCTIVIDAD DEL PROFESIONAL (RESPONSABLE DEL REGISTRO) ---
st.markdown("---")
st.markdown("## Productividad del Profesional por **Registro**")
st.markdown("Aquí puedes ver la productividad de los profesionales basada en la cantidad de pacientes que han **registrado**.")

if 'RESPONSABLE DEL REGISTRO' in df_filtered.columns and 'IDENTIFICACIÓN DEL PPL' in df_filtered.columns:

    if 'Todos' in professional_seleccionado or len(professional_seleccionado) > 1:
        # Asegurarse de que solo se incluyen los profesionales seleccionados si no es 'Todos'
        df_for_analysis_registro = df_filtered.copy()
        if 'Todos' not in professional_seleccionado:
             df_for_analysis_registro = df_filtered[df_filtered['RESPONSABLE DEL REGISTRO'].isin(professional_seleccionado)].copy()

        if not df_for_analysis_registro.empty:
            df_patients_per_professional_registro = df_for_analysis_registro.groupby('RESPONSABLE DEL REGISTRO').agg(
                total_pacientes_revisados=('IDENTIFICACIÓN DEL PPL', 'nunique'),
                registros_totales=('IDENTIFICACIÓN DEL PPL', 'count')
            ).reset_index()

            df_patients_per_professional_registro['total_pacientes_revisados'] = df_patients_per_professional_registro['total_pacientes_revisados'].astype(int)
            df_patients_per_professional_registro['registros_totales'] = df_patients_per_professional_registro['registros_totales'].astype(int)

            st.markdown("### Tabla de Pacientes Únicos Registrados por Profesional")
            st.dataframe(df_patients_per_professional_registro.set_index('RESPONSABLE DEL REGISTRO'))

            fig_registro, ax_registro = plt.subplots(figsize=(12, 6))
            bars_registro = ax_registro.bar(df_patients_per_professional_registro['RESPONSABLE DEL REGISTRO'], df_patients_per_professional_registro['total_pacientes_revisados'], color='skyblue')

            ax_registro.set_title('Pacientes Únicos Registrados por Profesional')
            ax_registro.set_xlabel('Responsable del Registro')
            ax_registro.set_ylabel('Número de Pacientes Únicos')
            ax_registro.tick_params(axis='x', rotation=45)

            for bar in bars_registro:
                yval = bar.get_height()
                ax_registro.text(bar.get_x() + bar.get_width()/2, yval + 5, int(yval), ha='center', va='bottom', fontsize=9)

            plt.tight_layout()
            st.pyplot(fig_registro)
        else:
            st.info("No hay datos de registros para los profesionales seleccionados en el rango de fechas.")


    elif len(professional_seleccionado) == 1:
        selected_professional_registro = professional_seleccionado[0]
        # Asegúrate de que el profesional seleccionado existe en la columna de 'RESPONSABLE DEL REGISTRO'
        if selected_professional_registro in df_filtered['RESPONSABLE DEL REGISTRO'].unique():
            st.subheader(f"Evolución Diaria de Registros para: {selected_professional_registro}")

            df_daily_activity_registro = df_filtered[df_filtered['RESPONSABLE DEL REGISTRO'] == selected_professional_registro].copy()
            df_daily_activity_registro['FECHA DE REGISTRO DE NOVEDAD'] = pd.to_datetime(df_daily_activity_registro['FECHA DE REGISTRO DE NOVEDAD'])
            df_daily_counts_registro = df_daily_activity_registro.groupby(df_daily_activity_registro['FECHA DE REGISTRO DE NOVEDAD'].dt.date).size().reset_index(name='Total Registros Diarios')
            df_daily_counts_registro.columns = ['Fecha', 'Total Registros Diarios']
            df_daily_counts_registro = df_daily_counts_registro.sort_values(by='Fecha')

            if not df_daily_counts_registro.empty:
                st.markdown(f"**Acumulado Diario de Registros para {selected_professional_registro}:**")
                st.dataframe(df_daily_counts_registro)

                fig_daily_registro, ax_daily_registro = plt.subplots(figsize=(14, 7))
                ax_daily_registro.plot(df_daily_counts_registro['Fecha'], df_daily_counts_registro['Total Registros Diarios'], marker='o', linestyle='-', color='indigo')

                ax_daily_registro.set_title(f'Evolución de Registros Diarios por {selected_professional_registro}')
                ax_daily_registro.set_xlabel('Período (Día)')
                ax_daily_registro.set_ylabel('Total Registros Diarios')
                ax_daily_registro.grid(True, linestyle='--', alpha=0.7)

                fig_daily_registro.autofmt_xdate(rotation=45)
                ax_daily_registro.xaxis.set_major_locator(plt.MaxNLocator(nbins=10))

                for i, txt in enumerate(df_daily_counts_registro['Total Registros Diarios']):
                    ax_daily_registro.annotate(txt, (df_daily_counts_registro['Fecha'].iloc[i], df_daily_counts_registro['Total Registros Diarios'].iloc[i]),
                                textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color='darkgreen')

                ax_daily_registro.set_ylim(bottom=0, top=df_daily_counts_registro['Total Registros Diarios'].max() * 1.15)

                plt.tight_layout()
                st.pyplot(fig_daily_registro)
            else:
                st.info(f"No hay datos de registros diarios para {selected_professional_registro} en el rango de fechas seleccionado.")
        else:
            st.info(f"El profesional '{selected_professional_registro}' no aparece como 'Responsable del Registro' en los datos filtrados.")

else:
    st.warning("Las columnas 'RESPONSABLE DEL REGISTRO' o 'IDENTIFICACIÓN DEL PPL' no se encontraron en el archivo. No se puede calcular la productividad por registro.")

# --- ANÁLISIS DE PRODUCTIVIDAD DEL PROFESIONAL (RESPONSABLE AUDITORIA) ---
st.markdown("## Productividad del Profesional por **Auditoría**")
st.markdown("Esta sección muestra la productividad de los profesionales basada en la cantidad de pacientes que han **auditado**.")

if 'RESPONSABLE AUDITORIA' in df_filtered.columns and 'IDENTIFICACIÓN DEL PPL' in df_filtered.columns:

    if 'Todos' in professional_seleccionado or len(professional_seleccionado) > 1:
        # Asegurarse de que solo se incluyen los profesionales seleccionados si no es 'Todos'
        df_for_analysis_auditoria = df_filtered.copy()
        if 'Todos' not in professional_seleccionado:
            df_for_analysis_auditoria = df_filtered[df_filtered['RESPONSABLE AUDITORIA'].isin(professional_seleccionado)].copy()

        if not df_for_analysis_auditoria.empty:
            df_patients_per_auditor = df_for_analysis_auditoria.groupby('RESPONSABLE AUDITORIA').agg(
                total_pacientes_auditados=('IDENTIFICACIÓN DEL PPL', 'nunique'),
                auditorias_totales=('IDENTIFICACIÓN DEL PPL', 'count')
            ).reset_index()

            df_patients_per_auditor['total_pacientes_auditados'] = df_patients_per_auditor['total_pacientes_auditados'].astype(int)
            df_patients_per_auditor['auditorias_totales'] = df_patients_per_auditor['auditorias_totales'].astype(int)

            st.markdown("### Tabla de Pacientes Únicos Auditados por Profesional")
            st.dataframe(df_patients_per_auditor.set_index('RESPONSABLE AUDITORIA'))

            fig_auditor, ax_auditor = plt.subplots(figsize=(12, 6))
            bars_auditor = ax_auditor.bar(df_patients_per_auditor['RESPONSABLE AUDITORIA'], df_patients_per_auditor['total_pacientes_auditados'], color='lightcoral')

            ax_auditor.set_title('Pacientes Únicos Auditados por Responsable de Auditoría')
            ax_auditor.set_xlabel('Responsable de Auditoría')
            ax_auditor.set_ylabel('Número de Pacientes Únicos')
            ax_auditor.tick_params(axis='x', rotation=45)

            for bar in bars_auditor:
                yval = bar.get_height()
                ax_auditor.text(bar.get_x() + bar.get_width()/2, yval + 5, int(yval), ha='center', va='bottom', fontsize=9)

            plt.tight_layout()
            st.pyplot(fig_auditor)
        else:
            st.info("No hay datos de auditorías para los profesionales seleccionados en el rango de fechas.")

    elif len(professional_seleccionado) == 1:
        selected_professional_auditor = professional_seleccionado[0]
        # Asegúrate de que el profesional seleccionado existe en la columna de 'RESPONSABLE AUDITORIA'
        if selected_professional_auditor in df_filtered['RESPONSABLE AUDITORIA'].unique():
            st.subheader(f"Evolución Diaria de Auditorías para: {selected_professional_auditor}")

            df_daily_activity_auditor = df_filtered[df_filtered['RESPONSABLE AUDITORIA'] == selected_professional_auditor].copy()
            df_daily_activity_auditor['FECHA DE REGISTRO DE NOVEDAD'] = pd.to_datetime(df_daily_activity_auditor['FECHA DE REGISTRO DE NOVEDAD'])
            df_daily_counts_auditor = df_daily_activity_auditor.groupby(df_daily_activity_auditor['FECHA DE REGISTRO DE NOVEDAD'].dt.date).size().reset_index(name='Total Auditorías Diarias')
            df_daily_counts_auditor.columns = ['Fecha', 'Total Auditorías Diarias']
            df_daily_counts_auditor = df_daily_counts_auditor.sort_values(by='Fecha')

            if not df_daily_counts_auditor.empty:
                st.markdown(f"**Acumulado Diario de Auditorías para {selected_professional_auditor}:**")
                st.dataframe(df_daily_counts_auditor)

                fig_daily_auditor, ax_daily_auditor = plt.subplots(figsize=(14, 7))
                ax_daily_auditor.plot(df_daily_counts_auditor['Fecha'], df_daily_counts_auditor['Total Auditorías Diarias'], marker='o', linestyle='-', color='firebrick')

                ax_daily_auditor.set_title(f'Evolución de Auditorías Diarias por {selected_professional_auditor}')
                ax_daily_auditor.set_xlabel('Período (Día)')
                ax_daily_auditor.set_ylabel('Total Auditorías Diarias')
                ax_daily_auditor.grid(True, linestyle='--', alpha=0.7)

                fig_daily_auditor.autofmt_xdate(rotation=45)
                ax_daily_auditor.xaxis.set_major_locator(plt.MaxNLocator(nbins=10))

                for i, txt in enumerate(df_daily_counts_auditor['Total Auditorías Diarias']):
                    ax_daily_auditor.annotate(txt, (df_daily_counts_auditor['Fecha'].iloc[i], df_daily_counts_auditor['Total Auditorías Diarias'].iloc[i]),
                                            textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color='darkred')

                ax_daily_auditor.set_ylim(bottom=0, top=df_daily_counts_auditor['Total Auditorías Diarias'].max() * 1.15)

                plt.tight_layout()
                st.pyplot(fig_daily_auditor)
            else:
                st.info(f"No hay datos de auditorías diarias para {selected_professional_auditor} en el rango de fechas seleccionado.")
        else:
            st.info(f"El profesional '{selected_professional_auditor}' no aparece como 'Responsable de Auditoría' en los datos filtrados.")

else:
    st.warning("Las columnas 'RESPONSABLE AUDITORIA' o 'IDENTIFICACIÓN DEL PPL' no se encontraron en el archivo. No se puede calcular la productividad por auditoría.")