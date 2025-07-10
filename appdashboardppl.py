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
            # Asegura tipos de string al cargar desde Parquet, incluyendo las columnas relevantes
            string_cols_to_convert_on_load = ['RESPONSABLE DEL REGISTRO', 'IDENTIFICACIÓN DEL PPL',
                                              'CLASIFICACION DE NOVEDAD', 'SEGUNDO APELLIDO', 'PRIMER NOMBRE',
                                              'SEGUNDO NOMBRE', 'PRIMER APELLIDO', 'RESPONSABLE AUDITORIA']
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
        # Aseguramos tipos de string y datetime al cargar de persistencia
        string_cols_to_convert_on_load_state = ['RESPONSABLE DEL REGISTRO', 'IDENTIFICACIÓN DEL PPL',
                                                'CLASIFICACION DE NOVEDAD', 'SEGUNDO APELLIDO', 'PRIMER NOMBRE',
                                                'SEGUNDO NOMBRE', 'PRIMER APELLIDO', 'RESPONSABLE AUDITORIA']
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
            # Convertir todas las columnas del DataFrame a mayúsculas
            df_new.columns = df_new.columns.str.upper()

            # Convertir explícitamente a string las columnas problemáticas ANTES de la validación
            string_cols_to_convert = ['RESPONSABLE DEL REGISTRO', 'IDENTIFICACIÓN DEL PPL', 'CLASIFICACION DE NOVEDAD', 'SEGUNDO APELLIDO', 'PRIMER NOMBRE', 'SEGUNDO NOMBRE', 'PRIMER APELLIDO', 'RESPONSABLE AUDITORIA']
            for col in string_cols_to_convert:
                if col in df_new.columns:
                    df_new[col] = df_new[col].fillna('').astype(str)

            # CONVERSIÓN DE TIPO DE DATO: columnas críticas a str y datetime
            required_cols_for_check = {
                'RESPONSABLE DEL REGISTRO': str,
                'FECHA DE REGISTRO DE NOVEDAD': 'datetime',
                'IDENTIFICACIÓN DEL PPL': str
            }
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

# *** BLOQUE DE FILTRADO DE FECHAS ***
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
    st.error("❌ Error crítico: La columna 'FECHA DE REGISTRO DE NOVEDAD' no se encontró en el archivo cargado. Asegúrate de que el nombre sea **exacto** y la columna exista.")
    st.stop()
# *** FIN DEL BLOQUE DE FILTRADO DE FECHAS ***

# --- PREPARACIÓN DE DATOS PARA ANÁLISIS UNIFICADO ---
# Se crea un DataFrame temporal para el análisis unificado.
# Cada fila en el original puede generar una o dos filas en el unificado,
# dependiendo de si el profesional es Responsable de Registro o Auditoría.

# Lista para almacenar los datos transformados
unified_data = []

# Iterar sobre las filas del DataFrame filtrado por fecha
for index, row in df_filtered_date.iterrows():
    # Si hay un Responsable del Registro, añadir una entrada de "Registro"
    if 'RESPONSABLE DEL REGISTRO' in row and pd.notna(row['RESPONSABLE DEL REGISTRO']) and row['RESPONSABLE DEL REGISTRO'] != '':
        unified_data.append({
            'Profesional': row['RESPONSABLE DEL REGISTRO'],
            'Tipo_Actividad': 'Registro',
            'IDENTIFICACIÓN DEL PPL': row['IDENTIFICACIÓN DEL PPL'],
            'FECHA DE REGISTRO DE NOVEDAD': row['FECHA DE REGISTRO DE NOVEDAD']
        })

    # Si hay un Responsable de Auditoría, añadir una entrada de "Auditoría"
    if 'RESPONSABLE AUDITORIA' in row and pd.notna(row['RESPONSABLE AUDITORIA']) and row['RESPONSABLE AUDITORIA'] != '':
        unified_data.append({
            'Profesional': row['RESPONSABLE AUDITORIA'],
            'Tipo_Actividad': 'Auditoría',
            'IDENTIFICACIÓN DEL PPL': row['IDENTIFICACIÓN DEL PPL'],
            'FECHA DE REGISTRO DE NOVEDAD': row['FECHA DE REGISTRO DE NOVEDAD']
        })

# Crear el DataFrame unificado
if unified_data:
    df_unified = pd.DataFrame(unified_data)
    # Convertir a string para evitar problemas de tipo si vienen de diferentes fuentes
    df_unified['Profesional'] = df_unified['Profesional'].astype(str)
    df_unified['IDENTIFICACIÓN DEL PPL'] = df_unified['IDENTIFICACIÓN DEL PPL'].astype(str)
else:
    df_unified = pd.DataFrame(columns=['Profesional', 'Tipo_Actividad', 'IDENTIFICACIÓN DEL PPL', 'FECHA DE REGISTRO DE NOVEDAD'])
    st.warning("No se encontraron profesionales de registro o auditoría para analizar en el rango de fechas seleccionado.")
    st.stop()


# --- FILTRO DE PROFESIONAL (UNIFICADO) ---
# Ahora el filtro se basa en la columna 'Profesional' del DataFrame unificado
professional_options_unified = df_unified['Profesional'].dropna().unique()

if professional_options_unified.size > 0:
    professional_options = ['Todos'] + sorted(list(professional_options_unified))
    professional_seleccionado = st.sidebar.multiselect(
        'Filtrar por Profesional:',
        options=professional_options,
        default=['Todos'],
        key="filter_professional_unified"
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

# Aplicar el filtro de profesionales al DataFrame unificado
if 'Todos' not in professional_seleccionado:
    df_filtered_unified = df_unified[df_unified['Profesional'].isin(professional_seleccionado)].copy()
else:
    df_filtered_unified = df_unified.copy()

if df_filtered_unified.empty:
    st.warning("No hay datos disponibles para la combinación de filtros seleccionada. Por favor, ajusta los filtros.")
    st.stop()

# --- ANÁLISIS DE PRODUCTIVIDAD UNIFICADO ---
st.markdown("---")
st.markdown("## Productividad General del Profesional (Registro y Auditoría)")
st.markdown("Aquí puedes ver la productividad consolidada de los profesionales, basada en los pacientes que han **registrado o auditado**.")

# Calcular pacientes únicos por profesional (sin importar el tipo de actividad)
df_patients_per_professional_unified = df_filtered_unified.groupby('Profesional').agg(
    pacientes_unicos_total=('IDENTIFICACIÓN DEL PPL', 'nunique'),
    actividades_totales=('IDENTIFICACIÓN DEL PPL', 'count')
).reset_index()

df_patients_per_professional_unified['pacientes_unicos_total'] = df_patients_per_professional_unified['pacientes_unicos_total'].astype(int)
df_patients_per_professional_unified['actividades_totales'] = df_patients_per_professional_unified['actividades_totales'].astype(int)

st.markdown("### Tabla de Pacientes Únicos y Actividades Totales por Profesional")
st.dataframe(df_patients_per_professional_unified.set_index('Profesional'))

# Generar el gráfico de barras unificado
if not df_patients_per_professional_unified.empty:
    fig_unified, ax_unified = plt.subplots(figsize=(14, 7))
    bars_unified = ax_unified.bar(df_patients_per_professional_unified['Profesional'],
                                  df_patients_per_professional_unified['pacientes_unicos_total'],
                                  color='mediumseagreen') # Color neutro y vibrante

    ax_unified.set_title('Pacientes Únicos por Profesional (Registro y Auditoría)')
    ax_unified.set_xlabel('Profesional')
    ax_unified.set_ylabel('Número de Pacientes Únicos')
    ax_unified.tick_params(axis='x', rotation=45, ha='right') # Ajuste de rotación y alineación de etiquetas

    # Añadir etiquetas de valor a las barras
    for bar in bars_unified:
        yval = bar.get_height()
        ax_unified.text(bar.get_x() + bar.get_width()/2, yval + 5, int(yval), ha='center', va='bottom', fontsize=9)

    ax_unified.set_ylim(bottom=0, top=df_patients_per_professional_unified['pacientes_unicos_total'].max() * 1.15) # Ajustar límite Y para espacio de etiquetas

    plt.tight_layout()
    st.pyplot(fig_unified)
else:
    st.info("No hay datos de productividad unificada para los filtros seleccionados.")

# --- SECCIÓN OPCIONAL: DETALLE DE EVOLUCIÓN DIARIA POR TIPO DE ACTIVIDAD (SI SELECCIONA UN SOLO PROFESIONAL) ---
if len(professional_seleccionado) == 1 and 'Todos' not in professional_seleccionado:
    selected_professional_detail = professional_seleccionado[0]
    st.markdown("---")
    st.subheader(f"Evolución Diaria Detallada para: {selected_professional_detail}")
    st.markdown("Desglose de actividad diaria como **Registrador** y **Auditor**.")

    # Filtrar solo por el profesional seleccionado en el df_unified
    df_daily_activity_detail = df_filtered_unified[df_filtered_unified['Profesional'] == selected_professional_detail].copy()
    df_daily_activity_detail['FECHA_DIA'] = df_daily_activity_detail['FECHA DE REGISTRO DE NOVEDAD'].dt.date

    if not df_daily_activity_detail.empty:
        # Contar actividades diarias por tipo y profesional
        df_daily_counts_detail = df_daily_activity_detail.groupby(['FECHA_DIA', 'Tipo_Actividad']).size().unstack(fill_value=0).reset_index()
        df_daily_counts_detail = df_daily_counts_detail.sort_values(by='FECHA_DIA')

        st.markdown(f"**Acumulado Diario por Tipo de Actividad para {selected_professional_detail}:**")
        st.dataframe(df_daily_counts_detail)

        fig_daily_detail, ax_daily_detail = plt.subplots(figsize=(14, 7))

        # Graficar cada tipo de actividad si existe
        if 'Registro' in df_daily_counts_detail.columns:
            ax_daily_detail.plot(df_daily_counts_detail['FECHA_DIA'], df_daily_counts_detail['Registro'], marker='o', linestyle='-', color='blue', label='Registros Diarios')
        if 'Auditoría' in df_daily_counts_detail.columns:
            ax_daily_detail.plot(df_daily_counts_detail['FECHA_DIA'], df_daily_counts_detail['Auditoría'], marker='x', linestyle='--', color='red', label='Auditorías Diarias')

        ax_daily_detail.set_title(f'Evolución Diaria de Actividades para {selected_professional_detail}')
        ax_daily_detail.set_xlabel('Período (Día)')
        ax_daily_detail.set_ylabel('Total Actividades Diarias')
        ax_daily_detail.grid(True, linestyle='--', alpha=0.7)
        ax_daily_detail.legend()

        fig_daily_detail.autofmt_xdate(rotation=45)
        ax_daily_detail.xaxis.set_major_locator(plt.MaxNLocator(nbins=10))
        ax_daily_detail.set_ylim(bottom=0) # Asegurar que el eje Y comience en 0

        # Ajuste para etiquetas de valores en el gráfico (opcional, puede ser ruidoso con muchos puntos)
        # for col in ['Registro', 'Auditoría']:
        #     if col in df_daily_counts_detail.columns:
        #         for i, txt in enumerate(df_daily_counts_detail[col]):
        #             if txt > 0: # Solo si hay actividad para ese día
        #                 ax_daily_detail.annotate(txt, (df_daily_counts_detail['FECHA_DIA'].iloc[i], df_daily_counts_detail[col].iloc[i]),
        #                                         textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)


        plt.tight_layout()
        st.pyplot(fig_daily_detail)
    else:
        st.info(f"No hay datos de actividad diaria detallada para {selected_professional_detail} en el rango de fechas seleccionado.")