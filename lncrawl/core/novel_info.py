import math
import re
from typing import Dict

from ..models import Chapter, Volume
from .crawler import Crawler
from .exeptions import LNException


def __format_title(text):
    return re.sub(r"\s+", " ", str(text)).strip().title()


def _get_id_safely(x):
    """Helper to safely extract and parse an ID into a number"""
    val = x.get('id') if isinstance(x, dict) else getattr(x, 'id', 0)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0


def _extract_chapter_number(title: str, url: str) -> float:
    """Attempts to intelligently find the chapter number to prevent unordered page errors"""
    title = str(title).lower() if title else ""
    url = str(url).lower() if url else ""
    
    # 1. Match explicit chapter text
    match = re.search(r'(?:chapter|ch|ch\.|#)\s*(\d+(\.\d+)?)', title)
    if match: return float(match.group(1))
    
    # 2. Match chapter text in URLs
    match = re.search(r'(?:chapter|ch|ch-)(\d+(\.\d+)?)', url)
    if match: return float(match.group(1))
    
    # 3. Match leading numbers (e.g., "12 - New Beginnings")
    match = re.search(r'^\s*(\d+(\.\d+)?)', title)
    if match: return float(match.group(1))
    
    # 4. Match trailing numbers in URLs (e.g., "/post-12/")
    match = re.search(r'-(\d+(\.\d+)?)/?$', url)
    if match: return float(match.group(1))
    
    return -1


def __format_volume(crawler: Crawler, vol_id_map: Dict[int, int]):
    if crawler.volumes:
        crawler.volumes = [
            vol if isinstance(vol, Volume) else Volume(**vol)
            for vol in sorted(crawler.volumes, key=_get_id_safely)
        ]
    else:
        for i in range(math.ceil(len(crawler.chapters) / 100)):
            crawler.volumes.append(Volume(id=i + 1))

    for index, vol in enumerate(crawler.volumes):
        if not isinstance(vol.id, int) or vol.id < 0:
            raise LNException(f"Invalid volume id at index {index}")
        vol.title = __format_title(vol.title or f"Volume {vol.id}")
        vol.start_chapter = len(crawler.chapters)
        vol.final_chapter = 0
        vol.chapter_count = 0
        vol_id_map[vol.id] = index


def __format_chapters(crawler: Crawler, vol_id_map: Dict[int, int]):
    crawler.chapters = [
        chap if isinstance(chap, Chapter) else Chapter(**chap)
        for chap in crawler.chapters
    ]
    
    # Sort smartly using extracted number > original ID > index
    for index, item in enumerate(crawler.chapters):
        num = _extract_chapter_number(item.title, item.url)
        original_id = _get_id_safely(item)
        vol = item.volume if item.volume else 0
        
        if num >= 0:
            item._sort_key = (vol, num)
        elif original_id > 0:
            item._sort_key = (vol, original_id)
        else:
            item._sort_key = (vol, index)

    crawler.chapters.sort(key=lambda c: c._sort_key)

    # Clean attributes and re-assign IDs to strictly continuous numbers (fixes out-of-order file writing)
    for index, item in enumerate(crawler.chapters):
        item.id = index + 1
        if hasattr(item, '_sort_key'):
            delattr(item, '_sort_key')

        if item.volume:
            vol_index = vol_id_map.get(item.volume, -1)
        else:
            vol_index = vol_id_map.get(index // 100 + 1, -1)
            
        if vol_index < 0 or vol_index >= len(crawler.volumes):
            vol_index = 0
            if not crawler.volumes:
                crawler.volumes.append(Volume(id=1, title="Volume 1"))
                vol_id_map[1] = 0

        volume = crawler.volumes[vol_index]
        item.volume = volume.id
        item.volume_title = volume.title
        item.title = __format_title(item.title or f"#{item.id}")

        volume.chapter_count = (volume.chapter_count or 0) + 1
        if not volume.start_chapter or item.id < volume.start_chapter:
            volume.start_chapter = item.id
        if not volume.final_chapter or item.id > volume.final_chapter:
            volume.final_chapter = item.id


def format_novel(crawler: Crawler):
    crawler.novel_title = __format_title(crawler.novel_title)
    crawler.novel_author = __format_title(crawler.novel_author)
    vol_id_map: Dict[int, int] = {}
    __format_volume(crawler, vol_id_map)
    __format_chapters(crawler, vol_id_map)
    crawler.volumes = [x for x in crawler.volumes if x.chapter_count > 0]
    
    # Fix volumes order caused by paginated fetch chunks resolving backwards
    crawler.volumes.sort(key=lambda x: x.start_chapter or 0)
    
    # Re-normalize volume definitions so they map perfectly into sequential ranges
    new_vol_id_map = {vol.id: i + 1 for i, vol in enumerate(crawler.volumes)}
    for vol in crawler.volumes:
        if vol.title:
            vol.title = re.sub(r'(?i)^volume \d+', f'Volume {new_vol_id_map[vol.id]}', vol.title)
        vol.id = new_vol_id_map[vol.id]
        
    for chapter in crawler.chapters:
        chapter.volume = new_vol_id_map.get(chapter.volume, chapter.volume)