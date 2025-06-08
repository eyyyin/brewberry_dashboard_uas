import streamlit as st
import pandas as pd
import plotly.express as px
import requests

API_KEY = st.secrets["OPENROUTER_API_KEY"]
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def get_ai_response(user_input):
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }

    response = requests.post(API_URL, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Gagal mendapatkan response AI. Error {response.status_code}: {response.text}"

@st.cache_data(ttl=3600)  # Cache insight AI selama 1 jam
def generate_ai_insight(chart_title, data_context_str):
    prompt_messages = [
        {"role": "system", "content": "Anda adalah seorang ahli analisis media dan strategi konten. Tugas Anda adalah memberikan 3 insight kunci yang ringkas, relevan, dan dapat ditindaklanjuti berdasarkan data yang diberikan, fokus pada implikasi untuk produksi media atau marketing. Hindari mengulang deskripsi data, fokus pada 'mengapa' atau 'apa selanjutnya'."},
        {"role": "user", "content": f"Berdasarkan data untuk chart '{chart_title}', yang memiliki konteks data berikut: {data_context_str}\n\nHasilkan 3 insight kunci yang relevan untuk strategi produksi media atau marketing. Format sebagai daftar bullet point."},
    ]

    try:
        response = requests.post(API_URL, headers=headers, json={
            "model": "openai/gpt-3.5-turbo",
            "messages": prompt_messages,
            "temperature": 0.7,
            "max_tokens": 300
        })

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Gagal mendapatkan insight AI. Error {response.status_code}: {response.text}"
    except Exception as e:
        st.error(f"Gagal mendapatkan insight dari AI: {e}")
        return "Tidak dapat menghasilkan insight AI saat ini."

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(
    page_title="Dashboard Media Intelligence Brewberry",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Judul dan Deskripsi Aplikasi ---
st.title("Dashboard Media Intelligence Brewberry")
st.markdown("""
Aplikasi ini menampilkan analisis media intelijen dari data yang Anda unggah.
Anda dapat menjelajahi tren sentimen, keterlibatan, dan distribusi berdasarkan berbagai platform dan jenis media.
""")

# --- Menambahkan Logo ke Sidebar ---
try:
    st.sidebar.image("Brewberry_Logo.png", use_container_width=True)
except FileNotFoundError:
    st.sidebar.warning("Logo Brewberry (Brewberry_Logo.png) tidak ditemukan. Pastikan ada di direktori yang sama dengan app.py.")
except Exception as e:
    st.sidebar.error(f"Error memuat logo: {e}")

st.sidebar.markdown("---")

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        try:
            dataframe = pd.read_csv(uploaded_file)

            st.write("---")
            st.subheader("Status Pembersihan Data Otomatis:")

            original_columns = dataframe.columns.tolist()
            st.info(f"Nama kolom asli yang terdeteksi: **{', '.join(original_columns)}**")

            normalized_columns_map = {}
            for col in original_columns:
                normalized_col = col.lower().replace(' ', '_').replace('-', '_').replace('.', '_')
                normalized_col = ''.join(e for e in normalized_col if e.isalnum() or e == '_')
                normalized_columns_map[col] = normalized_col
            
            dataframe.rename(columns=normalized_columns_map, inplace=True)
            st.success(f"Nama kolom dinormalisasi untuk pemrosesan internal.")

            # Koreksi nama kolom spesifik
            specific_column_corrections = {
                'engagement': 'engagements', 
                'media_type': 'media_type',
            }
            for old_norm, new_norm in specific_column_corrections.items():
                if old_norm in dataframe.columns and old_norm != new_norm:
                    dataframe.rename(columns={old_norm: new_norm}, inplace=True)
                    st.info(f"Mengoreksi nama kolom: '{old_norm}' menjadi '{new_norm}'.")

            required_cols_for_charts = ['date', 'sentiment', 'engagements', 'platform', 'media_type', 'location']
            missing_cols = [col for col in required_cols_for_charts if col not in dataframe.columns]
            if missing_cols:
                st.warning(f"Kolom berikut tidak ditemukan: **{', '.join(missing_cols)}**.")
            else:
                st.success("Semua kolom kunci untuk visualisasi ditemukan.")

            if 'date' in dataframe.columns:
                initial_rows = len(dataframe)
                dataframe['date'] = pd.to_datetime(dataframe['date'], errors='coerce')
                dataframe.dropna(subset=['date'], inplace=True)
                rows_after_date_cleaning = len(dataframe)
                st.success(f"Kolom 'date' dikonversi ke datetime. Dihapus {initial_rows - rows_after_date_cleaning} baris tanggal tidak valid.")
            else:
                st.warning("Kolom 'date' tidak ditemukan. Filter tanggal tidak tersedia.")

            if 'engagements' in dataframe.columns:
                initial_na_engagements = dataframe['engagements'].isnull().sum()
                dataframe['engagements'] = pd.to_numeric(dataframe['engagements'], errors='coerce')
                dataframe['engagements'].fillna(0, inplace=True)
                final_na_engagements = dataframe['engagements'].isnull().sum()
                if initial_na_engagements > 0:
                    st.success(f"Nilai hilang di kolom 'engagements' ({initial_na_engagements} nilai) diisi dengan 0.")
                elif final_na_engagements == 0:
                    st.success("Kolom 'engagements' sudah bersih (tidak ada nilai hilang).")
                else:
                    st.error("Masalah konversi 'engagements' ke numerik.")
            else:
                st.warning("Kolom 'engagements' tidak ditemukan. Chart keterlibatan mungkin tidak berfungsi.")

            st.write("---")

            return dataframe
        except Exception as e:
            st.error(f"Error loading or cleaning file: {e}. Pastikan file CSV valid.")
            return None
    return None

st.sidebar.header("Unggah Data Anda")
uploaded_file = st.sidebar.file_uploader("Pilih file CSV", type=["csv"])

df = load_data(uploaded_file)

if df is not None:
    st.success("Data berhasil dimuat dan dibersihkan!")
    st.info("Memulai analisis dan persiapan dashboard...")

    # Filter Platform
    st.sidebar.header("Filter Data")
    if 'platform' in df.columns:
        all_platforms = ['All'] + list(df['platform'].unique())
        selected_platform = st.sidebar.selectbox("Pilih Platform", all_platforms)
    else:
        selected_platform = 'All'
        st.sidebar.warning("Kolom 'platform' tidak ditemukan, filter platform tidak tersedia.")

    # Filter Tanggal
    if 'date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['date']):
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        date_range = st.sidebar.date_input("Pilih Rentang Tanggal", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]
        else:
            df_filtered = df
            st.sidebar.warning("Pilih rentang tanggal untuk memfilter data.")
    else:
        df_filtered = df
        st.sidebar.warning("Kolom 'date' tidak ditemukan atau bukan datetime. Filter tanggal tidak tersedia.")

    if selected_platform != 'All' and 'platform' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['platform'] == selected_platform]

    if not df_filtered.empty:
        # 1. Sentiment Breakdown
        st.subheader("1. Sentiment Breakdown")
        if 'sentiment' in df_filtered.columns:
            sentiment_counts = df_filtered['sentiment'].value_counts().reset_index()
            sentiment_counts.columns = ['Sentiment', 'Count']
            fig_sentiment = px.pie(sentiment_counts, names='Sentiment', values='Count',
                                   title='Distribusi Sentimen',
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_sentiment.update_traces(textinfo='
