import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI

# --- HARUS DI ATAS SEMUA ---
st.set_page_config(
    page_title="Dashboard Media Intelligence Brewberry",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Konfigurasi OpenAI (untuk OpenRouter AI) ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"]
)

# --- Fungsi Insight AI ---
@st.cache_data(ttl=3600)
def generate_ai_insight(chart_title, data_context_str):
    prompt_messages = [
        {"role": "system", "content": "Anda adalah seorang ahli analisis media dan strategi konten..."},
        {"role": "user", "content": f"Berdasarkan data untuk chart '{chart_title}', dengan konteks: {data_context_str}.\n\nBerikan 3 insight strategi yang relevan dalam bullet point."},
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=prompt_messages,
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Gagal mendapatkan insight dari AI: {e}")
        return "Tidak dapat menghasilkan insight AI saat ini."

# --- Judul dan Deskripsi ---
st.title("Dashboard Media Intelligence Brewberry")
st.markdown("""
Aplikasi ini menampilkan analisis media intelijen dari data yang Anda unggah.
Jelajahi tren sentimen, keterlibatan, dan distribusi berdasarkan platform dan jenis media.
""")

# --- Logo di Sidebar ---
try:
    st.sidebar.image("Brewberry_Logo.png", use_container_width=True)
except:
    st.sidebar.warning("Logo tidak ditemukan.")

st.sidebar.markdown("---")

# --- Load Data ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [''.join(e.lower() if e.isalnum() else '_' for e in col) for col in df.columns]
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df = df.dropna(subset=['date'])
            if 'engagements' in df.columns:
                df['engagements'] = pd.to_numeric(df['engagements'], errors='coerce').fillna(0)
            return df
        except Exception as e:
            st.error(f"Error loading file: {e}")
    return None

# --- Upload File ---
st.sidebar.header("Unggah Data Anda")
uploaded_file = st.sidebar.file_uploader("Pilih file CSV", type=["csv"])
df = load_data(uploaded_file)

# --- Filter & Visualisasi ---
if df is not None:
    st.success("Data berhasil dimuat!")

    # Filter Sidebar
    platform_filter = st.sidebar.selectbox("Platform", ['All'] + df['platform'].unique().tolist() if 'platform' in df.columns else ['All'])
    if 'date' in df.columns:
        min_date, max_date = df['date'].min(), df['date'].max()
        date_range = st.sidebar.date_input("Rentang Tanggal", [min_date, max_date], min_value=min_date, max_value=max_date)
        df = df[(df['date'] >= pd.to_datetime(date_range[0])) & (df['date'] <= pd.to_datetime(date_range[1]))]
    if platform_filter != 'All':
        df = df[df['platform'] == platform_filter]

    # Chart 1 - Sentiment Breakdown
    if 'sentiment' in df.columns:
        st.subheader("1. Sentiment Breakdown")
        sentiment_counts = df['sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['Sentiment', 'Count']
        fig = px.pie(sentiment_counts, names='Sentiment', values='Count', title='Distribusi Sentimen')
        st.plotly_chart(fig, use_container_width=True)
        with st.spinner("Insight AI..."):
            st.markdown(generate_ai_insight("Distribusi Sentimen", sentiment_counts.to_string(index=False)))

    # Chart 2 - Engagement Trend
    if 'engagements' in df.columns and 'date' in df.columns:
        st.subheader("2. Engagement Trend")
        trend = df.groupby(df['date'].dt.to_period("D"))['engagements'].sum().reset_index()
        trend['date'] = trend['date'].astype(str)
        fig = px.line(trend, x='date', y='engagements', title='Tren Keterlibatan Harian')
        st.plotly_chart(fig, use_container_width=True)
        with st.spinner("Insight AI..."):
            st.markdown(generate_ai_insight("Tren Keterlibatan", trend.tail(10).to_string(index=False)))

    # Chart 3 - Platform Engagements
    if 'platform' in df.columns and 'engagements' in df.columns:
        st.subheader("3. Platform Engagements")
        pf_eng = df.groupby('platform')['engagements'].sum().reset_index()
        fig = px.bar(pf_eng, x='platform', y='engagements', title='Keterlibatan per Platform')
        st.plotly_chart(fig, use_container_width=True)
        with st.spinner("Insight AI..."):
            st.markdown(generate_ai_insight("Keterlibatan Platform", pf_eng.to_string(index=False)))

    # Chart 4 - Media Type
    if 'media_type' in df.columns:
        st.subheader("4. Media Type Mix")
        media_counts = df['media_type'].value_counts().reset_index()
        media_counts.columns = ['Media Type', 'Count']
        fig = px.pie(media_counts, names='Media Type', values='Count', title='Jenis Media')
        st.plotly_chart(fig, use_container_width=True)
        with st.spinner("Insight AI..."):
            st.markdown(generate_ai_insight("Jenis Media", media_counts.to_string(index=False)))

    # Chart 5 - Top 5 Location
    if 'location' in df.columns and 'engagements' in df.columns:
        st.subheader("5. Top 5 Locations by Engagement")
        loc_top = df.groupby('location')['engagements'].sum().nlargest(5).reset_index()
        fig = px.bar(loc_top, x='location', y='engagements', title='Top 5 Lokasi Berdasarkan Engagement')
        st.plotly_chart(fig, use_container_width=True)
        with st.spinner("Insight AI..."):
            st.markdown(generate_ai_insight("Top 5 Lokasi", loc_top.to_string(index=False)))
else:
    st.info("Silakan unggah file CSV Anda terlebih dahulu.")

# --- Sidebar Gambar Kaleng ---
st.sidebar.markdown("---")
try:
    st.sidebar.image("Brewberry_can.png", use_container_width=True)
except:
    st.sidebar.warning("Gambar kemasan kaleng tidak ditemukan.")
