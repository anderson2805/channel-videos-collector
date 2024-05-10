import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re
from datetime import datetime
import streamlit as st
from src.yt_ingestion import getVideoDetail
# Add subtitles to the post details
import requests
from src.service import create_yt_service
from youtube_transcript_api import YouTubeTranscriptApi
from utils.processing_utils import process_captions
# from utils.embeddings_utils import get_embeddings, get_embedding, cosine_similarity
# from langchain_text_splitters import TokenTextSplitter
import concurrent.futures
global service, api_list
# api_file = open("./data/yt_secret.txt", "r")
# apis = api_file.read()
apis = st.secrets["keys"]
api_list = apis.split("\n")
API_KEY = api_list.pop()
api_list = [API_KEY] + api_list
service = create_yt_service(API_KEY)

# text_splitter = TokenTextSplitter(encoding_name="cl100k_base", chunk_size=8000, chunk_overlap=0)
def durationSec(durationLs):
    durationLs = [int(time) for time in durationLs]
    if(len(durationLs) == 3):
        return (durationLs[0] * 3600) + (durationLs[1] * 60) + durationLs[2]
    elif(len(durationLs) == 2):
        return (durationLs[0] * 60) + durationLs[1]
    else:
        return durationLs[0]

def searchChunking(ids: list, size: int = 50):
    resultsChunks = [ids[i:i + size]
                     for i in range(0, len(ids), size)]
    return resultsChunks

def extract_hashtags(text):
    # the regular expression
    regex = "#(\w+)"
    # extracting the hashtags
    hashtag_list = re.findall(regex, text)
    hashtag_list = [hashtag.title() for hashtag in hashtag_list]
    return(hashtag_list)

def process_description(text):
    if (text == ""):
        return ""
    sentences = re.sub(r'(\W)(?=\1)', '', text).split('\n')
    processed = []
    for index, sentence in enumerate(sentences):
        url_search = re.search(r'http\S+', sentence)
        at_search = re.search(r'@', sentence)
        if(re.subn(r'\W', '', sentence)[1] == len(sentence) or not sentence[0].isalpha() or len(sentences[index-1]) == 0):
            break
        elif (url_search is None and at_search is None):
            processed.append(sentence)
        elif(len(processed) > 1 and (url_search is not None and len(url_search.span()) > 1 and (url_search.span()[1] - url_search.span()[0]) == len(sentence)) or sentences[index - 1][-1] in [':', '-']):
            try:
                processed.pop()
            except:
                print(processed)
    return " ".join(processed)


def process_yt_videos(video_ids: list, seed_id = None, seed_content = None):
    global service, api_list

    current_time = datetime.now().strftime("%Y%m%dT%H%M%SZ%z")
    videoList = []
    # processBar = st.progress(0)
    chunkList = searchChunking(video_ids)
    chunkLength = len(chunkList)
    responses = []
    for count, chunk in enumerate(chunkList):
        print("Processing videos %i / %i" %
              (count + 1, chunkLength))
        # processBar.progress((count+1)/chunkLength)
        videoIds_chunk = ",".join(chunk)
        try:
            response = getVideoDetail(videoIds_chunk, service)
        except:
            API_KEY = api_list.pop()
            api_list = [API_KEY] + api_list
            service = create_yt_service(API_KEY)
            response = getVideoDetail(videoIds_chunk, service)
        responses = response['items'] + responses
        for item in response['items']:
            contentDetails = item['contentDetails']
            snippet = item['snippet']
            statistics = item.get('statistics')
            topicDetails = item.get('topicDetails')
            recordingDetails = item.get('recordingDetails')
            recordingDate = recordingDetails.get('recordingDate')
            hashtags = extract_hashtags(snippet.get('description'))
            tags = snippet.get('tags', [])
            videoDict = {'videoId': item['id'],
                         'publishedAt': (snippet['publishedAt']),
                         'recordingDate': recordingDate,
                         'collectDateTime': datetime.now(),
                         'title': snippet['title'],
                         'description': snippet.get('description'),
                         'processedDescription': process_description(snippet.get('description', "")),
                         'duration': durationSec(re.findall(r'\d+', contentDetails['duration'])),
                         'defaultAudioLanguage': snippet.get('defaultAudioLanguage'),
                         'commentCount': statistics.get('commentCount'),
                         'favoriteCount': statistics['favoriteCount'],
                         'likeCount': statistics.get('likeCount'),
                         'viewCount': statistics.get('viewCount'),
                         'channelId': snippet['channelId'],
                         'topicDetails': topicDetails,
                         'locationDescription': recordingDetails.get('locationDescription'),
                         'tags': tags,
                         'hashtags': hashtags
                         }
            videoList.append(videoDict)


    video_captions = process_yt_transcripts(video_ids)
    # map the array of embeddings to caption.keys
    
    # video_embeddings = dict(zip(video_captions.keys(),
    #                             get_embeddings([caption['caption'] for caption in video_captions.values()], "text-embedding-3-large")))
    
    # Calculate the similarity between the seed video and the other videos
    # if seed_id:
    #     seed_content = video_captions[seed_id]['caption']
        
    # seed_video_embedding = get_embedding(seed_content, "text-embedding-3-large")
    # similarity_scores = {}
    # for video_id in video_embeddings.keys():
    #     similarity_scores[video_id] = cosine_similarity(seed_video_embedding, video_embeddings[video_id])
    
    # zip the similarity scores with videoList
    # fe_yt_videos = []
    # for video in videoList:
    #     video['similarity_score'] = similarity_scores.get(video['videoId'],0)
    #     ft_yt_video = {'Published At': video['publishedAt'],
    #                    'Title': video['title'],
    #                     'Description': video['description'],
    #                     #'Channel Id': video['channelId'],
    #                     'Likes': video['likeCount'],
    #                     'Views': video['viewCount'],
    #                     'Comments': video['commentCount'],
    #                     'URL': 'https://www.youtube.com/watch?v=' + video['videoId'],
    #                     'Similarity Score': video['similarity_score']*100
            
    #     }
    #     fe_yt_videos.append(ft_yt_video)
    # processBar.empty()


    return videoList, video_captions



def get_yt_transcript(video_id):
    #print("Processing: " + video_id)
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        original_caption = None
        translated_caption = None

        for index, transcript in enumerate(transcript_list):
            if index <= 1 and 'English' in transcript.language:
                caption_raw = transcript.fetch()
                original_caption = process_captions(caption_raw)
                if original_caption != "":
                    return video_id, transcript.language, caption_raw, original_caption

            elif index == 0 and 'English' not in transcript.language:
                caption_raw = transcript.translate('en').fetch()
                translated_caption = process_captions(caption_raw)
                return video_id, transcript.language, caption_raw, translated_caption
        return video_id, None, None, None
    except Exception as e:
        #print(f"Error processing video ID {video_id}: {e}")
        return video_id, None, None, None

def process_yt_transcripts(yt_video_ids: list)-> dict:
    captions = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(get_yt_transcript, video_id) for video_id in yt_video_ids]
        for future in concurrent.futures.as_completed(futures):
            video_id, language, caption_raw, caption = future.result()
            captions[video_id] = {'language': language, 'caption': caption}
    return captions


def get_tt_transcript(tt_post_details: list[dict]) -> list[dict]:
    for post_details in tt_post_details:
        # Get post subtitles
        for subtitleInfo in post_details["video"]["subtitleInfos"]:
            if subtitleInfo['Source'] == 'ASR':
                url = subtitleInfo["Url"].replace("https://v16-webapp.tiktok.com/", "https://v16-cla.tiktokcdn.com/")
                response = requests.get(url).text
                lines = response.strip().split("\n\n")
                subtitles = []
                for line in lines:
                    if "-->" in line:
                        if line.startswith("\n"):
                            line = line[2:]
                        times, subtitle_text = line.split("\n")
                        start, end = times.split(" --> ")
                        start = start.strip()
                        end = end.strip()
                        subtitle_text = subtitle_text.strip()
                        subtitle = {"start": start, "end": end, "text": subtitle_text}
                        subtitles.append(subtitle)

                subtitleInfo["subtitles"] = subtitles
                
    return tt_post_details

async def get_tt_posts_details(post_ids, c):
    # Create a list of post ids
    post_details = []
    print(f"Post IDs: {post_ids}")  # Add this line
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(c.get_post_details, post_id) for post_id in post_ids]
        for future in concurrent.futures.as_completed(futures):
            post_detail = future.result()
            post_details.append(post_detail)
    return post_details

async def add_tt_subtitle(tt_post_details: list):
    async def fetch_subtitle(subtitleInfo):
        url = subtitleInfo["Url"].replace("https://v16-webapp.tiktok.com/", "https://v16-cla.tiktokcdn.com/")
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(url).text)
        lines = response.strip().split("\n\n")
        subtitles = []
        for line in lines:
            if "-->" in line:
                if line.startswith("\n"):
                    line = line[2:]
                times, subtitle_text = line.split("\n")
                start, end = times.split(" --> ")
                start = start.strip()
                end = end.strip()
                subtitle_text = subtitle_text.strip()
                subtitle = {"start": start, "end": end, "text": subtitle_text}
                subtitles.append(subtitle)
        subtitleInfo["subtitles"] = subtitles
        return subtitleInfo

    async def get_tt_transcript(tt_post_details):
        tasks = []
        for post_details in tt_post_details:
            for subtitleInfo in post_details["video"]["subtitleInfos"]:
                if subtitleInfo['Source'] == 'ASR':
                    tasks.append(fetch_subtitle(subtitleInfo))
        return await asyncio.gather(*tasks)

    # Example usage
    subtitles = await (get_tt_transcript(tt_post_details))

    # Insert the subtitles into the post details
    for post_details in tt_post_details:
        for subtitleInfo in post_details["video"]["subtitleInfos"]:
            if subtitleInfo['Source'] == 'ASR':
                subtitleInfo["subtitles"] = [subtitle['subtitles'] for subtitle in subtitles if subtitleInfo["Url"] == subtitle["Url"]][0]
    return tt_post_details

def optimized_tt_post_details(tt_post_details: list[dict]) -> list[dict]:
    optimized_posts_details = []
    for post in tt_post_details:
        subtitles = next((sub['subtitles'] for sub in post['video']['subtitleInfos'] if sub and sub['Source'] == 'ASR'), None)
        processed_transcript = process_captions(subtitles) if subtitles else None
        
        optimized_post = {
            'post_id': post['id'],
            'create_datetime': post['createTime'],
            'description': post['desc'],
            'music_title': post['music']['title'],
            'author_id': post['author']['id'],
            'author_unique_id': post['author']['uniqueId'],
            'like_count': post['stats']['diggCount'],
            'share_count': post['stats']['shareCount'],
            'comment_count': post['stats']['commentCount'],
            'play_count': post['stats']['playCount'],
            'video_duration': post['video']['duration'],
            'suggested_words': post['suggestedWords'],
            'location_created': post.get('locationCreated'),
            'content_location': post.get('contentLocation'),
            'diversification_labels': post.get('diversificationLabels'),
            'caption_raw': subtitles,
            'caption': processed_transcript
        }
        optimized_posts_details.append(optimized_post)
    return optimized_posts_details

async def process_tt_posts(post_ids, tt_client, seed_id = None, seed_content = None) -> list[dict]:
    # Add subtitles to the post details
    
    tt_post_details = await get_tt_posts_details(post_ids, tt_client)
    tt_post_details = await add_tt_subtitle(tt_post_details)
    # Optimize the post details
    optimized_posts_details = optimized_tt_post_details(tt_post_details)
    video_captions = {}
    for post in optimized_posts_details:
        if post['caption']:
            video_captions[post['post_id']] = {'caption': post['caption'], 'caption_raw': post['caption_raw']}
    
    video_embeddings = dict(zip(video_captions.keys(),
                            get_embeddings([caption['caption'] for caption in video_captions.values()], "text-embedding-3-large")))
    
    # Calculate the similarity between the seed video and the other videos
    if seed_id:
        seed_content = video_captions[seed_id]['caption']
        
    seed_video_embedding = get_embedding(seed_content, "text-embedding-3-large")
    similarity_scores = {}
    for video_id in video_embeddings.keys():
        similarity_scores[video_id] = cosine_similarity(seed_video_embedding, video_embeddings[video_id])

    fe_tt_videos = []
    for video in optimized_posts_details:
        video['similarity_score'] = similarity_scores.get(video['videoId'],0)
        fe_tt_video = {'Published At': datetime.fromtimestamp(video['create_datetime']).strftime('%Y-%m-%d %H:%M:%S'),
                       'Title': video['title'],
                        'Description': video['description'],
                        'Author': video['author_unique_id'],
                        'Likes': video['like_count'],
                        'Shares': video['share_count'],
                        'Comments': video['commentCount'],
                        'Views': video['play_count'],
                        'URL': 'https://www.tiktok.com/@' + video['author_unique_id'] + '/video/' + video['post_id'],
                        'Similarity Score': video['similarity_score']*100
            
        }
        fe_tt_videos.append(fe_tt_video)
    
    return fe_tt_videos, optimized_posts_details, video_captions
# Example usage:
if __name__ == '__main__':
    #YT video id
    yt_video_ids = ['USrvVn2Bl2E',
                    'deJ_V1qklk8',
                    'El8ARW_Iy7c',
                    'NTB24wJZOS4',
                    'BvbPCQx5KXU',
                    'nV4vZo6A-Ak',
                    'WCuLskqUsZ0',
                    '_wPhqfk8lVg',
                    '3UN99-3kJ_Y',
                    '-WGNf3H3XI4']
    video_captions = process_yt_videos(yt_video_ids, 'USrvVn2Bl2E')
    print(video_captions)