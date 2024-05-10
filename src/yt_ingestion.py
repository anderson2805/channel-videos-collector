
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st

from src.service import create_yt_service
from pytubefix import Channel
# api_file = open("./data/yt_secret.txt", "r")
# apis = api_file.read()
apis = st.secrets["keys"]
api_list = apis.split("\n")
API_KEY = api_list.pop()
api_list = [API_KEY] + api_list
service = create_yt_service(API_KEY)


def getVideoDetail(video_ids: list, service = service) -> str:
    part_string = 'contentDetails,statistics,snippet,topicDetails,recordingDetails,localizations'

    response = service.videos().list(
        part=part_string,
        id=video_ids
    ).execute()

    return response


def getChannelDetail(channel_ids: list, service = service) -> str:
    """Call YT Channel API

    Args:
        channel_ids (list): list of channel details

    Returns:
        str: html return from api, containing channels details, stated in part_string
    """
    try:
        part_string = 'snippet,brandingSettings,statistics,topicDetails,localizations'
        response = service.channels().list(
            part=part_string,
            id=channel_ids,
            maxResults=50
        ).execute()
    except:
        part_string = 'snippet,brandingSettings,statistics,localizations'
        response = service.channels().list(
            part=part_string,
            id=channel_ids,
            maxResults=50
        ).execute()
    return response

def getCommentDetail(videoId: str, service = service) -> str:
    """Call YT Channel API

    Args:
        video_ids (list): a videoId that comments will be extracted from.

    Returns:
        str: html return from api, containing comments details, stated in part_string
    """
    responses = []
    part_string = 'id, snippet, replies'
    nextPageToken = ''
    pageNumber = 0
    while (nextPageToken!= 'end' or pageNumber == 0):
        pageNumber += 1
        response = service.commentThreads().list(
            part=part_string,
            videoId=videoId,
            maxResults=100,
            pageToken=nextPageToken,
        ).execute()
        nextPageToken = response.get('nextPageToken','end')
        # Store the current page of results
        responses = responses + response['items']
    return responses

def getRecentChannelVids(channel_ids: list, recent_x: int) -> list:
    """Return list of channel vids ids (no API needed)

    Args:
        channel_ids (list): List of channel ids
        recent_x (int): x recents videos to ingest

    Returns:
        list: dictionary of channel id and their list of video url
        {
            channelId: 'channelId',
            videoIds: ['videoUrl1', 'videoUrl2' etc,...]
        }
    """
    result = []
    for channel_id in channel_ids:
        url = "https://www.youtube.com/channel/" + channel_id + '/videos'
        c = Channel(url)
        result.append({
            'channelId': channel_id,
            'videoUrls': [videoUrl[32:] for videoUrl in c.video_urls[:recent_x]]
        })
    return result


# def getRelatedVideoIds(relatedToVideoId: str, service = service) -> list:
#     """DEPRECIATED SINCE AUG 2023"""
#     maxResults = 50
#     pageCount = 0
#     videoIdsList = []
#     response = {}
#     try:
#         while (response.get('nextPageToken') is not None or pageCount == 0):
#             response = service.search().list(
#                 part='id',
#                 relatedToVideoId=relatedToVideoId,
#                 maxResults=maxResults,
#                 pageToken=response.get('nextPageToken'),
#                 type='video'
#             ).execute()
#             pageCount += 1
#             # Store the current page of results
#             for item in response['items']:
#                 videoIdsList.append(item['id']['videoId'])
#     except Exception as e:
#         error = e.error_details[0]['reason']
#         print(error)
#         if(error == 'quotaExceeded'):
#             API_KEY = api_list[2]
#             service = create_yt_service(API_KEY)
#             while (response.get('nextPageToken') is not None or pageCount == 0):
#                 response = service.search().list(
#                     part='id',
#                     relatedToVideoId=relatedToVideoId,
#                     maxResults=maxResults,
#                     pageToken=response.get('nextPageToken'),
#                     type='video'
#                 ).execute()
#                 pageCount += 1
#                 # Store the current page of results
#                 for item in response['items']:
#                     videoIdsList.append(item['id']['videoId'])

#     relatedVideoIds = list(set(videoIdsList))

#     return relatedVideoIds


def get_video_details(VideoIds: list) -> bool:
    resultsChunks = [VideoIds[i:i + 50]
                     for i in range(0, len(VideoIds), 50)]
    for result in resultsChunks:
        try:
            getVideoDetail(",".join(result))
        except:
            getVideoDetail(",".join(result), switchService())
    return True


def query_keywords(keyword: str, seedId: str = None, order: str = 'relevance', videoCaption: str = "any", channelId: str = "", pageLimit=2, service = service, api_list = api_list) -> list:
    """Search youtube based on youtube search API
    Source: https://developers.google.com/youtube/v3/docs/search/list

    Args:
        keyword (str): query
        order (str, optional): The order parameter specifies the method that will be used to order resources in the API response. Defaults to 'relevance'.
        Acceptable values are:
            date: Resources are sorted in reverse chronological order based on the date they were created.
            rating: Resources are sorted from highest to lowest rating.
            relevance: Resources are sorted based on their relevance to the search query. This is the default value for this parameter.
            title: Resources are sorted alphabetically by title.
            videoCount: Channels are sorted in descending order of their number of uploaded videos.
            viewCount: Resources are sorted from highest to lowest number of views. For live broadcasts, videos are sorted by number of concurrent viewers while the broadcasts are ongoing.
        videoCaption (str, optional): The videoCaption parameter indicates whether the API should filter video search results based on whether they have captions. If you specify a value for this parameter, you must also set the type parameter's value to video.
        Defaults to "any".
        Acceptable values are:
            any: Do not filter results based on caption availability.
            closedCaption: Only include videos that have captions.
            none: Only include videos that do not have captions.
        pageLimit (int, optional): 50 max return per page. Defaults to 2.

    Returns:
        list: list of video ids
    """
    maxResults = 50
    videoIdsList = [seedId]
    response = {}
    query = keyword
    pageCount = 0


    while (response.get('nextPageToken') is not None or pageCount == 0) and pageCount != pageLimit:
        try:
            response = service.search().list(
                part='id,snippet',
                maxResults=maxResults,
                q=query,
                channelId = channelId,  
                pageToken=response.get('nextPageToken'),
                type='video',
                order=order,
                videoCaption=videoCaption
            ).execute()
            pageCount += 1
            print("Next page found, downloading", response.get('nextPageToken'))
            # Store the current page of results
            for item in response['items']:
                videoIdsList.append(item['id']['videoId'])
        except Exception as e:
            error = e['status_code']
            if(error == 403):
                API_KEY = api_list[2]
                service = create_yt_service(API_KEY)
                response = service.search().list(
                part='id,snippet',
                maxResults=maxResults,
                q=query,
                channelId = channelId,  
                pageToken=response.get('nextPageToken'),
                type='video',
                order=order,
                videoCaption=videoCaption
                ).execute()
                pageCount += 1
                print("Next page found, downloading", response.get('nextPageToken'))
                # Store the current page of results
                for item in response['items']:
                    videoIdsList.append(item['id']['videoId'])

    searchVideoIDs = list(set(videoIdsList))
    return searchVideoIDs


def queryChannelVidIds(channelId: str, publishedAfter: str = '2022-12-29', publishedBefore: str = '2022-11-29', limit=3, service = service):
    maxResults = 50
    response = {}
    videoIdsList = []
    pageCount = 0
    
    while (response.get('nextPageToken') is not None or pageCount == 0) and pageCount != limit:
        response = service.search().list(
            part='snippet',
            maxResults=maxResults,
            order='date',
            publishedAfter = publishedAfter + 'T00:00:00Z',
            # publishedBefore = publishedBefore + 'T00:00:00Z',
            channelId=channelId,
            pageToken=response.get('nextPageToken')
        ).execute()
        pageCount += 1
        print("Next page found, downloading", response.get('nextPageToken'))
        videoIdsList += [item['id'].get('videoId') for item in response['items'] if item['id'].get('videoId')]
    return videoIdsList

def get_channel_video_ids(channelId: str, publishedAfter: str = '2022-12-29', publishedBefore: str = '2022-11-29', limit=3) -> bool:
    global service
    try:
        return queryChannelVidIds(channelId, publishedAfter, publishedBefore, limit, service)
    except:
        service = switchService()
        return queryChannelVidIds(channelId, publishedAfter, publishedBefore, limit, service)


def ingest(ingestFunc):
    try:
        return ingestFunc
    except:
        print("SWITCH API")
        API_KEY = api_list.pop()
        api_list = [API_KEY] + api_list
        service = create_yt_service(API_KEY)
        return ingestFunc

def switchService(api_list=api_list):
    global service
    API_KEY = api_list.pop()
    print("SWITCH API")
    print(API_KEY)
    api_list = [API_KEY] + api_list
    service = create_yt_service(API_KEY) 
    return service 

if __name__ == "__main__":
    seedId = "JZ1Vols480M"
    order = "relevance"
    pageLimit =  2
    videoCaption = "any"
    print(API_KEY)
    print(query_keywords("America German Economy", seedId = "JZ1Vols480M", pageLimit = 1, videoCaption= "closedCaption"))