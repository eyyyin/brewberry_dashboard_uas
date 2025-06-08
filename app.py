import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Ambil API Key dari secrets.toml
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

@st.cache_data(ttl=3600)  # Cache hasil AI selama 1 jam
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
            insight_text = response.json()["choices"][0]["message"]["content"]
            return insight_text
        else:
            return f"Gagal mendapatkan insight dari AI. Error {response.status_code}: {response.text}"

    except Exception as e:
        st.error(f"Gagal mendapatkan insight dari AI: {e}")
        return "Tidak dapat menghasilkan insight AI saat ini."


# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="Dashboard Media Intelligence Brewberry",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Judul dan Deskripsi ---
st.title("Dashboard Media Intelligence Brewberry")
st.markdown("""
Aplikasi ini menampilkan analisis media intelijen dari data yang Anda unggah.
Anda dapat menjelajahi tren sentimen, keterlibatan, dan distribusi berdasarkan berbagai platform dan jenis media.
""")

# --- Sidebar Logo ---
try:
    st.sidebar.image("Brewberry_Logo.png", use_container_width=True)
except FileNotFoundError:
    st.sidebar.warning("Logo Brewberry (Brewberry_Logo.png) tidak ditemukan.")
except Exception as e:
    st.sidebar.error(f"Error memuat logo: {e}")

st.sidebar.markdown("---")

# --- Fungsi Load dan Bersihkan Data ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)

            st.write("---")
            st.subheader("Status Pembersihan Data Otomatis:")

            original_columns = df.columns.tolist()
            st.info(f"Nama kolom asli yang terdeteksi: **{', '.join(original_columns)}**")

            # Normalisasi nama kolom
            normalized_columns_map = {}
            for col in original_columns:
                normalized_col = col.lower().replace(' ', '_').replace('-', '_').replace('.', '_')
                normalized_col = ''.join(e for e in normalized_col if e.isalnum() or e == '_')
                normalized_columns_map[col] = normalized_col
            df.rename(columns=normalized_columns_map, inplace=True)
            st.success("Nama kolom dinormalisasi untuk pemrosesan internal.")

            # Koreksi nama kolom yang sering bervariasi
            specific_column_corrections = {
                'engagement': 'engagements',
                # kamu bisa tambahkan lagi jika perlu
            }
            for old_name, new_name in specific_column_corrections.items():
                if old_name in df.columns and old_name != new_name:
                    df.rename(columns={old_name: new_name}, inplace=True)
                    st.info(f"Mengoreksi nama kolom: '{old_name}' menjadi '{new_name}'.")

            # Cek kolom penting
            required_cols = ['date', 'sentiment', 'engagements', 'platform', 'media_type', 'location']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.warning(f"Kolom penting tidak ditemukan: {', '.join(missing_cols)}")
            else:
                st.success("Semua kolom kunci ditemukan.")

            # Konversi 'date'
            if 'date' in df.columns:
                before_len = len(df)
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df.dropna(subset=['date'], inplace=True)
                after_len = len(df)
                st.success(f"Kolom 'date' dikonversi. Dihapus {before_len - after_len} baris tanggal tidak valid.")
            else:
                st.warning("Kolom 'date' tidak ditemukan.")

            # Isi missing di 'engagements'
            if 'engagements' in df.columns:
                missing_eng = df['engagements'].isnull().sum()
                df['engagements'] = pd.to_numeric(df['engagements'], errors='coerce').fillna(0)
                if missing_eng > 0:
                    st.success(f"Nilai hilang di kolom 'engagements' ({missing_eng} nilai) diisi 0.")
            else:
                st.warning("Kolom 'engagements' tidak ditemukan.")

            st.write("---")
            return df
        except Exception as e:
            st.error(f"Error saat memuat/bersihkan file: {e}")
            return None
    return None


# --- Sidebar Upload ---
st.sidebar.header("Unggah Data Anda")
uploaded_file = st.sidebar.file_uploader("Pilih file CSV", type=["csv"])

df = load_data(uploaded_file)

if df is not None:
    st.success("Data berhasil dimuat dan dibersihkan!")
    st.info("Memulai analisis data dan persiapan dashboard...")

    # --- Sidebar Filter ---
    st.sidebar.header("Filter Data")

    # Filter Platform
    if 'platform' in df.columns:
        platforms = ['All'] + list(df['platform'].unique())
        selected_platform = st.sidebar.selectbox("Pilih Platform", platforms)
    else:
        selected_platform = 'All'
        st.sidebar.warning("Kolom 'platform' tidak ditemukan. Filter platform tidak tersedia.")

    # Filter Date
    if 'date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['date']):
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        date_range = st.sidebar.date_input("Pilih Rentang Tanggal", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]
        else:
            df_filtered = df
            st.sidebar.warning("Pilih rentang tanggal untuk filter.")
    else:
        df_filtered = df
        st.sidebar.warning("Kolom 'date' tidak ditemukan atau format salah. Filter tanggal tidak tersedia.")

    # Terapkan filter platform
    if selected_platform != 'All' and 'platform' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['platform'] == selected_platform]

    if not df_filtered.empty:
        # Chart 1: Sentiment Breakdown
        st.subheader("1. Sentiment Breakdown")
        if 'sentiment' in df_filtered.columns:
            sentiment_counts = df_filtered['sentiment'].value_counts().reset_index()
            sentiment_counts.columns = ['Sentiment', 'Count']
            fig_sentiment = px.pie(sentiment_counts, names='Sentiment', values='Count',
                                   title='Distribusi Sentimen',
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_sentiment.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_sentiment, use_container_width=True)

            with st.spinner('Menghasilkan insight AI untuk Sentimen...'):
                data_summary = sentiment_counts.to_string(index=False)
                insight = generate_ai_insight("Distribusi Sentimen", f"Jumlah per sentimen:\n{data_summary}")
                st.markdown("**Insight dari AI:**")
                st.markdown(insight)
        else:
            st.warning("Kolom 'sentiment' tidak ditemukan.")

        # Chart 2: Engagement Trend
        st.subheader("2. Engagement Trend")
        if 'engagements' in df_filtered.columns and 'date' in df_filtered.columns:
            engagement_trend = df_filtered.groupby(df_filtered['date'].dt.to_period('D'))['engagements'].sum().reset_index()
            engagement_trend['date'] = engagement_trend['date'].astype(str)
            fig_engagement = px.line(engagement_trend, x='date', y='engagements',
                                     title='Tren Keterlibatan Seiring Waktu',
                                     labels={'date': 'Tanggal', 'engagements': 'Total Keterlibatan'})
            st.plotly_chart(fig_engagement, use_container_width=True)

            with st.spinner('Menghasilkan insight AI untuk Tren Keterlibatan...'):
                data_summary = engagement_trend.tail(10).to_string(index=False)
                insight = generate_ai_insight("Tren Keterlibatan Seiring Waktu", f"Data 10 hari terakhir:\n{data_summary}")
                st.markdown("**Insight dari AI:**")
                st.markdown(insight)
        else:
            st.warning
