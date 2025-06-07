import streamlit as st
import pandas as pd
import plotly.express as px
import io
from openai import OpenAI

# --- Konfigurasi OpenAI (untuk OpenRouter AI) ---
# Ambil API Key dari Streamlit Secrets untuk keamanan
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"] # Mengambil dari secrets.toml
)

# --- Fungsi untuk Memanggil AI untuk Insight ---
@st.cache_data(ttl=3600) # Cache insight AI selama 1 jam untuk performa dan menghindari re-call API
def generate_ai_insight(chart_title, data_context_str):
    prompt_messages = [
        {"role": "system", "content": "Anda adalah seorang ahli analisis media dan strategi konten. Tugas Anda adalah memberikan 3 insight kunci yang ringkas, relevan, dan dapat ditindaklanjuti berdasarkan data yang diberikan, fokus pada implikasi untuk produksi media atau marketing. Hindari mengulang deskripsi data, fokus pada 'mengapa' atau 'apa selanjutnya'."},
        {"role": "user", "content": f"Berdasarkan data untuk chart '{chart_title}', yang memiliki konteks data berikut: {data_context_str}\n\nHasilkan 3 insight kunci yang relevan untuk strategi produksi media atau marketing. Format sebagai daftar bullet point."},
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Anda bisa ganti model ini dengan yang lain dari OpenRouter
            messages=prompt_messages,
            temperature=0.7, # Kontrol kreativitas respons (0.0-1.0)
            max_tokens=300 # Batasi panjang respons AI
        )
        insight_text = response.choices[0].message.content
        return insight_text
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

# --- Menambahkan Logo ke Sidebar (di bagian atas) ---
try:
    st.sidebar.image("Brewberry_Logo.png", use_container_width=True) # Logo Brewberry - UBAH DI SINI
except FileNotFoundError:
    st.sidebar.warning("Logo Brewberry (Brewberry_Logo.png) tidak ditemukan. Pastikan ada di direktori yang sama dengan app.py.")
except Exception as e:
    st.sidebar.error(f"Error memuat logo: {e}")

st.sidebar.markdown("---") # Garis pemisah di sidebar

# --- Fungsi untuk Memuat dan Membersihkan Data ---
@st.cache_data # Menggunakan cache untuk performa
def load_data(uploaded_file):
    if uploaded_file is not None:
        try:
            dataframe = pd.read_csv(uploaded_file)

            st.write("---")
            st.subheader("Status Pembersihan Data Otomatis:")

            # 1. Normalisasi nama kolom untuk konsistensi di backend (huruf kecil, underscore)
            original_columns = dataframe.columns.tolist()
            st.info(f"Nama kolom asli yang terdeteksi: **{', '.join(original_columns)}**")

            # Membuat dictionary pemetaan nama kolom asli ke nama yang dinormalisasi (huruf kecil, underscore)
            normalized_columns_map = {}
            for col in original_columns:
                # Mengubah spasi dan karakter non-alphanumeric menjadi underscore
                normalized_col = col.lower().replace(' ', '_').replace('-', '_').replace('.', '_')
                # Hapus karakter non-alphanumeric yang tersisa kecuali underscore
                normalized_col = ''.join(e for e in normalized_col if e.isalnum() or e == '_')
                normalized_columns_map[col] = normalized_col
            
            dataframe.rename(columns=normalized_columns_map, inplace=True)
            st.success(f"Nama kolom dinormalisasi untuk pemrosesan internal.")

            # Penyesuaian nama kolom yang sering bervariasi tapi maknanya sama
            specific_column_corrections = {
                'engagement': 'engagements', 
                'media_type': 'media_type', 
            }
            for old_norm, new_norm in specific_column_corrections.items():
                if old_norm in dataframe.columns and old_norm != new_norm:
                    dataframe.rename(columns={old_norm: new_norm}, inplace=True)
                    st.info(f"Mengoreksi nama kolom: '{old_norm}' menjadi '{new_norm}'.")
            
            # Verifikasi kolom penting yang digunakan di chart setelah normalisasi
            required_cols_for_charts = ['date', 'sentiment', 'engagements', 'platform', 'media_type', 'location']
            missing_cols = [col for col in required_cols_for_charts if col not in dataframe.columns]
            if missing_cols:
                st.warning(f"Perhatian: Kolom berikut (dibutuhkan untuk chart) tidak ditemukan dalam data Anda setelah normalisasi: **{', '.join(missing_cols)}**.")
            else:
                st.success("Semua kolom kunci yang dibutuhkan untuk visualisasi ditemukan.")


            # 2. Kolom 'date' dikonversi menjadi objek datetime & Baris dengan tanggal tidak valid dihapus.
            if 'date' in dataframe.columns:
                initial_rows = len(dataframe)
                dataframe['date'] = pd.to_datetime(dataframe['date'], errors='coerce')
                dataframe.dropna(subset=['date'], inplace=True)
                rows_after_date_cleaning = len(dataframe)
                st.success(f"Kolom **'Date'** dikonversi ke format datetime. Dihapus {initial_rows - rows_after_date_cleaning} baris dengan tanggal tidak valid.")
            else:
                st.warning("Kolom 'Date' tidak ditemukan dalam data Anda. Filter tanggal dan tren waktu mungkin tidak berfungsi.")


            # 3. Nilai 'engagements' yang hilang diisi dengan 0.
            if 'engagements' in dataframe.columns:
                initial_na_engagements = dataframe['engagements'].isnull().sum()
                dataframe['engagements'] = pd.to_numeric(dataframe['engagements'], errors='coerce')
                dataframe['engagements'].fillna(0, inplace=True)
                final_na_engagements = dataframe['engagements'].isnull().sum()
                
                if initial_na_engagements > 0:
                    st.success(f"Nilai yang hilang di kolom **'Engagements'** ({initial_na_engagements} nilai) diisi dengan 0.")
                elif final_na_engagements == 0:
                     st.success("Kolom 'Engagements' sudah bersih (tidak ada nilai hilang yang diisi).")
                else:
                     st.error("Ada masalah dengan konversi 'Engagements' ke numerik. Beberapa nilai mungkin tetap NaN.")

            else:
                st.warning("Kolom 'Engagements' tidak ditemukan dalam data Anda. Chart terkait keterlibatan mungkin tidak berfungsi.")

            st.write("---")

            return dataframe
        except Exception as e:
            st.error(f"Error loading or cleaning file: {e}. Pastikan file adalah CSV yang valid dan tidak korup.")
            return None
    return None

# --- Unggah File CSV ---
st.sidebar.header("Unggah Data Anda")
uploaded_file = st.sidebar.file_uploader("Pilih file CSV", type=["csv"])

df = load_data(uploaded_file)

if df is not None:
    st.success("Data berhasil dimuat dan dibersihkan!")
    st.info("Memulai analisis data dan persiapan dashboard...")

    # --- Sidebar Filter ---
    st.sidebar.header("Filter Data")

    # Filter Platform (menggunakan 'platform' huruf kecil untuk akses data, tampilkan 'Platform' di UI)
    if 'platform' in df.columns:
        all_platforms = ['All'] + list(df['platform'].unique())
        selected_platform = st.sidebar.selectbox("Pilih Platform", all_platforms)
    else:
        selected_platform = 'All'
        st.sidebar.warning("Kolom 'Platform' tidak ditemukan dalam data Anda. Filter platform tidak tersedia.")

    # Filter Tanggal (menggunakan 'date' huruf kecil untuk akses data, tampilkan 'Tanggal' di UI)
    if 'date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['date']):
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        date_range = st.sidebar.date_input("Pilih Rentang Tanggal", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]
        else:
            df_filtered = df # Jika hanya satu tanggal dipilih, gunakan seluruh data
            st.sidebar.warning("Pilih rentang tanggal untuk memfilter data.")
    else:
        df_filtered = df
        st.sidebar.warning("Kolom 'Date' tidak ditemukan atau tidak dalam format tanggal yang benar. Filter tanggal tidak tersedia.")

    # Terapkan filter platform
    if selected_platform != 'All' and 'platform' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['platform'] == selected_platform]

    if not df_filtered.empty:
        # --- Menampilkan 5 Chart Plotly + Insight AI ---

        # 1. Sentiment Breakdown (menggunakan 'sentiment' huruf kecil)
        st.subheader("1. Sentiment Breakdown")
        if 'sentiment' in df_filtered.columns:
            sentiment_counts = df_filtered['sentiment'].value_counts().reset_index()
            sentiment_counts.columns = ['Sentiment', 'Count'] # Nama kolom untuk Plotly Pie Chart
            fig_sentiment = px.pie(sentiment_counts, names='Sentiment', values='Count',
                                   title='Distribusi Sentimen',
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_sentiment.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_sentiment, use_container_width=True) # UBAH DI SINI

            # Insight AI untuk Sentiment Breakdown
            with st.spinner('Menghasilkan insight AI untuk Sentimen...'):
                sentiment_data_summary = sentiment_counts.to_string(index=False)
                insight = generate_ai_insight(
                    "Distribusi Sentimen",
                    f"Berikut adalah jumlah per sentimen:\n{sentiment_data_summary}"
                )
                st.markdown("**Insight dari AI:**")
                st.markdown(insight)
        else:
            st.warning("Kolom 'Sentiment' tidak ditemukan dalam data Anda. Chart Sentiment Breakdown tidak dapat dibuat.")

        # 2. Engagement Trend (menggunakan 'engagements' dan 'date' huruf kecil)
        st.subheader("2. Engagement Trend")
        if 'engagements' in df_filtered.columns and 'date' in df_filtered.columns:
            engagement_trend = df_filtered.groupby(df_filtered['date'].dt.to_period('D'))['engagements'].sum().reset_index()
            engagement_trend['date'] = engagement_trend['date'].astype(str) # Ubah ke string untuk Plotly
            fig_engagement_trend = px.line(engagement_trend, x='date', y='engagements',
                                            title='Tren Keterlibatan Seiring Waktu',
                                            labels={'date': 'Tanggal', 'engagements': 'Total Keterlibatan'}) # Label tampilan
            st.plotly_chart(fig_engagement_trend, use_container_width=True) # UBAH DI SINI

            # Insight AI untuk Engagement Trend
            with st.spinner('Menghasilkan insight AI untuk Tren Keterlibatan...'):
                engagement_data_summary = engagement_trend.tail(10).to_string(index=False) # Ambil 10 baris terakhir
                insight = generate_ai_insight(
                    "Tren Keterlibatan Seiring Waktu",
                    f"Berikut adalah tren keterlibatan per tanggal (10 data terakhir):\n{engagement_data_summary}"
                )
                st.markdown("**Insight dari AI:**")
                st.markdown(insight)
        else:
            st.warning("Kolom 'Engagements' atau 'Date' tidak ditemukan dalam data Anda. Chart Engagement Trend tidak dapat dibuat.")

        # 3. Platform Engagements (menggunakan 'platform' dan 'engagements' huruf kecil)
        st.subheader("3. Platform Engagements")
        if 'platform' in df_filtered.columns and 'engagements' in df_filtered.columns:
            platform_engagement = df_filtered.groupby('platform')['engagements'].sum().reset_index()
            fig_platform_engagement = px.bar(platform_engagement, x='platform', y='engagements',
                                             title='Keterlibatan Berdasarkan Platform',
                                             labels={'platform': 'Platform Media', 'engagements': 'Total Keterlibatan'}, # Label tampilan
                                             color='platform')
            st.plotly_chart(fig_platform_engagement, use_container_width=True) # UBAH DI SINI

            # Insight AI untuk Platform Engagements
            with st.spinner('Menghasilkan insight AI untuk Keterlibatan Platform...'):
                platform_data_summary = platform_engagement.to_string(index=False)
                insight = generate_ai_insight(
                    "Keterlibatan Berdasarkan Platform",
                    f"Berikut adalah total keterlibatan per platform:\n{platform_data_summary}"
                )
                st.markdown("**Insight dari AI:**")
                st.markdown(insight)
        else:
            st.warning("Kolom 'Platform' atau 'Engagements' tidak ditemukan dalam data Anda. Chart Platform Engagements tidak dapat dibuat.")

        # 4. Media Type Mix (menggunakan 'media_type' huruf kecil)
        st.subheader("4. Media Type Mix")
        if 'media_type' in df_filtered.columns:
            media_type_counts = df_filtered['media_type'].value_counts().reset_index()
            # Ubah nama kolom untuk tampilan tanpa underscore di chart pie Plotly
            media_type_counts.columns = ['Media Type', 'Count'] 
            fig_media_type = px.pie(media_type_counts, names='Media Type', values='Count',
                                    title='Distribusi Jenis Media',
                                    color_discrete_sequence=px.colors.qualitative.Set3)
            fig_media_type.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_media_type, use_container_width=True) # UBAH DI SINI

            # Insight AI untuk Media Type Mix
            with st.spinner('Menghasilkan insight AI untuk Distribusi Jenis Media...'):
                media_type_data_summary = media_type_counts.to_string(index=False)
                insight = generate_ai_insight(
                    "Distribusi Jenis Media",
                    f"Berikut adalah jumlah konten per jenis media:\n{media_type_data_summary}"
                )
                st.markdown("**Insight dari AI:**")
                st.markdown(insight)
        else:
            st.warning("Kolom 'Media Type' tidak ditemukan dalam data Anda. Chart Media Type Mix tidak dapat dibuat.")

        # 5. Top 5 Locations by Engagement (menggunakan 'location' dan 'engagements' huruf kecil)
        st.subheader("5. Top 5 Locations by Engagement")
        if 'location' in df_filtered.columns and 'engagements' in df_filtered.columns:
            location_engagement = df_filtered.groupby('location')['engagements'].sum().nlargest(5).reset_index()
            fig_top_locations = px.bar(location_engagement, x='location', y='engagements',
                                       title='5 Lokasi Teratas Berdasarkan Keterlibatan',
                                       labels={'location': 'Lokasi', 'engagements': 'Total Keterlibatan'}, # Label tampilan
                                       color='location')
            st.plotly_chart(fig_top_locations, use_container_width=True) # UBAH DI SINI

            # Insight AI untuk Top 5 Locations
            with st.spinner('Menghasilkan insight AI untuk Lokasi Teratas...'):
                location_data_summary = location_engagement.to_string(index=False)
                insight = generate_ai_insight(
                    "5 Lokasi Teratas Berdasarkan Keterlibatan",
                    f"Berikut adalah total keterlibatan untuk 5 lokasi teratas:\n{location_data_summary}"
                )
                st.markdown("**Insight dari AI:**")
                st.markdown(insight)
        else:
            st.warning("Kolom 'Location' atau 'Engagements' tidak ditemukan dalam data Anda. Chart Top 5 Locations tidak dapat dibuat.")
    else:
        st.warning("Tidak ada data yang tersedia setelah filter diterapkan. Coba sesuaikan filter Anda atau unggah file CSV yang berbeda.")
else:
    st.info("Silakan unggah file CSV Anda untuk memulai.")

# --- Menambahkan Gambar Kemasan Kaleng di Sidebar (di bagian bawah) ---
st.sidebar.markdown("---") # Garis pemisah
try:
    st.sidebar.image("Brewberry_can.png", use_container_width=True) # Gambar kaleng kemasan - UBAH DI SINI
except FileNotFoundError:
    st.sidebar.warning("Gambar kemasan kaleng (Brewberry_can.png) tidak ditemukan. Pastikan ada di direktori yang sama dengan app.py.")
except Exception as e:
    st.sidebar.error(f"Error memuat gambar kemasan kaleng: {e}")