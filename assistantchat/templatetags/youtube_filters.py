from django import template
from django.template.defaultfilters import stringfilter
from urllib.parse import urlparse, parse_qs


register = template.Library()


@register.filter
def youtube_embed_url(url):
    """Convert YouTube URL to embed URL"""
    if not url:
        return ''
        
    parsed_url = urlparse(url)
    
    # Handle youtube.com/watch?v=VIDEO_ID
    if 'youtube.com' in parsed_url.netloc and 'watch' in parsed_url.path:
        query = parse_qs(parsed_url.query)
        if 'v' in query:
            video_id = query['v'][0]
            return f'https://www.youtube.com/embed/{video_id}'
    
    # Handle youtu.be/VIDEO_ID
    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path.lstrip('/')
        return f'https://www.youtube.com/embed/{video_id}'
    
    # Return original URL if we can't parse it
    return url