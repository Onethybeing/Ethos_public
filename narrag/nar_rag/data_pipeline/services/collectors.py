"""
Data Collectors - Fetch content from various sources

Sources:
- RSS feeds (TechCrunch, The Verge, Wired, BBC, etc.)
- Hacker News (via Algolia API)
"""

import feedparser
import requests
import datetime
from typing import List, Dict, Any, Optional
import logging
import time
import re
from dateutil import parser as date_parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCollector:
    """
    Collects articles and posts from various open sources.
    
    No authentication required - uses public APIs and RSS feeds.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NarrativeMemoryBot/1.0 (Research Project - Educational)'
        })
    
    # ================== RSS Feeds ==================
    
    def fetch_rss(self, url: str, source_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch articles from an RSS feed with robust parsing.
        """
        logger.info(f"Fetching RSS: {source_name}")
        
        try:
            # Add timeout to fetching
            feed = feedparser.parse(url)
            
            if feed.bozo:
                logger.warning(f"RSS warning for {source_name}: {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries[:limit]:
                # Extract timestamp safely
                timestamp = self._parse_rss_date(entry)
                
                # Clean text
                summary = entry.get("summary", "") or entry.get("description", "")
                text = self._clean_html(summary)
                
                # Get image
                image_url = self._extract_rss_image(entry)
                
                items.append({
                    "title": entry.get("title", "").strip(),
                    "text": text,
                    "url": entry.get("link", ""),
                    "source": source_name,
                    "timestamp": timestamp,
                    "image_url": image_url
                })
            
            logger.info(f"Fetched {len(items)} items from {source_name}")
            return items
            
        except Exception as e:
            logger.error(f"Failed to fetch RSS {source_name}: {e}")
            return []
    
    def _parse_rss_date(self, entry) -> int:
        """Robust date parsing for RSS entries."""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return int(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return int(time.mktime(entry.updated_parsed))
            elif hasattr(entry, 'published'):
                dt = date_parser.parse(entry.published)
                return int(dt.timestamp())
            elif hasattr(entry, 'updated'):
                dt = date_parser.parse(entry.updated)
                return int(dt.timestamp())
        except Exception:
            pass
            
        # Fallback to now
        return int(datetime.datetime.now().timestamp())
    
    def _extract_rss_image(self, entry) -> Optional[str]:
        """Extract image URL from RSS entry looking at multiple fields."""
        # 1. Check media_content (common in standard RSS)
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if 'image' in media.get('medium', '') or 'image' in media.get('type', ''):
                    return media.get('url')
        
        # 2. Check media_thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url')
        
        # 3. Check enclosures (podcasts/standard attachments)
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get('type', '').startswith('image'):
                    return enc.get('href') or enc.get('url')
        
        # 4. Check standard aggregators fields
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('rel') == 'enclosure' and link.get('type', '').startswith('image'):
                    return link.get('href')
        
        # 5. Try parsing from content/summary HTML (last resort)
        content = entry.get('content', [{'value': ''}])[0].get('value', '')
        summary = entry.get('summary', '')
        
        for html in [content, summary]:
            if html:
                matches = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
                if matches:
                    return matches.group(1)
                    
        return None
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and entities."""
        if not text:
            return ""
        # Remove tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Fix entities
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()
    
    # ================== Hacker News ==================
    
    def fetch_hackernews(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch top stories from Hacker News via Algolia API.
        Filter for stories that likely have decent discussions or technical narratives.
        """
        logger.info("Fetching Hacker News...")
        
        # Search for recent regular stories (not jobs, etc)
        url = f"https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=points>20&hitsPerPage={limit}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            hits = response.json().get("hits", [])
            items = []
            
            for hit in hits:
                story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                title = hit.get("title", "").strip()
                
                # HN doesn't provide body text usually, so we use title + comment count as proxy for importance
                text = f"Hacker News discussion with {hit.get('num_comments', 0)} comments."
                
                items.append({
                    "title": title,
                    "text": text,
                    "url": story_url,
                    "source": "hackernews",
                    "timestamp": hit.get("created_at_i", int(datetime.datetime.now().timestamp())),
                    "image_url": None
                })
            
            logger.info(f"Fetched {len(items)} stories from HN")
            return items
            
        except Exception as e:
            logger.error(f"Failed to fetch Hacker News: {e}")
            return []
    
    # ================== Bulk Fetch ==================
    
    def fetch_all(self) -> List[Dict[str, Any]]:
        """
        Fetch from all configured sources.
        """
        all_items = []
        
        # --- Tech & AI ---
        tech_sources = {
            "TechCrunch": "https://techcrunch.com/feed/",
            "The Verge": "https://www.theverge.com/rss/index.xml",
            "Wired": "https://www.wired.com/feed/rss",
            "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
            "Engadget": "https://www.engadget.com/rss.xml",
            "VentureBeat": "https://venturebeat.com/feed/",
            "MIT Tech Review": "https://www.technologyreview.com/feed/",
            "9to5Mac": "https://9to5mac.com/feed/",
            "The Register": "https://www.theregister.com/headlines.atom",
        }
        
        # --- World News ---
        news_sources = {
            "BBC Tech": "http://feeds.bbci.co.uk/news/technology/rss.xml",
            "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
            "Reuters World": "https://www.reutersagency.com/feed/",
            "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
            "NPR News": "https://feeds.npr.org/1001/rss.xml",
            "The Guardian": "https://www.theguardian.com/world/rss",
        }
        
        # --- Business & Finance ---
        business_sources = {
            "CNBC": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
            "Forbes": "https://www.forbes.com/innovation/feed/",
            "Bloomberg": "https://feeds.bloomberg.com/technology/news.rss",
        }
        
        # --- Science ---
        science_sources = {
            "Nature News": "https://www.nature.com/nature.rss",
            "Science Daily": "https://www.sciencedaily.com/rss/all.xml",
            "Phys.org": "https://phys.org/rss-feed/",
        }
        
        all_sources = {**tech_sources, **news_sources, **business_sources, **science_sources}
        
        for name, url in all_sources.items():
            items = self.fetch_rss(url, name, limit=10)
            all_items.extend(items)
            time.sleep(0.3)
        
        # Hacker News
        items = self.fetch_hackernews(limit=30)
        all_items.extend(items)
        
        logger.info(f"Total items collected: {len(all_items)}")
        return all_items


# Singleton instance
collector = DataCollector()
