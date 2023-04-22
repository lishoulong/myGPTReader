import logging
import html2text
import feedparser
import validators
import re
import requests
import lxml.html
from lxml.html.clean import clean_html
from youtube_transcript_api import YouTubeTranscriptApi


def get_urls(urls):
    rss_urls = []
    page_urls = []
    youtube_urls = []
    for url in urls:
        if validators.url(url):
            feed = feedparser.parse(url)
            if hasattr(feed, 'version') and feed.version:
                rss_urls.append(url)
            elif check_if_youtube_url(url):
                youtube_urls.append(url)
            else:
                page_urls.append(url)
    return {'rss_urls': rss_urls, 'page_urls': page_urls, 'youtube_urls': youtube_urls}


def scrape_website(url: str) -> str:
    result = _parse_url_or_html(url)
    try:
        text_content = html2text.html2text(result)
        print(f'result url 成功=>{url}')
        return text_content
    except Exception as e:
        logging.warning(f"html2text.html2text error: {e}")
        return f"Error: {e}"


def get_text_from_urls(urls):
    documents = []
    for url in urls['page_urls']:
        document = scrape_website(url)
        documents.append(document)
    if len(urls['youtube_urls']) > 0:
        for url in urls['youtube_urls']:
            video_id = get_youtube_video_id(url)
            document = get_text_from_youtube_id(video_id)
            if (document is not None):
                documents.append(document)
            else:
                documents.append(
                    f"Can't get transcript from youtube video: {url}")
    return documents


def _parse_url_or_html(url_or_html: str) -> lxml.html.Element:
    """
    Given URL or HTML, return lxml.html.Element
    """
    # coerce to HTML
    orig_url = None
    if url_or_html.startswith("http"):
        orig_url = url_or_html
        url_or_html = requests.get(url_or_html).text
    # collapse whitespace
    url_or_html = re.sub("[ \t]+", " ", url_or_html)
    doc = lxml.html.fromstring(url_or_html)
    if orig_url:
        doc.make_links_absolute(orig_url)
    cleaned_html = clean_html(doc)
    html_string = lxml.html.tostring(cleaned_html, encoding="unicode")
    return html_string


def check_if_youtube_url(url):
    return 'youtube.com' in url or 'youtu.be' in url


def get_text_from_youtube_id(video_id):
    if video_id is None:
        return None
    transcript = get_youtube_transcript(video_id)
    if transcript is None:
        return None
    return transcript


def get_youtube_transcript(video_id: str) -> str:
    try:
        srt = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ""
        for chunk in srt:
            transcript = transcript + chunk["text"] + "\n"
    except Exception as e:
        logging.error(f"get_youtube_transcript Error: {e} - {video_id}")
        transcript = None
    return transcript


def get_youtube_video_id(url):
    if url is None:
        return None
    if 'youtube.com' in url:
        return url.split('v=')[-1]
    if 'youtu.be' in url:
        return url.split('/')[-1]
    return None
