from io import BytesIO
from src.yt_ingestion import getRecentChannelVids, queryChannelVidIds, get_channel_video_ids
from src.process import process_yt_videos
import pandas as pd
import streamlit as st
import asyncio
import concurrent.futures
from pytubefix import Channel

async def get_channel_id_name(channel_url):
    c = Channel(channel_url)
 # Asynchronous call to fetch data
    return c.channel_id, c.channel_name

def get_channel_info(channel):
    return asyncio.run(get_channel_id_name(channel))

async def get_channels_basic_info(channels):
    channels_basic_info = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(get_channel_info, channels)

    for result in results:
        channels_basic_info.append(result)

    return channels_basic_info

def get_videos_detail(channels_basic_info, publishedAfter="2024-04-01", limit=2):
    all_video_details = []
    all_captions = {}
    processBar = st.progress(0)
    for index, channel_basic_info in enumerate(channels_basic_info):
        c_id, c_name = channel_basic_info
        query_c = get_channel_video_ids(channelId = c_id, publishedAfter = publishedAfter, limit= limit)
        video_details, captions = process_yt_videos(query_c, c_name)
        # Add channel_name into captions
        for video_id in captions.keys():
            captions[video_id]["channel_name"] = c_name
        for detail in video_details:
            detail["channel_name"] = c_name
            
        all_video_details.extend(video_details)
        all_captions.update(captions)
        processBar.progress((index+1)/len(channels_basic_info))
    processBar.empty()
    return all_video_details, all_captions


def export_excel(all_video_details, all_captions) -> BytesIO:
    
    output = BytesIO()
    # convert all_video_details into df
    df = pd.DataFrame(all_video_details)
    df_captions = pd.DataFrame(all_captions)
    df_captions = df_captions.T

    # Rename index column to video_id
    df_captions.index.name = 'video_id'
    df_captions.reset_index(inplace=True)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='video details', index=False)
        df_captions.to_excel(writer, sheet_name='captions', index=False)
        
    processed_data = output.getvalue()

    return processed_data