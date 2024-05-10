from io import BytesIO
import asyncio
import numpy as np
import pandas as pd
import streamlit as st
from pytubefix import YouTube
from channel_collector import get_channels_basic_info, get_videos_detail, export_excel


ss = st.session_state

st.set_page_config(
    layout="wide",
    page_title="🔍Channel Videos Finder",
    page_icon="🔍",

)

st.markdown("# 🔍Channel Videos Finder")


channels_input = st.text_area(label = "Enter list of channels (recommended 5 at a time), seperated by newlines:")

channel_urls = channels_input.split('\n')

col1, col2 = st.columns(2)

with col1:
    published_after = st.date_input("Filter Videos Published After", value=pd.to_datetime('2024-04-01'))
with col2:
    maximum_videos_per_channel = st.slider("Enter maximum number of videos per channel", min_value= 50, value=100, step=50, max_value=200)


but1, but2 = st.columns(2)
with but1:
    if st.button("Get Videos", type = "primary", use_container_width=True):

        channels_basic_info = asyncio.run(get_channels_basic_info(channel_urls))

        all_video_details, all_captions = get_videos_detail(channels_basic_info, str(published_after), maximum_videos_per_channel//50)

        ss['export'] = export_excel(all_video_details, all_captions)
        

with but2:
    if(st.session_state.get('export') is not None):
        st.download_button(
            label="⬇️Download Channel's Video Data",
            data=st.session_state.export,
            type = "primary",
            use_container_width=True,
            file_name='videos.xlsx',
            help='Include full data of video stats, locations and hashtags.'
                )
