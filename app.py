import streamlit as st
import pandas as pd
import plotly.express as px
import openai

# Set API key OpenAI kamu di sini atau lewat environment variable
openai.api_key = "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"

st.set_page_config(page_title="BrewBerry Dashboard", layout="wide")

st.title("BrewBerry Media Intelligence Dashboard")

def generate_ai_insight(title, data_context):
    prompt = f"Berikan insight singkat tentang data berikut untuk topik '{title}':\n{data_context}\nInsight:"
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            temperature=0.7,
            n=1,
            stop=None,
        )
        insight_text = response.choices[0].text.strip()
        return insight_text
    except Exception as e:
        return f"Error generating insight: {str(e)}"

uploaded_file = st.file_uploader("Unggah file CSV media BrewBerry", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        st.sidebar.header("Filter Data")

        # Filter by Date Range jika ada kolom 'date'
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            min_date = df['date'].min()
            max_date = df['date'].max()
            date_range = st.sidebar.date_input("Pilih rentang tanggal", [min_date, max_date])
            if len(date_range) == 2:
                start_date, end_date = date_range
                df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
            else:
                df_filtered = df.copy()
        else:
            st.warning("Kolom 'date' tidak ditemukan dalam data.")
            df_filtered = df.copy()

        # Filter by Platform jika ada kolom 'platform'
        if 'platform' in df.columns:
            platforms = df['platform'].unique()
            selected_platforms = st.sidebar.multiselect("Pilih platform", platforms, default=platforms)
            df_filtered = df_filtered[df_filtered['platform'].isin(selected_platforms)]
        else:
            st.warning("Kolom 'platform' tidak ditemukan dalam data.")

        # Filter by Media Type jika ada kolom 'media_type'
        if 'media_type' in df.columns:
            media_types = df['media_type'].unique()
            selected_media = st.sidebar.multiselect("Pilih tipe media", media_types, default=media_types)
            df_filtered = df_filtered[df_filtered['media_type'].isin(selected_media)]
        else:
            st.warning("Kolom 'media_type' tidak ditemukan dalam data.")

        st.write(f"Total data setelah filter: {len(df_filtered)}")

        if df_filtered.empty:
            st.warning("Data hasil filter kosong. Silakan ubah filter.")
        else:
            st.header("Visualisasi dan Insight")

            # 1. Sentiment Breakdown
            st.subheader("1. Sentiment Breakdown")
            if 'sentiment' in df_filtered.columns:
                sentiment_counts = df_filtered['sentiment'].value_counts().reset_index()
                sentiment_counts.columns = ['Sentiment', 'Count']
                fig_sentiment = px.pie(sentiment_counts, names='Sentiment', values='Count', title='Distribusi Sentiment')
                fig_sentiment.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_sentiment, use_container_width=True)

                data_context_sentiment = sentiment_counts.to_dict()
                insight_sentiment = generate_ai_insight("Sentiment Breakdown", str(data_context_sentiment))
                st.markdown("**Insight AI:**")
                st.info(insight_sentiment)
            else:
                st.warning("Kolom 'sentiment' tidak ditemukan di data.")

            # 2. Engagement Over Time
            st.subheader("2. Engagement Over Time")
            if 'date' in df_filtered.columns and 'engagements' in df_filtered.columns:
                df_time_engagement = df_filtered.groupby('date')['engagements'].sum().reset_index()
                fig_engagement = px.line(df_time_engagement, x='date', y='engagements',
                                         title='Engagement Over Time',
                                         labels={'date': 'Tanggal', 'engagements': 'Total Engagement'})
                st.plotly_chart(fig_engagement, use_container_width=True)

                data_context_engagement = df_time_engagement.to_dict()
                insight_engagement = generate_ai_insight("Engagement Over Time", str(data_context_engagement))
                st.markdown("**Insight AI:**")
                st.info(insight_engagement)
            else:
                st.warning("Kolom 'date' atau 'engagements' tidak ditemukan.")

            # 3. Distribution by Platform
            st.subheader("3. Distribution by Platform")
            if 'platform' in df_filtered.columns:
                platform_counts = df_filtered['platform'].value_counts().reset_index()
                platform_counts.columns = ['Platform', 'Count']
                fig_platform = px.bar(platform_counts, x='Platform', y='Count', title='Distribution by Platform')
                st.plotly_chart(fig_platform, use_container_width=True)

                data_context_platform = platform_counts.to_dict()
                insight_platform = generate_ai_insight("Distribution by Platform", str(data_context_platform))
                st.markdown("**Insight AI:**")
                st.info(insight_platform)
            else:
                st.warning("Kolom 'platform' tidak ditemukan.")

            # 4. Distribution by Media Type
            st.subheader("4. Distribution by Media Type")
            if 'media_type' in df_filtered.columns:
                media_counts = df_filtered['media_type'].value_counts().reset_index()
                media_counts.columns = ['Media Type', 'Count']
                fig_media = px.bar(media_counts, x='Media Type', y='Count', title='Distribution by Media Type')
                st.plotly_chart(fig_media, use_container_width=True)

                data_context_media = media_counts.to_dict()
                insight_media = generate_ai_insight("Distribution by Media Type", str(data_context_media))
                st.markdown("**Insight AI:**")
                st.info(insight_media)
            else:
                st.warning("Kolom 'media_type' tidak ditemukan.")

            # 5. Distribution by Location
            st.subheader("5. Distribution by Location")
            if 'location' in df_filtered.columns:
                location_counts = df_filtered['location'].value_counts().reset_index()
                location_counts.columns = ['Location', 'Count']
                fig_location = px.bar(location_counts, x='Location', y='Count', title='Distribution by Location')
                st.plotly_chart(fig_location, use_container_width=True)

                data_context_location = location_counts.to_dict()
                insight_location = generate_ai_insight("Distribution by Location", str(data_context_location))
                st.markdown("**Insight AI:**")
                st.info(insight_location)
            else:
                st.warning("Kolom 'location' tidak ditemukan.")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses file: {str(e)}")
else:
    st.info("Silakan unggah file CSV terlebih dahulu untuk memulai analisis.")
