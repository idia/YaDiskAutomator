#!/usr/bin/env python3
"""
Yandex Disk Video Downloader

Downloads streaming videos from a public Yandex Disk folder and uploads them
to a specified folder on your own Yandex Disk, preserving file names and folder structure.
"""

import os
import sys
import re
import argparse
import requests
from typing import List, Dict, Tuple, Optional, Any
from urllib.parse import quote
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import yt_dlp

# Exit codes
EXIT_SUCCESS = 0
EXIT_INVALID_ARGS = 1
EXIT_ERROR = 2

# Video file extensions
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.3gp', '.ogv']


def filter_video_files(items: List[Dict]) -> List[Dict]:
    """
    Filter items to only include video files.
    
    Args:
        items: List of file items
    
    Returns:
        List of video file items only
    """
    video_files = []
    for item in items:
        name = item.get('name', '')
        if any(name.endswith(ext) for ext in VIDEO_EXTENSIONS):
            video_files.append(item)
    return video_files


def load_env_file() -> None:
    """Load environment variables from .env file if it exists."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)


def get_oauth_token() -> str:
    """
    Get OAuth token from environment variable or .env file.
    
    Returns:
        OAuth token string
    
    Raises:
        ValueError: If token is not found
    """
    token = os.getenv('YANDEX_OAUTH_TOKEN')
    if not token:
        raise ValueError("YANDEX_OAUTH_TOKEN not found in environment variables or .env file")
    return token


def get_public_folder_url() -> str:
    """
    Get public folder URL from environment variable or .env file.
    
    Returns:
        Public folder URL string
    
    Raises:
        ValueError: If URL is not found
    """
    url = os.getenv('YANDEX_PUBLIC_FOLDER_URL')
    if not url:
        raise ValueError("YANDEX_PUBLIC_FOLDER_URL not found in environment variables or .env file")
    return url


def get_destination_path() -> str:
    """
    Get destination path from environment variable or .env file.
    
    Returns:
        Destination path string
    
    Raises:
        ValueError: If path is not found
    """
    path = os.getenv('YANDEX_DESTINATION_PATH')
    if not path:
        raise ValueError("YANDEX_DESTINATION_PATH not found in environment variables or .env file")
    return path


def validate_public_url(url: str) -> bool:
    """
    Validate public Yandex Disk folder URL format.
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL is valid, False otherwise
    """
    return ('disk.yandex.ru/d/' in url or 'yadi.sk/d/' in url) and url.startswith('http')


def validate_destination_path(path: str) -> bool:
    """
    Validate destination path format (must start with /).
    
    Args:
        path: Path to validate
    
    Returns:
        True if path is valid, False otherwise
    """
    return path.startswith('/') and len(path) > 1


def collect_all_folders(page, public_url: str, base_path: str, verbose: bool, processed_folder_urls: set) -> List[Dict]:
    """
    Collect all folders from current page WITHOUT entering them.
    Returns list of folder info: {'name': cleaned_name, 'url': full_url, 'path': folder_path}
    """
    import re
    folders = []
    
    # Check for captcha first
    captcha_selectors = [
        'text=/[Рр]обот|[Cc]aptcha|[Пп]одтвердите/',
        '[class*="captcha"]',
        '[class*="Captcha"]',
        '[id*="captcha"]',
        '[id*="Captcha"]',
        'iframe[src*="captcha"]',
        'iframe[src*="smartcaptcha"]'
    ]
    
    captcha_solved = False
    while not captcha_solved:
        captcha_found = False
        for selector in captcha_selectors:
            try:
                elements = page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    captcha_found = True
                    break
            except:
                continue
        
        if captcha_found:
            print("\n" + "="*60)
            print("CAPTCHA DETECTED!")
            print("Please solve the captcha in the browser window.")
            print("After solving, press ENTER to continue...")
            print("="*60 + "\n")
            input("Press ENTER after solving captcha...")
            page.wait_for_timeout(2000)
            
            # Check again if captcha is still present
            captcha_still_present = False
            for selector in captcha_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        captcha_still_present = True
                        break
                except:
                    continue
            
            if not captcha_still_present:
                captcha_solved = True
                print("Captcha solved! Continuing...\n")
        else:
            captcha_solved = True
    
    # Wait a bit for content to load after captcha
    page.wait_for_timeout(2000)
    
    # Get all elements - need to query fresh after captcha/navigation
    all_elements = page.query_selector_all(
        'a[href*="/d/"], '
        '.file-item, '
        '[data-file-name], '
        '.listing-item, '
        '.resource-item, '
        '.listing-item__title, '
        '.listing-item__title-link, '
        '.resource__name, '
        '.resource__title, '
        '.file__name, '
        'a.resource__name-link, '
        'a[class*="resource"], '
        'a[class*="file"], '
        'a[class*="listing"]'
    )
    
    if verbose:
        print(f"    Found {len(all_elements)} elements with primary selectors")
    
    if len(all_elements) == 0:
        all_elements = page.query_selector_all('a[href]')
        if verbose:
            print(f"    Found {len(all_elements)} elements with fallback selector")
    
    # Process elements - re-query if navigation occurs
    processed_count = 0
    for idx in range(len(all_elements)):
        # Re-query elements if we've processed many (in case of navigation)
        if idx > 0 and idx % 5 == 0:
            try:
                # Quick check if current element is still valid
                test_elem = all_elements[idx]
                test_elem.get_attribute('data-file-name')
            except:
                # Elements became invalid, re-query
                if verbose:
                    print(f"    Elements became invalid, re-querying...")
                all_elements = page.query_selector_all(
                    'a[href*="/d/"], '
                    '.file-item, '
                    '[data-file-name], '
                    '.listing-item, '
                    '.resource-item, '
                    '.listing-item__title, '
                    '.listing-item__title-link, '
                    '.resource__name, '
                    '.resource__title, '
                    '.file__name, '
                    'a.resource__name-link, '
                    'a[class*="resource"], '
                    'a[class*="file"], '
                    'a[class*="listing"]'
                )
                if len(all_elements) == 0:
                    all_elements = page.query_selector_all('a[href]')
                if idx >= len(all_elements):
                    break
        
        element = all_elements[idx]
        processed_count += 1
        try:
            # Get name
            name = (element.get_attribute('data-file-name') or 
                   element.get_attribute('data-resource-name') or
                   element.get_attribute('data-name') or
                   element.get_attribute('title') or
                   element.get_attribute('aria-label') or
                   element.inner_text() or
                   element.text_content())
            
            if not name:
                continue
            
            name = name.strip()
            
            # Skip ignored folders
            if name in ['Аудио', 'Доки']:
                continue
            
            # Check if it's a video file (has extension)
            name_normalized = name.replace('\n', '').replace('\r', '').strip().lower()
            has_video_ext = any(name_normalized.endswith(ext) for ext in VIDEO_EXTENSIONS)
            has_file_ext = any(name_normalized.endswith(ext) for ext in ['.txt', '.pdf', '.doc', '.zip', '.rar', '.jpg', '.png', '.gif', '.json', '.xml', '.mp3', '.wav', '.ogg'])
            
            # If it has video extension, it's a file, not a folder
            if has_video_ext:
                continue
            
            # If it has other file extension, it's a file, not a folder
            if has_file_ext:
                continue
            
            # Try to get href
            href = element.get_attribute('href')
            if not href:
                parent_link = element.query_selector('a[href]')
                if parent_link:
                    href = parent_link.get_attribute('href')
            
            # If no href, try to get URL via click (but don't enter, just get URL)
            if not href:
                try:
                    url_before = page.url
                    # Try single click first to see if we can get href from navigation
                    element.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    current_url = page.url
                    if current_url != url_before and '/d/' in current_url:
                        href = current_url
                        # Navigate back immediately
                        page.goto(url_before, wait_until='domcontentloaded', timeout=15000)
                        page.wait_for_timeout(2000)
                    else:
                        # If click didn't navigate, try double-click
                        page.goto(url_before, wait_until='domcontentloaded', timeout=15000)
                        page.wait_for_timeout(1000)
                        element.dblclick(timeout=5000)
                        page.wait_for_timeout(2000)
                        current_url = page.url
                        if current_url != url_before and '/d/' in current_url:
                            href = current_url
                            # Navigate back immediately
                            page.goto(url_before, wait_until='domcontentloaded', timeout=15000)
                            page.wait_for_timeout(2000)
                except:
                    # If we're already in a folder, try to go back
                    try:
                        if page.url != public_url:
                            page.goto(public_url, wait_until='domcontentloaded', timeout=15000)
                            page.wait_for_timeout(2000)
                    except:
                        pass
                    continue
            
            if not href:
                continue
            
            # Construct full URL
            if href.startswith('/'):
                if 'disk.yandex.ru' in public_url or 'disk.yandex.ru' in href:
                    full_url = f"https://disk.yandex.ru{href}"
                else:
                    full_url = f"https://yadi.sk{href}"
            elif href.startswith('http'):
                full_url = href
            else:
                continue
            
            # Check if already processed
            if full_url in processed_folder_urls:
                continue
            
            # Clean folder name from date/time
            name_normalized = name.replace('\n', ' ').replace('\r', ' ')
            cleaned_name = re.sub(r'\s*\d{1,2}\.\d{1,2}\.\d{2,4}.*$', '', name_normalized).strip()
            if not cleaned_name or len(cleaned_name) < 2:
                cleaned_name = name_normalized.strip()
            
            # Build folder path
            if base_path:
                folder_path = f"{base_path}/{cleaned_name}"
            else:
                folder_path = cleaned_name
            
            # Check for duplicates
            is_duplicate = any(f.get('path') == folder_path or f.get('name') == cleaned_name for f in folders)
            if not is_duplicate:
                folders.append({
                    'name': cleaned_name,
                    'url': full_url,
                    'path': folder_path
                })
                processed_folder_urls.add(full_url)
                if verbose:
                    print(f"    Found folder: {cleaned_name}")
        except Exception as e:
            error_str = str(e)
            if 'destroyed' in error_str.lower() or 'navigation' in error_str.lower() or 'context' in error_str.lower():
                # Element became invalid due to navigation - skip silently
                continue
            else:
                if verbose:
                    print(f"    Warning: Could not process element: {e}")
                continue
    
    if verbose:
        print(f"    Successfully processed {len(folders)} folder(s) from {processed_count} elements")
    
    return folders


def parse_folder_contents(page, folder_url: str, folder_path: str, verbose: bool,
                         cache_dir: str = None, tree_file_path: str = None,
                         destination_path: str = None, oauth_token: str = None,
                         download_immediately: bool = False) -> List[Dict]:
    """
    Enter a folder and collect all video files from it.
    If download_immediately is True, downloads and uploads videos immediately instead of adding to list.
    Returns list of video items with relative_path (empty if download_immediately=True).
    """
    items = []
    
    try:
        # Navigate to folder
        if verbose:
            print(f"  Entering folder: {folder_path}")
        page.goto(folder_url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(3000)
        
        # Check for captcha with loop (like in other functions)
        captcha_selectors = [
            'text=/[Рр]обот|[Cc]aptcha|[Пп]одтвердите/',
            '[class*="captcha"]',
            '[class*="Captcha"]',
            '[id*="captcha"]',
            '[id*="Captcha"]',
            'iframe[src*="captcha"]',
            'iframe[src*="smartcaptcha"]'
        ]
        
        captcha_solved = False
        while not captcha_solved:
            captcha_found = False
            for selector in captcha_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        captcha_found = True
                        break
                except:
                    continue
            
            if captcha_found:
                print("\n" + "="*60)
                print("CAPTCHA DETECTED!")
                print("Please solve the captcha in the browser window.")
                print("After solving, press ENTER to continue...")
                print("="*60 + "\n")
                input("Press ENTER after solving captcha...")
                page.wait_for_timeout(3000)
                
                # Check again if captcha is still present
                captcha_still_present = False
                for selector in captcha_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            captcha_still_present = True
                            break
                    except:
                        continue
                
                if not captcha_still_present:
                    captcha_solved = True
                    print("Captcha solved! Continuing...\n")
                    # Wait a bit more for content to load
                    page.wait_for_timeout(2000)
                    # Re-navigate to ensure page is fully loaded
                    page.goto(folder_url, wait_until='domcontentloaded', timeout=60000)
                    page.wait_for_timeout(3000)
            else:
                captcha_solved = True
        
        # Get all elements - re-query after captcha/navigation
        def get_elements():
            elements = page.query_selector_all(
                'a[href*="/d/"], '
                '.file-item, '
                '[data-file-name], '
                '.listing-item, '
                '.resource-item, '
                '.listing-item__title, '
                '.listing-item__title-link, '
                '.resource__name, '
                '.resource__title, '
                '.file__name, '
                'a.resource__name-link, '
                'a[class*="resource"], '
                'a[class*="file"], '
                'a[class*="listing"]'
            )
            if len(elements) == 0:
                elements = page.query_selector_all('a[href]')
            return elements
        
        all_elements = get_elements()
        
        # Track processed file names to avoid duplicates
        processed_files = set()
        
        file_idx = 0
        for idx in range(len(all_elements)):
            # Re-check for captcha periodically
            if idx > 0 and idx % 10 == 0:
                captcha_found = False
                for selector in captcha_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            captcha_found = True
                            break
                    except:
                        continue
                
                if captcha_found:
                    print("\n" + "="*60)
                    print("CAPTCHA DETECTED during processing!")
                    print("Please solve the captcha in the browser window.")
                    print("After solving, press ENTER to continue...")
                    print("="*60 + "\n")
                    input("Press ENTER after solving captcha...")
                    page.wait_for_timeout(3000)
                    # Re-navigate and re-query elements
                    page.goto(folder_url, wait_until='domcontentloaded', timeout=60000)
                    page.wait_for_timeout(3000)
                    all_elements = get_elements()
                    if idx >= len(all_elements):
                        break
            
            # Check if element is still valid, re-query if needed
            if idx > 0 and idx % 5 == 0:
                try:
                    test_elem = all_elements[idx]
                    test_elem.get_attribute('data-file-name')
                except:
                    # Elements became invalid, re-query
                    if verbose:
                        print(f"    Elements became invalid, re-querying...")
                    all_elements = get_elements()
                    if idx >= len(all_elements):
                        break
            
            element = all_elements[idx]
            # Initialize saved_name at the beginning (will be used if context gets destroyed)
            saved_name = None
            try:
                # Get name - handle potential navigation/context destruction
                try:
                    name = (element.get_attribute('data-file-name') or 
                           element.get_attribute('data-resource-name') or
                           element.get_attribute('data-name') or
                           element.get_attribute('title') or
                           element.get_attribute('aria-label') or
                           element.inner_text() or
                           element.text_content())
                except Exception as context_error:
                    error_str = str(context_error)
                    if 'Execution context was destroyed' in error_str or 'Target closed' in error_str:
                        if verbose:
                            print(f"    Warning: Element context destroyed at index {idx}, re-querying elements...")
                        all_elements = get_elements()
                        if idx >= len(all_elements):
                            break
                        element = all_elements[idx]
                        # Retry getting name
                        try:
                            name = (element.get_attribute('data-file-name') or 
                                   element.get_attribute('data-resource-name') or
                                   element.get_attribute('data-name') or
                                   element.get_attribute('title') or
                                   element.get_attribute('aria-label') or
                                   element.inner_text() or
                                   element.text_content())
                        except:
                            # Still failed, skip this element
                            if verbose:
                                print(f"    Warning: Could not get name after re-query, skipping...")
                            continue
                    else:
                        raise
                
                if not name:
                    continue
                
                name = name.strip()
                
                # Skip ignored folders
                if name in ['Аудио', 'Доки']:
                    continue
                
                # Check if it's a video file
                name_normalized = name.replace('\n', '').replace('\r', '').strip().lower()
                is_video = any(name_normalized.endswith(ext) for ext in VIDEO_EXTENSIONS)
                
                if not is_video:
                    continue  # Skip non-video files
                
                # Skip if we already processed this file
                if name in processed_files:
                    if verbose:
                        print(f"    Skipping {name}: already processed")
                    continue
                
                # Mark as being processed
                processed_files.add(name)
                
                # Try to get href - multiple strategies
                href = None
                
                # Strategy 1: Direct href attribute
                try:
                    href = element.get_attribute('href')
                    if href and verbose:
                        print(f"    Found href (direct): {href[:100]}...")
                except Exception as e:
                    if 'Execution context was destroyed' in str(e) or 'Target closed' in str(e):
                        if verbose:
                            print(f"    Warning: Context destroyed while getting href, re-querying...")
                        all_elements = get_elements()
                        if idx >= len(all_elements):
                            break
                        element = all_elements[idx]
                        try:
                            href = element.get_attribute('href')
                        except:
                            href = None
                    else:
                        href = None
                
                # Strategy 2: Parent link element (search up the tree)
                if not href:
                    try:
                        # Try closest parent that is a link
                        parent = element.evaluate_handle('el => el.closest("a[href]")')
                        if parent:
                            parent_element = parent.as_element()
                            if parent_element:
                                href = parent_element.get_attribute('href')
                                if href and verbose:
                                    print(f"    Found href (closest parent): {href[:100]}...")
                    except Exception as e:
                        if 'Execution context was destroyed' not in str(e) and 'Target closed' not in str(e):
                            pass  # Ignore other errors
                
                # Strategy 3: Find parent link element using query_selector
                if not href:
                    try:
                        # Try to find parent link
                        current = element
                        for _ in range(5):  # Check up to 5 levels up
                            try:
                                parent_elem = current.evaluate_handle('el => el.parentElement')
                                if not parent_elem:
                                    break
                                parent = parent_elem.as_element()
                                if parent:
                                    tag_name = parent.evaluate('el => el.tagName')
                                    if tag_name and tag_name.lower() == 'a':
                                        href = parent.get_attribute('href')
                                        if href:
                                            if verbose:
                                                print(f"    Found href (parent element): {href[:100]}...")
                                            break
                                    current = parent
                                else:
                                    break
                            except:
                                break
                    except:
                        pass
                
                # Strategy 4: Find child link element
                if not href:
                    try:
                        child_link = element.query_selector('a[href]')
                        if child_link:
                            href = child_link.get_attribute('href')
                            if href and verbose:
                                print(f"    Found href (child): {href[:100]}...")
                    except:
                        pass
                
                # Strategy 5: Check data attributes for URL
                if not href:
                    try:
                        data_href = element.get_attribute('data-href') or element.get_attribute('data-url') or element.get_attribute('data-link')
                        if data_href:
                            href = data_href
                            if verbose:
                                print(f"    Found href (data attribute): {href[:100]}...")
                    except:
                        pass
                
                # Strategy 6: Try to find link by searching for elements with the same name
                if not href:
                    try:
                        # Find all links and match by text content
                        all_links = page.query_selector_all('a[href]')
                        for link in all_links:
                            link_text = link.inner_text() or link.text_content() or link.get_attribute('title') or link.get_attribute('aria-label')
                            if link_text and link_text.strip() == name:
                                href = link.get_attribute('href')
                                if href:
                                    if verbose:
                                        print(f"    Found href (matched link): {href[:100]}...")
                                    break
                    except:
                        pass
                
                # Strategy 7: For video files, try clicking to get streaming URL
                if not href:
                    # Save name before navigation (in case context gets destroyed)
                    if not saved_name:
                        saved_name = name
                    try:
                        video_urls = []
                        response_urls = []
                        page_url_before = page.url
                        url_found_via_navigation = False
                        
                        def handle_request(request):
                            url = request.url
                            if 'captcha' in url.lower() or 'smartcaptcha' in url.lower():
                                return
                            if 'streaming.disk.yandex.net' in url or 'streaming.disk.yandex.ru' in url:
                                if '/hls/' in url or url.endswith('.m3u8') or '.mp4' in url or '.m3u8' in url:
                                    if url not in video_urls:
                                        video_urls.append(url)
                                        if verbose:
                                            print(f"    Captured streaming URL (request): {url[:100]}...")
                            # Also check for direct download URLs
                            if '/d/' in url and any(url.endswith(ext) for ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm']):
                                if url not in response_urls:
                                    response_urls.append(url)
                                    if verbose:
                                        print(f"    Captured download URL (request): {url[:100]}...")
                        
                        def handle_response(response):
                            url = response.url
                            if 'captcha' in url.lower() or 'smartcaptcha' in url.lower():
                                return
                            if 'streaming.disk.yandex.net' in url or 'streaming.disk.yandex.ru' in url:
                                if '/hls/' in url or url.endswith('.m3u8') or '.mp4' in url or '.m3u8' in url:
                                    if url not in response_urls:
                                        response_urls.append(url)
                                        if verbose:
                                            print(f"    Captured streaming URL (response): {url[:100]}...")
                            # Also check for direct download URLs
                            if '/d/' in url and any(url.endswith(ext) for ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm']):
                                if url not in response_urls:
                                    response_urls.append(url)
                                    if verbose:
                                        print(f"    Captured download URL (response): {url[:100]}...")
                        
                        # Register handlers BEFORE clicking
                        page.on('request', handle_request)
                        page.on('response', handle_response)
                        
                        # Try to click the element
                        try:
                            element.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)
                            
                            if verbose:
                                print(f"    Clicking on {name} to get video URL...")
                            
                            element.click(timeout=10000)
                            
                            # Wait longer for video to load and URLs to be captured
                            page.wait_for_timeout(5000)  # Increased from 3000 to 5000
                            
                            # Check if page URL changed (might be direct link)
                            page_url_after = page.url
                            
                            # PRIORITY: Use captured streaming URLs first (they are the actual download URLs)
                            # Only use page URL if no streaming URLs were captured
                            if not href:
                                if video_urls:
                                    href = video_urls[0]
                                    if verbose:
                                        print(f"    ✓ Using captured streaming URL (request): {href[:100]}...")
                                elif response_urls:
                                    href = response_urls[0]
                                    if verbose:
                                        print(f"    ✓ Using captured streaming URL (response): {href[:100]}...")
                            
                            # If no streaming URL captured but page URL changed, use page URL as fallback
                            if not href and page_url_after != page_url_before and '/d/' in page_url_after:
                                if verbose:
                                    print(f"    Page URL changed to: {page_url_after[:100]}...")
                                    print(f"    Note: Using page URL as fallback (no streaming URL captured)")
                                href = page_url_after
                                url_found_via_navigation = True
                                # Navigate back and wait for page to fully reload
                                try:
                                    page.goto(page_url_before, wait_until='domcontentloaded', timeout=30000)
                                    page.wait_for_timeout(2000)
                                    # Re-query elements after navigation to ensure they're valid
                                    all_elements = get_elements()
                                except Exception as nav_error:
                                    if verbose:
                                        print(f"    Warning: Could not navigate back: {nav_error}")
                                    # URL already found, continue with it
                                    pass
                            
                            # Check for video element in DOM (only if URL not found yet)
                            if not href:
                                try:
                                    video_elements = page.query_selector_all('video[src], video source[src]')
                                    for video_elem in video_elements:
                                        video_src = video_elem.get_attribute('src')
                                        if video_src:
                                            if 'streaming.disk.yandex' in video_src or '/d/' in video_src:
                                                href = video_src
                                                if verbose:
                                                    print(f"    Found video src: {video_src[:100]}...")
                                                break
                                except:
                                    pass
                            
                            # Check for iframe with video (only if URL not found yet)
                            if not href:
                                try:
                                    iframes = page.query_selector_all('iframe[src]')
                                    for iframe in iframes:
                                        iframe_src = iframe.get_attribute('src')
                                        if iframe_src and ('streaming.disk.yandex' in iframe_src or '/d/' in iframe_src):
                                            href = iframe_src
                                            if verbose:
                                                print(f"    Found iframe src: {iframe_src[:100]}...")
                                            break
                                except:
                                    pass
                            
                            # If we found a URL, close overlay and ensure we're on the right page
                            if href:
                                # Save href and name before navigation (in case context gets destroyed)
                                saved_href = href
                                saved_name_for_item = saved_name
                                
                                if verbose:
                                    print(f"    ✓ URL found for {saved_name_for_item}, preparing to add to list...")
                                try:
                                    page.keyboard.press('Escape')
                                    page.wait_for_timeout(500)
                                except:
                                    pass
                                
                                # If page URL changed but we found URL via request/response, navigate back
                                if not url_found_via_navigation and page_url_after != page_url_before:
                                    if verbose:
                                        print(f"    Navigating back to folder page...")
                                    try:
                                        page.goto(page_url_before, wait_until='domcontentloaded', timeout=30000)
                                        page.wait_for_timeout(2000)
                                        all_elements = get_elements()
                                    except Exception as nav_err:
                                        if verbose:
                                            print(f"    Warning during navigation back: {nav_err}")
                                        pass
                                # If page URL didn't change, make sure we're still on the folder page
                                elif page_url_after == page_url_before:
                                    try:
                                        current_url = page.url
                                        if current_url != page_url_before:
                                            page.goto(page_url_before, wait_until='domcontentloaded', timeout=30000)
                                            page.wait_for_timeout(2000)
                                            all_elements = get_elements()
                                    except:
                                        pass
                                
                                # Restore href and name after navigation (they might have been lost)
                                href = saved_href
                                name = saved_name_for_item
                                
                                # Break out of Strategy 7 try block since we found the URL
                                # The href will be used below to add the item
                                if verbose:
                                    print(f"    Breaking out of Strategy 7, href = {href[:100] if href else 'None'}...")
                                    print(f"    Name preserved: {name}")
                                break
                            elif verbose:
                                print(f"    No video URL captured after click (video_urls: {len(video_urls)}, response_urls: {len(response_urls)})")
                        except Exception as click_error:
                            # Even if click failed, check if we captured URLs before the error
                            if not href:
                                if video_urls:
                                    href = video_urls[0]
                                    if verbose:
                                        print(f"    Using captured request URL (after error): {href[:100]}...")
                                elif response_urls:
                                    href = response_urls[0]
                                    if verbose:
                                        print(f"    Using captured response URL (after error): {href[:100]}...")
                            if verbose:
                                print(f"    Warning: Could not click element for {name}: {click_error}")
                    except Exception as e:
                        if verbose:
                            print(f"    Warning: Could not get link for {name}: {e}")
                
                # After Strategy 7: check if we have href and name
                if verbose:
                    print(f"    After Strategy 7: href = {href[:100] if href else 'None'}, name = {name if 'name' in locals() else 'NOT DEFINED'}")
                
                if not href:
                    if verbose:
                        print(f"    ERROR: No download URL found for {name if 'name' in locals() else 'UNKNOWN'}")
                        print(f"    Stopping execution: cannot proceed without download URL")
                    raise Exception(f"Cannot find download URL for {name if 'name' in locals() else 'UNKNOWN'}. Script execution stopped.")
                
                if verbose:
                    print(f"    Processing href for {name}: {href[:100] if href else 'None'}...")
                
                # Construct full URL
                if href.startswith('/'):
                    if 'disk.yandex.ru' in folder_url or 'disk.yandex.ru' in href:
                        full_url = f"https://disk.yandex.ru{href}"
                    else:
                        full_url = f"https://yadi.sk{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    if verbose:
                        print(f"    Warning: Invalid href format for {name}, skipping...")
                    continue
                
                # Build relative path
                relative_path = f"{folder_path}/{name}"
                
                # If download_immediately is True, download and upload immediately
                if download_immediately and cache_dir and tree_file_path:
                    try:
                        # Build local path
                        path_parts = [part.strip().replace('\n', ' ').replace('\r', ' ') 
                                     for part in relative_path.split('/') if part.strip()]
                        sanitized_parts = [sanitize_folder_name(part) if i < len(path_parts) - 1 
                                          else sanitize_filename(part) 
                                          for i, part in enumerate(path_parts)]
                        
                        if len(path_parts) > 1:
                            folder_parts = sanitized_parts[:-1]
                            local_folder_path = os.path.join(cache_dir, *folder_parts)
                            os.makedirs(local_folder_path, exist_ok=True)
                        
                        local_path = os.path.join(cache_dir, *sanitized_parts)
                        
                        # Check if already downloaded
                        is_fully_downloaded, is_partially_downloaded = is_file_downloaded(
                            relative_path, tree_file_path)
                        
                        if is_fully_downloaded:
                            if verbose:
                                print(f"    Skipping {relative_path} - already fully downloaded")
                            continue
                        
                        # Download video
                        if not is_partially_downloaded or not os.path.exists(local_path):
                            if verbose:
                                print(f"\n    Downloading {relative_path} immediately...")
                            if not download_video(full_url, local_path, verbose, page):
                                print(f"ERROR: Failed to download {relative_path}")
                                raise Exception(f"Download failed for {relative_path}. Script execution stopped.")
                            
                            mark_file_partially_downloaded(relative_path, tree_file_path, verbose)
                            if verbose:
                                print(f"    ✓ Downloaded: {relative_path}")
                        
                        # Upload to Yandex Disk if destination_path and oauth_token provided
                        if destination_path and oauth_token:
                            clean_relative_path = relative_path.lstrip('/')
                            if destination_path.endswith('/'):
                                full_destination = f"{destination_path}{clean_relative_path}"
                            else:
                                full_destination = f"{destination_path}/{clean_relative_path}"
                            
                            if verbose:
                                print(f"    Uploading {relative_path} to {full_destination}...")
                            
                            # Create folder structure
                            if len(path_parts) > 1:
                                folder_path_for_upload = '/'.join(path_parts[:-1])
                                folder_path_for_upload = folder_path_for_upload.lstrip('/')
                                create_folder_structure(destination_path, folder_path_for_upload, 
                                                       oauth_token, verbose)
                            
                            if not upload_to_yandex_disk(local_path, full_destination, oauth_token, 
                                                       verbose, use_web_interface=False, page=page):
                                print(f"ERROR: Failed to upload {relative_path}")
                                raise Exception(f"Upload failed for {relative_path}. Script execution stopped.")
                            
                            mark_file_downloaded(relative_path, tree_file_path, verbose)
                            if verbose:
                                print(f"    ✓ Uploaded: {relative_path}")
                            
                            # Delete local file after successful upload
                            try:
                                os.remove(local_path)
                                if verbose:
                                    print(f"    Deleted local file: {local_path}")
                            except Exception as e:
                                if verbose:
                                    print(f"    Warning: Could not delete local file: {e}")
                        else:
                            if verbose:
                                print(f"    Note: Upload skipped (no destination_path or oauth_token)")
                        
                        # Continue to next file (don't add to items list)
                        continue
                    except Exception as download_error:
                        print(f"ERROR: Failed to process {relative_path}: {download_error}")
                        raise  # Re-raise to stop execution
                
                # Original code: add to items list if not downloading immediately
                if verbose:
                    print(f"    Adding video to items list: {relative_path} -> {full_url[:100]}...")
                
                items.append({
                    'name': name,
                    'download_url': full_url,
                    'order': file_idx,
                    'relative_path': relative_path
                })
                file_idx += 1
                
                if verbose:
                    print(f"    ✓ Successfully added video to list: {relative_path}")
            except Exception as e:
                error_str = str(e)
                # If we have href but got an error, try to add the file anyway (context might be destroyed but data is saved)
                if 'href' in locals() and href:
                    if verbose:
                        print(f"    Warning: Exception occurred but href is available, attempting to add file anyway...")
                    try:
                        # Use saved name if available, otherwise try to reconstruct
                        item_name = name if 'name' in locals() and name else saved_name if 'saved_name' in locals() else f"video_{file_idx}"
                        relative_path = f"{folder_path}/{item_name}"
                        
                        # Construct full URL
                        if href.startswith('/'):
                            if 'disk.yandex.ru' in folder_url or 'disk.yandex.ru' in href:
                                full_url = f"https://disk.yandex.ru{href}"
                            else:
                                full_url = f"https://yadi.sk{href}"
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = href
                        
                        items.append({
                            'name': item_name,
                            'download_url': full_url,
                            'order': file_idx,
                            'relative_path': relative_path
                        })
                        file_idx += 1
                        if verbose:
                            print(f"    ✓ Successfully added video to list (recovered from error): {relative_path}")
                        continue  # Successfully added, move to next element
                    except Exception as recovery_error:
                        if verbose:
                            print(f"    Failed to recover: {recovery_error}")
                
                if 'Execution context was destroyed' in error_str or 'Target closed' in error_str:
                    if verbose:
                        print(f"    Warning: Execution context destroyed, re-querying elements...")
                    # Re-query elements and continue from current index
                    all_elements = get_elements()
                    if idx >= len(all_elements):
                        break
                    # Don't increment idx, retry current position
                    continue
                else:
                    if verbose:
                        print(f"    Warning: Could not process element: {e}")
                    continue
        
        if verbose:
            print(f"  Found {len(items)} video(s) in {folder_path}")
    except Exception as e:
        # If it's a critical error about missing download URL or download/upload failure, re-raise it
        error_msg = str(e)
        if ("Cannot find download URL" in error_msg or 
            "cannot proceed without download URL" in error_msg.lower() or
            "Download failed" in error_msg or
            "Upload failed" in error_msg or
            "Script execution stopped" in error_msg):
            raise
        if verbose:
            print(f"  Error parsing folder {folder_path}: {e}")
        # For other errors during parsing, also stop execution if download_immediately is True
        if download_immediately:
            print(f"ERROR: Parsing error in folder {folder_path}: {e}")
            raise Exception(f"Parsing error: {e}. Script execution stopped.")
    
    return items


def parse_public_folder(public_url: str, base_path: str = "", verbose: bool = False, browser=None, context=None, page=None, playwright_instance=None, test_mode: bool = False, processed_folder_urls: set = None,
                        cache_dir: str = None, tree_file_path: str = None,
                        destination_path: str = None, oauth_token: str = None,
                        download_immediately: bool = False) -> Tuple[List[Dict], List[Dict], Optional[Any], Optional[Any], Optional[Any], Optional[Any]]:
    """
    NEW LOGIC: 
    1. First, collect all folders from current level (without entering them)
    2. Create folder tree
    3. Then, enter each folder one by one and collect files (or download immediately if download_immediately=True)
    
    Args:
        public_url: Public folder URL
        base_path: Base path for relative paths
        verbose: Enable verbose output
        browser: Playwright browser instance (optional)
        context: Playwright browser context (optional)
        page: Playwright page instance (optional)
        playwright_instance: Playwright instance (optional)
        test_mode: If True, process only first video
        processed_folder_urls: Set of already processed folder URLs
        cache_dir: Local cache directory for downloads (required if download_immediately=True)
        tree_file_path: Path to tree.md file (required if download_immediately=True)
        destination_path: Yandex Disk destination path (optional, for upload)
        oauth_token: Yandex Disk OAuth token (optional, for upload)
        download_immediately: If True, download and upload videos immediately instead of collecting in list
    
    Returns:
        Tuple of (items, folder_info, browser, context, page, playwright_instance)
    """
    if processed_folder_urls is None:
        processed_folder_urls = set()
    
    is_root_call = browser is None
    
    # Initialize browser if root call
    if is_root_call:
        if verbose:
            print(f"Parsing public folder: {public_url}")
        print("\n" + "="*60)
        print("Browser will stay open throughout script execution.")
        print("If captcha appears, solve it once - script will continue")
        print("in the same browser session to minimize bot detection.")
        print("="*60 + "\n")
        playwright_instance = sync_playwright().start()
        
        try:
            import shutil
            chrome_paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium',
                shutil.which('google-chrome'),
                shutil.which('chromium'),
                shutil.which('chromium-browser'),
            ]
            chrome_executable = None
            for path in chrome_paths:
                if path and os.path.exists(path):
                    chrome_executable = path
                    if verbose:
                        print(f"Using system browser: {path}")
                    break
            
            browser = playwright_instance.chromium.launch(
                headless=False,
                executable_path=chrome_executable,
                args=[
                    '--enable-features=VaapiVideoDecoder',
                    '--use-gl=egl',
                    '--enable-hardware-acceleration',
                ]
            )
        except Exception as e:
            if verbose:
                print(f"Could not use system Chrome, using Playwright Chromium: {e}")
            browser = playwright_instance.chromium.launch(headless=False)
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
        )
        page = context.new_page()
    
    items = []
    all_folders = []  # All folders found at all levels
    
    try:
        # Navigate to URL
        if is_root_call:
            if verbose:
                print(f"Navigating to: {public_url}")
            page.goto(public_url, wait_until='domcontentloaded', timeout=60000)
        else:
            if verbose:
                print(f"Navigating to subfolder: {public_url}")
            page.goto(public_url, wait_until='domcontentloaded', timeout=60000)
        
        page.wait_for_timeout(3000)
        
        # Check for captcha
        captcha_solved = False
        while not captcha_solved:
            captcha_selectors = [
                'text=/[Рр]обот|[Cc]aptcha|[Пп]одтвердите/',
                '[class*="captcha"]',
                '[class*="Captcha"]',
                '[id*="captcha"]',
                '[id*="Captcha"]',
                'iframe[src*="captcha"]',
                'iframe[src*="smartcaptcha"]'
            ]
            
            captcha_found = False
            for selector in captcha_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        captcha_found = True
                        break
                except:
                    continue
            
            if captcha_found:
                if is_root_call:
                    print("\n" + "="*60)
                    print("CAPTCHA DETECTED!")
                    print("Please solve the captcha in the browser window.")
                    print("After solving, press ENTER to continue...")
                    print("="*60 + "\n")
                    input("Press ENTER after solving captcha...")
                page.wait_for_timeout(2000)
                
                captcha_still_present = False
                for selector in captcha_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            captcha_still_present = True
                            break
                    except:
                        continue
                
                if not captcha_still_present:
                    captcha_solved = True
                    if is_root_call:
                        print("Captcha solved! Continuing...\n")
                    # Don't reload - just wait a bit for page to update
                    page.wait_for_timeout(3000)
                else:
                    if is_root_call:
                        print("Captcha still present. Please solve it and press ENTER again...")
            else:
                captcha_solved = True
        
        # Wait for content
        if verbose:
            print("  Waiting for page content to load...")
        
        for attempt in range(10):
            page.wait_for_timeout(2000)
            test_elements = page.query_selector_all('a[href*="/d/"], [data-file-name], .listing-item, .resource-item')
            if len(test_elements) > 0:
                if verbose:
                    print(f"  Content loaded (found {len(test_elements)} elements)")
                break
        
        # STEP 1: Collect all folders from current level (without entering them)
        if verbose:
            print(f"  Step 1: Collecting folders from current level...")
        current_level_folders = collect_all_folders(page, public_url, base_path, verbose, processed_folder_urls)
        all_folders.extend(current_level_folders)
        if verbose:
            print(f"  Found {len(current_level_folders)} folder(s) at current level")
        
        # STEP 2: Recursively collect folders from subfolders
        if not test_mode:
            for folder in current_level_folders:
                try:
                    # Recursively collect folders from subfolder (returns folders list, not items)
                    subfolder_folders, _, _, _, _, _ = parse_public_folder(
                        folder['url'],
                        folder['path'],
                        verbose,
                        browser,
                        context,
                        page,
                        playwright_instance,
                        test_mode,
                        processed_folder_urls,
                        cache_dir=cache_dir,
                        tree_file_path=tree_file_path,
                        destination_path=destination_path,
                        oauth_token=oauth_token,
                        download_immediately=download_immediately
                    )
                    all_folders.extend(subfolder_folders)
                except Exception as e:
                    if verbose:
                        print(f"  Warning: Could not collect folders from {folder['path']}: {e}")
                    continue
        
        # For non-root calls, just return collected folders
        if not is_root_call:
            return all_folders, [], None, None, None, None
        
        # STEP 3: Now enter each folder one by one and collect files (only for root call)
        if verbose:
            print(f"  Step 3: Entering folders to collect files...")
            print(f"  Total folders to process: {len(all_folders)}")
        
        # Process all collected folders
        for folder in all_folders:
            # Enter folder and collect files (or download immediately)
            folder_items = parse_folder_contents(page, folder['url'], folder['path'], verbose,
                                                 cache_dir=cache_dir, tree_file_path=tree_file_path,
                                                 destination_path=destination_path, oauth_token=oauth_token,
                                                 download_immediately=download_immediately)
            items.extend(folder_items)
            if verbose:
                print(f"  Collected {len(folder_items)} video(s) from {folder['path']}")
        
        # Also collect files from root level (if any)
        if verbose:
            print(f"  Checking root level for files...")
        root_items = parse_folder_contents(page, public_url, "", verbose,
                                          cache_dir=cache_dir, tree_file_path=tree_file_path,
                                          destination_path=destination_path, oauth_token=oauth_token,
                                          download_immediately=download_immediately)
        items.extend(root_items)
        if verbose:
            print(f"  Collected {len(root_items)} video(s) from root level")
        
        # Convert all_folders to folder_info format
        folder_info = [{'name': f['name'], 'path': f['path']} for f in all_folders]
        
        return items, folder_info, browser, context, page, playwright_instance
        
    except Exception as e:
        if is_root_call:
            raise ValueError(f"Error parsing public folder: {e}")
        else:
            return [], [], None, None, None, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for filesystem compatibility while preserving Unicode.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove or replace invalid filesystem characters
    # But preserve Unicode characters (Cyrillic, etc.)
    invalid_chars = '<>:"|?*\\'
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing dots and spaces (Windows issue)
    sanitized = sanitized.strip('. ')
    
    # Replace multiple underscores with single one
    sanitized = re.sub(r'_+', '_', sanitized)
    
    return sanitized.strip('_')


def sanitize_folder_name(folder_name: str) -> str:
    """
    Sanitize folder name for filesystem compatibility while preserving Unicode.
    
    Args:
        folder_name: Original folder name
    
    Returns:
        Sanitized folder name safe for filesystem
    """
    import re
    # Same as filename sanitization
    invalid_chars = '<>:"|?*\\'
    sanitized = folder_name
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    sanitized = sanitized.strip('. ')
    sanitized = re.sub(r'_+', '_', sanitized)
    
    return sanitized.strip('_')


def create_folder_structure(destination_path: str, folder_path: str, oauth_token: str, verbose: bool = False) -> None:
    """
    Create folder structure on Yandex Disk.
    
    Args:
        destination_path: Base destination path on Yandex Disk
        folder_path: Relative folder path to create
        oauth_token: OAuth token for Yandex Disk API
        verbose: Enable verbose output
    """
    if not folder_path:
        return
    
    # Split folder path into parts
    path_parts = folder_path.split('/')
    current_path = destination_path
    
    for part in path_parts:
        if not part:
            continue
        
        # Sanitize folder name
        sanitized_part = sanitize_folder_name(part)
        if not sanitized_part:
            continue
        
        # Build full path
        if current_path.endswith('/'):
            full_path = f"{current_path}{sanitized_part}"
        else:
            full_path = f"{current_path}/{sanitized_part}"
        
        # Create folder via API
        try:
            api_url = "https://cloud-api.yandex.net/v1/disk/resources"
            headers = {'Authorization': f'OAuth {oauth_token}'}
            params = {'path': full_path}
            
            response = requests.put(f"{api_url}?path={full_path}", headers=headers, timeout=30)
            
            # 201 = created, 409 = already exists (both are OK)
            if response.status_code not in [201, 409]:
                if verbose:
                    print(f"  Warning: Could not create folder {full_path}: {response.status_code}")
            elif verbose:
                print(f"  Created folder: {full_path}")
        except Exception as e:
            if verbose:
                print(f"  Warning: Error creating folder {full_path}: {e}")
        
        current_path = full_path


def download_video(download_url: str, local_path: str, verbose: bool = False, page=None) -> bool:
    """
    Download video file from URL to local path.
    
    Args:
        download_url: URL to download video from
        local_path: Local file path to save video to
        verbose: Enable verbose output
    
    Returns:
        True if download successful, False otherwise
    """
    try:
        # Check if file already exists locally
        if os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            # If file exists and is larger than 1MB, assume it's already downloaded
            if file_size > 1024 * 1024:
                if verbose:
                    print(f"  File already exists locally ({file_size} bytes), skipping download")
                return True
        
        # Create directory if needed
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Check if URL is a Yandex Disk page (needs yt-dlp) or direct download
        is_direct_download = any(download_url.lower().endswith(ext) for ext in VIDEO_EXTENSIONS + ['.m3u8', '.mpd'])
        is_yandex_page = ('disk.yandex.ru/d/' in download_url or 'yadi.sk/d/' in download_url) and not is_direct_download
        
        # If we have a Playwright page and it's a direct download, use cookies from browser
        if page and is_direct_download:
            try:
                if verbose:
                    print(f"  Using browser cookies for download...")
                
                cookies = page.context.cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                
                with requests.get(download_url, stream=True, timeout=300, 
                                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                                cookies=cookie_dict) as r:
                    r.raise_for_status()
                    content_type = r.headers.get('content-type', '').lower()
                    total_size = int(r.headers.get('content-length', 0))
                    
                    if 'text/html' in content_type:
                        raise Exception(f"URL returned HTML instead of video (likely captcha page)")
                    
                    with open(local_path, 'wb') as f:
                        downloaded = 0
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if verbose and total_size > 0:
                                    percent = (downloaded / total_size) * 100
                                    print(f'\r  Downloading: {percent:.1f}% ({downloaded}/{total_size} bytes)', end='', flush=True)
                        if verbose:
                            print()  # New line
                    
                    if verbose:
                        print(f"  Download completed: {downloaded} bytes")
                    return True
            except Exception as e:
                if verbose:
                    print(f"  Warning: Browser cookie download failed: {e}, trying yt-dlp...")
        
        # Use yt-dlp for Yandex Disk pages or streaming URLs
        if is_yandex_page or '.m3u8' in download_url or '.mpd' in download_url:
            if verbose:
                print(f"  Downloading streaming video with yt-dlp...")
            
            ydl_opts = {
                'outtmpl': local_path,
                'quiet': not verbose,
                'no_warnings': not verbose,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([download_url])
            
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                if verbose:
                    print(f"  Download completed")
                return True
            else:
                raise Exception("Downloaded file is empty or doesn't exist")
        else:
            # Direct download with requests
            if verbose:
                print(f"  Downloading directly...")
            
            with requests.get(download_url, stream=True, timeout=300) as r:
                r.raise_for_status()
                content_type = r.headers.get('content-type', '').lower()
                
                if 'text/html' in content_type:
                    raise Exception(f"URL returned HTML instead of video")
                
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            if verbose:
                print(f"  Download completed")
            return True
            
    except Exception as e:
        if verbose:
            print(f"  Download error: {e}")
        return False


def get_upload_url(destination_path: str, oauth_token: str, verbose: bool = False) -> str:
    """
    Get upload URL from Yandex Disk API.
    
    Args:
        destination_path: Full destination path on Yandex Disk
        oauth_token: OAuth token for Yandex Disk API
        verbose: Enable verbose output
    
    Returns:
        Upload URL string
    
    Raises:
        requests.RequestException: On API error
    """
    api_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    headers = {'Authorization': f'OAuth {oauth_token}'}
    params = {'path': destination_path, 'overwrite': 'true'}
    
    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        upload_data = response.json()
        upload_url = upload_data.get('href')
        if not upload_url:
            raise requests.RequestException("Upload URL not found in API response")
        return upload_url
    except requests.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                raise requests.RequestException("Authentication error: OAuth token invalid or expired")
        raise requests.RequestException(f"Failed to get upload URL: {e}")


def get_folder_url_from_path(destination_path: str, oauth_token: str, verbose: bool = False) -> Optional[str]:
    """
    Get web interface URL for a folder on Yandex Disk from its path.
    
    Args:
        destination_path: Full path to folder on Yandex Disk (e.g., "/Videos/Downloaded")
        oauth_token: OAuth token for Yandex Disk API
        verbose: Enable verbose output
    
    Returns:
        Web interface URL for the folder, or None if not found
    """
    try:
        # Parse destination path to get folder path (remove filename if present)
        path_parts = [p for p in destination_path.split('/') if p]
        
        # Remove filename if it's in the path (check if last part looks like a file)
        if path_parts and any(path_parts[-1].endswith(ext) for ext in VIDEO_EXTENSIONS + ['.txt', '.zip', '.rar']):
            path_parts = path_parts[:-1]
        
        if not path_parts:
            # Root folder
            return "https://disk.yandex.ru"
        
        # Build folder path
        folder_path = '/' + '/'.join(path_parts)
        
        # Try to get folder info from API to construct proper URL
        api_url = "https://cloud-api.yandex.net/v1/disk/resources"
        headers = {'Authorization': f'OAuth {oauth_token}'}
        params = {'path': folder_path}
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                # Folder exists, construct URL
                # Format: https://disk.yandex.ru/client/disk/Папка1/Папка2
                # URL-encode folder names
                encoded_parts = [quote(part, safe='') for part in path_parts]
                folder_url = "https://disk.yandex.ru/client/disk/" + "/".join(encoded_parts)
                if verbose:
                    print(f"  Constructed folder URL: {folder_url}")
                return folder_url
        except:
            pass
        
        # Fallback: construct URL directly from path parts
        encoded_parts = [quote(part, safe='') for part in path_parts]
        folder_url = "https://disk.yandex.ru/client/disk/" + "/".join(encoded_parts)
        if verbose:
            print(f"  Using constructed folder URL: {folder_url}")
        return folder_url
        
    except Exception as e:
        if verbose:
            print(f"  Warning: Could not get folder URL: {e}")
        return None


def upload_to_yandex_disk_web_interface(local_path: str, destination_path: str, page, oauth_token: str = None, verbose: bool = False) -> bool:
    """
    Upload file to Yandex Disk through web interface using Playwright (faster than API).
    
    Args:
        local_path: Local file path to upload
        destination_path: Destination path on Yandex Disk (e.g., "/Videos/Downloaded/file.mp4")
        page: Playwright page object (must be logged in to Yandex Disk)
        oauth_token: OAuth token for Yandex Disk API (optional, used to get folder URL)
        verbose: Enable verbose output
    
    Returns:
        True if upload successful, False otherwise
    """
    try:
        file_size = os.path.getsize(local_path)
        file_name = os.path.basename(local_path)
        
        # Get folder URL from destination path
        folder_url = None
        if destination_path and destination_path != '/':
            if oauth_token:
                folder_url = get_folder_url_from_path(destination_path, oauth_token, verbose)
            else:
                # Fallback: construct URL directly from path
                path_parts = [p for p in destination_path.split('/') if p]
                # Remove filename if present
                if path_parts and any(path_parts[-1].endswith(ext) for ext in VIDEO_EXTENSIONS + ['.txt', '.zip', '.rar']):
                    path_parts = path_parts[:-1]
                if path_parts:
                    encoded_parts = [quote(part, safe='') for part in path_parts]
                    folder_url = "https://disk.yandex.ru/client/disk/" + "/".join(encoded_parts)
        
        # Navigate to Yandex Disk or specific folder
        if folder_url:
            if verbose:
                print(f"  Opening folder: {folder_url}")
            page.goto(folder_url, wait_until='domcontentloaded', timeout=30000)
        else:
            if verbose:
                print(f"  Opening Yandex Disk root...")
            page.goto("https://disk.yandex.ru", wait_until='domcontentloaded', timeout=30000)
        
        page.wait_for_timeout(3000)  # Wait for page to load
        
        # Verify we're in the right folder by checking breadcrumbs or folder name
        if folder_url and verbose:
            try:
                # Try to find folder name in page to verify navigation
                current_url = page.url
                if verbose:
                    print(f"  Current page URL: {current_url}")
            except:
                pass
        
        # Find upload button/input
        if verbose:
            print(f"  Looking for upload input...")
        
        # Wait for page to be ready
        page.wait_for_timeout(1000)
        
        # Try to find file input (usually hidden)
        # Yandex Disk uses a file input for uploads
        file_input_selector = 'input[type="file"]'
        
        # Check if input exists, if not, try to trigger upload button
        try:
            file_input = page.locator(file_input_selector).first
            if not file_input.is_visible():
                # Try to click upload button to reveal input
                upload_buttons = [
                    'button:has-text("Загрузить")',
                    'button:has-text("Upload")',
                    '[data-testid="upload-button"]',
                    '.upload-button',
                    'button[aria-label*="upload" i]',
                    'button[aria-label*="загрузить" i]'
                ]
                for button_selector in upload_buttons:
                    try:
                        button = page.locator(button_selector).first
                        if button.is_visible(timeout=1000):
                            if verbose:
                                print(f"  Clicking upload button...")
                            button.click()
                            page.wait_for_timeout(500)
                            break
                    except:
                        continue
        except:
            pass
        
        # Set file to upload
        if verbose:
            print(f"  Selecting file: {file_name}")
        
        file_input = page.locator(file_input_selector).first
        file_input.set_input_files(local_path)
        
        # Wait for upload to complete
        if verbose:
            print(f"  Waiting for upload to complete...")
        
        # Monitor upload progress
        # Look for progress indicators or completion messages
        max_wait_time = 3600  # 1 hour max
        start_time = page.evaluate("() => Date.now()")
        
        while True:
            page.wait_for_timeout(2000)
            
            # Check for completion indicators
            completion_indicators = [
                'text=/загрузка завершена/i',
                'text=/upload complete/i',
                'text=/файл загружен/i',
                '.upload-complete',
                '[data-testid="upload-complete"]'
            ]
            
            for indicator in completion_indicators:
                try:
                    element = page.locator(indicator).first
                    if element.is_visible(timeout=100):
                        if verbose:
                            print(f"  Upload completed!")
                        return True
                except:
                    continue
            
            # Check for errors
            error_indicators = [
                'text=/ошибка/i',
                'text=/error/i',
                '.upload-error',
                '[data-testid="upload-error"]'
            ]
            
            for indicator in error_indicators:
                try:
                    element = page.locator(indicator).first
                    if element.is_visible(timeout=100):
                        error_text = element.text_content()
                        if verbose:
                            print(f"  Upload error: {error_text}")
                        return False
                except:
                    continue
            
            # Check timeout
            current_time = page.evaluate("() => Date.now()")
            if (current_time - start_time) > max_wait_time * 1000:
                if verbose:
                    print(f"  Upload timeout after {max_wait_time} seconds")
                return False
            
            # Show progress (if available)
            try:
                progress_text = page.locator('.upload-progress, [data-testid="upload-progress"]').first.text_content()
                if progress_text and verbose:
                    print(f'\r\033[K  {progress_text}', end='', flush=True)
            except:
                pass
        
    except Exception as e:
        if verbose:
            print(f"  Web interface upload failed: {e}")
        return False


def upload_to_yandex_disk_api_only(local_path: str, destination_path: str, oauth_token: str, verbose: bool = False) -> bool:
    """
    Upload file to Yandex Disk via API only (standard method, no optimizations).
    Used internally by other upload functions.
    
    Args:
        local_path: Local file path to upload
        destination_path: Destination path on Yandex Disk
        oauth_token: OAuth token for Yandex Disk API
        verbose: Enable verbose output
    
    Returns:
        True if upload successful, False otherwise
    """
    try:
        # Get upload URL
        upload_url = get_upload_url(destination_path, oauth_token, verbose)
        
        # Get file size for progress tracking
        file_size = os.path.getsize(local_path)
        
        # Custom file-like object with progress callback
        class ProgressFile:
            def __init__(self, file_obj, total_size, callback=None):
                self.file_obj = file_obj
                self.total_size = total_size
                self.uploaded = 0
                self.callback = callback
            
            def read(self, size=-1):
                chunk = self.file_obj.read(size)
                if chunk:
                    self.uploaded += len(chunk)
                    if self.callback:
                        self.callback(self.uploaded, self.total_size)
                return chunk
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass
        
        # Progress callback function
        def show_progress(uploaded, total):
            percent = (uploaded / total) * 100 if total > 0 else 0
            bar_length = 40
            filled = int(bar_length * uploaded / total) if total > 0 else 0
            bar = '=' * filled + '-' * (bar_length - filled)
            def format_bytes(bytes_val):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if bytes_val < 1024.0:
                        return f"{bytes_val:.1f} {unit}"
                    bytes_val /= 1024.0
                return f"{bytes_val:.1f} TB"
            
            uploaded_str = format_bytes(uploaded)
            total_str = format_bytes(total)
            # Use ANSI escape code to clear line and move cursor to beginning
            # \033[K clears from cursor to end of line, \r moves to beginning
            message = f'  Uploading: [{bar}] {percent:.1f}% ({uploaded_str}/{total_str})'
            print(f'\r\033[K{message}', end='', flush=True)
        
        # Upload with progress tracking
        headers = {'Content-Type': 'application/octet-stream'}
        with open(local_path, 'rb') as f:
            progress_file = ProgressFile(f, file_size, show_progress)
            response = requests.put(upload_url, data=progress_file, headers=headers, timeout=600)
            response.raise_for_status()
        
        print()  # New line after progress bar
        if verbose:
            print(f"  Upload completed: {file_size} bytes")
        
        return True
            
    except requests.RequestException as e:
        if '401' in str(e) or 'Authentication' in str(e):
            raise requests.RequestException(f"Authentication error: OAuth token invalid or expired")
        raise requests.RequestException(f"Upload failed: {e}")
    except IOError as e:
        raise IOError(f"File read error: {e}")


def upload_to_yandex_disk_with_extension_workaround(local_path: str, destination_path: str, oauth_token: str, verbose: bool = False) -> bool:
    """
    Upload file to Yandex Disk with extension workaround to bypass 128 KB/s limit.
    Temporarily changes file extension to .txt, uploads, then renames back.
    
    Args:
        local_path: Local file path to upload
        destination_path: Destination path on Yandex Disk
        oauth_token: OAuth token for Yandex Disk API
        verbose: Enable verbose output
    
    Returns:
        True if upload successful, False otherwise
    """
    import tempfile
    import shutil
    
    try:
        # Get original file extension
        original_ext = os.path.splitext(local_path)[1]
        original_name = os.path.basename(local_path)
        
        # Create temporary file with .txt extension
        temp_dir = tempfile.gettempdir()
        temp_name = os.path.splitext(original_name)[0] + '.txt'
        temp_path = os.path.join(temp_dir, temp_name)
        
        if verbose:
            print(f"  Creating temporary file with .txt extension to bypass speed limit...")
        
        # Copy file to temp location with .txt extension
        shutil.copy2(local_path, temp_path)
        
        # Change destination path extension to .txt
        destination_path_txt = os.path.splitext(destination_path)[0] + '.txt'
        
        try:
            # Upload with .txt extension using API directly (no recursion)
            if verbose:
                print(f"  Uploading as .txt file (bypassing speed limit)...")
            success = upload_to_yandex_disk_api_only(temp_path, destination_path_txt, oauth_token, verbose)
            
            if not success:
                return False
            
            # Rename file back to original extension via API
            if verbose:
                print(f"  Renaming file back to original extension...")
            
            api_url = "https://cloud-api.yandex.net/v1/disk/resources/move"
            headers = {'Authorization': f'OAuth {oauth_token}'}
            params = {
                'from': destination_path_txt,
                'path': destination_path,
                'overwrite': 'true'
            }
            
            response = requests.post(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            if verbose:
                print(f"  File renamed successfully")
            
            return True
            
        finally:
            # Clean up temp file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
                
    except Exception as e:
        if verbose:
            print(f"  Extension workaround upload failed: {e}")
        return False


def upload_to_yandex_disk(local_path: str, destination_path: str, oauth_token: str, verbose: bool = False, use_web_interface: bool = False, page = None) -> bool:
    """
    Upload file to Yandex Disk with progress bar.
    Supports multiple upload methods for optimal speed.
    
    Args:
        local_path: Local file path to upload
        destination_path: Destination path on Yandex Disk (preserves folder structure on Yandex Disk)
        oauth_token: OAuth token for Yandex Disk API
        verbose: Enable verbose output
        use_web_interface: If True, use web interface upload (faster, requires Playwright page)
        page: Playwright page object (required if use_web_interface=True)
    
    Returns:
        True if upload successful, False otherwise
    
    Raises:
        requests.RequestException: On API or network error
        IOError: On file read error
    """
    # Try web interface first if requested
    if use_web_interface and page:
        if verbose:
            print(f"  Using web interface upload (faster method)...")
        try:
            result = upload_to_yandex_disk_web_interface(local_path, destination_path, page, oauth_token, verbose)
            if result:
                return True
            if verbose:
                print(f"  Web interface upload failed, falling back to API...")
        except Exception as e:
            if verbose:
                print(f"  Web interface upload error: {e}, falling back to API...")
    
    # Try extension workaround for API upload (bypasses 128 KB/s limit)
    file_ext = os.path.splitext(local_path)[1].lower()
    restricted_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.3gp', '.ogv', '.zip', '.rar', '.7z', '.tar', '.gz', '.db', '.sqlite', '.sqlite3']
    
    if file_ext in restricted_extensions:
        if verbose:
            print(f"  File extension {file_ext} is restricted, using extension workaround...")
        try:
            return upload_to_yandex_disk_with_extension_workaround(local_path, destination_path, oauth_token, verbose)
        except Exception as e:
            if verbose:
                print(f"  Extension workaround failed: {e}, trying standard API upload...")
    
    # Standard API upload (may be slow for restricted file types)
    return upload_to_yandex_disk_api_only(local_path, destination_path, oauth_token, verbose)


def create_structure_tree(video_files: List[Dict], folder_info: List[Dict], tree_file_path: str, verbose: bool = False) -> None:
    """
    Create or update structure tree in markdown file.
    All files are marked as [ ] (not downloaded) by default.
    
    Args:
        video_files: List of video items with relative_path
        folder_info: List of folder items with path
        tree_file_path: Path to tree.md file
        verbose: Enable verbose output
    """
    # Build tree structure from video files and folders
    tree_structure = {}
    
    # First, add all folders to the tree structure
    for folder in folder_info:
        folder_path = folder.get('path', folder.get('name', ''))
        if folder_path:
            path_parts = folder_path.split('/')
            current = tree_structure
            for part in path_parts:
                if part not in current:
                    current[part] = {'type': 'folder', 'children': {}}
                current = current[part]['children']
    
    # Then, add video files to the tree structure
    for video in video_files:
        relative_path = video.get('relative_path', video['name'])
        path_parts = relative_path.split('/')
        
        current = tree_structure
        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:
                # Last part is the file - mark as not downloaded [ ]
                current[part] = {'type': 'file', 'downloaded': False}
            else:
                # It's a folder - create if doesn't exist
                if part not in current:
                    current[part] = {'type': 'folder', 'children': {}}
                current = current[part]['children']
    
    # Read existing tree.md if it exists to preserve downloaded status
    downloaded_files = set()
    partially_downloaded_files = set()
    if os.path.exists(tree_file_path):
        try:
            with open(tree_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                import re
                for line in content.split('\n'):
                    if '✓' in line or '[x]' in line.lower():
                        match = re.search(r'`([^`]+)`', line)
                        if match:
                            downloaded_files.add(match.group(1))
                    elif '[p]' in line.lower():
                        match = re.search(r'`([^`]+)`', line)
                        if match:
                            partially_downloaded_files.add(match.group(1))
        except Exception as e:
            if verbose:
                print(f"Warning: Could not read existing tree.md: {e}")
    
    # Mark files as downloaded or partially downloaded if they were already marked
    def mark_downloaded(node, path=''):
        for key, value in node.items():
            current_path = f"{path}/{key}" if path else key
            if isinstance(value, dict):
                if value.get('type') == 'file':
                    if current_path in downloaded_files:
                        value['downloaded'] = True
                    elif current_path in partially_downloaded_files:
                        value['partially_downloaded'] = True
                elif value.get('type') == 'folder':
                    mark_downloaded(value.get('children', {}), current_path)
    
    mark_downloaded(tree_structure)
    
    # Generate markdown tree
    def build_tree_markdown(node, indent=0, prefix=''):
        lines = []
        items = sorted(node.items())
        for i, (name, value) in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = '└── ' if is_last else '├── '
            next_prefix = prefix + ('    ' if is_last else '│   ')
            
            if isinstance(value, dict):
                if value.get('type') == 'file':
                    # It's a file - show with status [ ] by default
                    if value.get('downloaded', False):
                        status = ' ✓'
                    elif value.get('partially_downloaded', False):
                        status = ' [p]'
                    else:
                        status = ' [ ]'  # Not downloaded
                    lines.append(f"{prefix}{current_prefix}{name}{status}")
                elif value.get('type') == 'folder':
                    # It's a folder - show with / and process children
                    lines.append(f"{prefix}{current_prefix}{name}/")
                    lines.extend(build_tree_markdown(value.get('children', {}), indent + 1, next_prefix))
        
        return lines
    
    tree_lines = build_tree_markdown(tree_structure)
    
    # Write to file
    with open(tree_file_path, 'w', encoding='utf-8') as f:
        f.write("# Структура папок и файлов\n\n")
        f.write("```\n")
        for line in tree_lines:
            f.write(line + '\n')
        f.write("```\n\n")
        f.write("## Статус загрузки\n\n")
        f.write("- ✓ или [x] = файл полностью загружен (скачан и залит на Яндекс Диск)\n")
        f.write("- [p] = файл загружен частично (скачан на компьютер, но не залит на Яндекс Диск)\n")
        f.write("- [ ] = файл не загружен\n\n")
        f.write("## Файлы\n\n")
        for video in sorted(video_files, key=lambda x: x.get('relative_path', x['name'])):
            relative_path = video.get('relative_path', video['name'])
            # Remove leading slash if present (paths should be relative, not absolute)
            relative_path = relative_path.lstrip('/')
            if relative_path in downloaded_files:
                status = 'x'
            elif relative_path in partially_downloaded_files:
                status = 'p'
            else:
                status = ' '  # Not downloaded
            f.write(f"- [{status}] `{relative_path}`\n")
    
    if verbose:
        print(f"Structure tree saved to {tree_file_path}")


def mark_file_partially_downloaded(relative_path: str, tree_file_path: str, verbose: bool = False) -> None:
    """
    Mark file as partially downloaded (downloaded locally but not uploaded) in tree.md.
    
    Args:
        relative_path: Relative path of the file
        tree_file_path: Path to tree.md file
        verbose: Enable verbose output
    """
    if not os.path.exists(tree_file_path):
        return
    
    try:
        with open(tree_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace [ ] with [p] for this file
        import re
        pattern = rf'(\[ \] `{re.escape(relative_path)}`)'
        replacement = f'[p] `{relative_path}`'
        new_content = re.sub(pattern, replacement, content)
        
        # Also replace in tree structure
        pattern2 = rf'(\[ \])(\s*{re.escape(os.path.basename(relative_path))})'
        replacement2 = f'[p]\\2'
        new_content = re.sub(pattern2, replacement2, new_content)
        
        if new_content != content:
            with open(tree_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            if verbose:
                print(f"  Marked {relative_path} as partially downloaded [p]")
    except Exception as e:
        if verbose:
            print(f"  Warning: Could not mark file as partially downloaded: {e}")


def mark_file_downloaded(relative_path: str, tree_file_path: str, verbose: bool = False) -> None:
    """
    Mark file as downloaded (fully uploaded) in tree.md.
    
    Args:
        relative_path: Relative path of the file
        tree_file_path: Path to tree.md file
        verbose: Enable verbose output
    """
    if not os.path.exists(tree_file_path):
        return
    
    try:
        with open(tree_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace [p] or [ ] with [x] for this file
        import re
        pattern = rf'(\[[px ]\] `{re.escape(relative_path)}`)'
        replacement = f'[x] `{relative_path}`'
        new_content = re.sub(pattern, replacement, content)
        
        # Also replace in tree structure (✓ or [p] or [ ] with ✓)
        pattern2 = rf'(\[p\]|\[ \])(\s*{re.escape(os.path.basename(relative_path))})'
        replacement2 = f' ✓\\2'
        new_content = re.sub(pattern2, replacement2, new_content)
        
        if new_content != content:
            with open(tree_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            if verbose:
                print(f"  Marked {relative_path} as downloaded [x]")
    except Exception as e:
        if verbose:
            print(f"  Warning: Could not mark file as downloaded: {e}")


def read_files_from_tree(tree_file_path: str, folder_filter: Optional[str] = None) -> List[Dict]:
    """
    Read list of video files from tree.md file.
    
    Args:
        tree_file_path: Path to tree.md file
        folder_filter: Optional folder name to filter files (e.g., "Замещающий ребенок")
    
    Returns:
        List of file dictionaries with 'relative_path' and 'name' keys
    """
    files = []
    
    if not os.path.exists(tree_file_path):
        return files
    
    try:
        with open(tree_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract files from "## Файлы" section
        files_section_match = re.search(r'## Файлы\s*\n\n(.*?)(?=\n\n|$)', content, re.DOTALL)
        if files_section_match:
            files_text = files_section_match.group(1)
            # Match lines like: - [ ] `path/to/file.mp4` or - [p] `/path/to/file.mp4`
            pattern = r'- \[[px ]\]\s*`?([^`\n]+)`?'
            matches = re.findall(pattern, files_text)
            for match in matches:
                relative_path = match.strip().lstrip('/')  # Remove leading slash
                if not relative_path:
                    continue
                # Apply folder filter if specified
                if folder_filter:
                    if not (relative_path.startswith(folder_filter + '/') or relative_path == folder_filter):
                        continue
                files.append({
                    'relative_path': relative_path,
                    'name': os.path.basename(relative_path)
                })
        
        # Also extract from tree structure (``` block)
        tree_block_match = re.search(r'```\s*\n(.*?)\n```', content, re.DOTALL)
        if tree_block_match:
            tree_lines = tree_block_match.group(1).split('\n')
            current_path = []
            for line in tree_lines:
                # Parse tree structure lines like: │   ├── file.mp4 [ ]
                line = line.strip()
                if not line:
                    continue
                
                # Count indentation
                indent = len(line) - len(line.lstrip())
                level = indent // 4  # Assuming 4 spaces per level
                
                # Extract name and status
                match = re.search(r'[├└]──\s*([^[]+?)(\s*\[[px ]\]|\s*✓)?$', line)
                if match:
                    name = match.group(1).strip()
                    # Remove trailing / for folders
                    if name.endswith('/'):
                        name = name[:-1]
                        is_folder = True
                    else:
                        is_folder = False
                    
                    # Update current path based on level
                    current_path = current_path[:level]
                    current_path.append(name)
                    
                    # If it's a file (has video extension), add it
                    if not is_folder and any(name.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        relative_path = '/'.join(current_path)
                        # Apply folder filter if specified
                        if folder_filter:
                            if not (relative_path.startswith(folder_filter + '/') or relative_path == folder_filter):
                                continue
                        files.append({
                            'relative_path': relative_path,
                            'name': name
                        })
    
    except Exception as e:
        print(f"Warning: Could not read tree.md: {e}")
    
    return files


def find_file_on_page(page, file_name: str, folder_url: str, folder_path: str, verbose: bool = False) -> Optional[str]:
    """
    Find a specific file on Yandex Disk page by name and get its download URL.
    
    Args:
        page: Playwright page instance
        file_name: Name of the file to find
        folder_url: URL of the folder containing the file
        folder_path: Path to the folder (for relative path)
        verbose: Enable verbose output
    
    Returns:
        Download URL if found, None otherwise
    """
    try:
        # Navigate to folder if needed
        current_url = page.url
        if folder_url not in current_url:
            if verbose:
                print(f"  Navigating to folder: {folder_path}")
            page.goto(folder_url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(3000)
            
            # Check for captcha
            captcha_selectors = [
                'text=/[Рр]обот|[Cc]aptcha|[Пп]одтвердите/',
                '[class*="captcha"]',
                '[class*="Captcha"]',
                '[id*="captcha"]',
                '[id*="Captcha"]',
                'iframe[src*="captcha"]',
                'iframe[src*="smartcaptcha"]'
            ]
            
            captcha_solved = False
            while not captcha_solved:
                captcha_found = False
                for selector in captcha_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            captcha_found = True
                            break
                    except:
                        continue
                
                if captcha_found:
                    print("\n" + "="*60)
                    print("CAPTCHA DETECTED!")
                    print("Please solve the captcha in the browser window.")
                    print("After solving, press ENTER to continue...")
                    print("="*60 + "\n")
                    input("Press ENTER after solving captcha...")
                    page.wait_for_timeout(3000)
                    
                    captcha_still_present = False
                    for selector in captcha_selectors:
                        try:
                            elements = page.query_selector_all(selector)
                            if elements and len(elements) > 0:
                                captcha_still_present = True
                                break
                        except:
                            continue
                    
                    if not captcha_still_present:
                        captcha_solved = True
                        print("Captcha solved! Continuing...\n")
                        page.wait_for_timeout(2000)
                else:
                    captcha_solved = True
        
        # Get all elements
        all_elements = page.query_selector_all(
            'a[href*="/d/"], '
            '.file-item, '
            '[data-file-name], '
            '.listing-item, '
            '.resource-item, '
            '.listing-item__title, '
            '.listing-item__title-link, '
            '.resource__name, '
            '.resource__title, '
            '.file__name, '
            'a.resource__name-link, '
            'a[class*="resource"], '
            'a[class*="file"], '
            'a[class*="listing"]'
        )
        
        if len(all_elements) == 0:
            all_elements = page.query_selector_all('a[href]')
        
        # Search for file by name
        file_name_normalized = file_name.lower().strip()
        for element in all_elements:
            try:
                # Get name
                name = (element.get_attribute('data-file-name') or 
                       element.get_attribute('data-resource-name') or
                       element.get_attribute('data-name') or
                       element.get_attribute('title') or
                       element.get_attribute('aria-label') or
                       element.inner_text() or
                       element.text_content())
                
                if not name:
                    continue
                
                name = name.strip()
                name_normalized = name.lower().strip()
                
                # Check if names match
                if name_normalized != file_name_normalized:
                    continue
                
                # Found the file! Now get download URL
                href = element.get_attribute('href')
                if not href:
                    parent_link = element.query_selector('a[href]')
                    if parent_link:
                        href = parent_link.get_attribute('href')
                
                # If no href, try clicking to get streaming URL
                if not href:
                    try:
                        video_urls = []
                        
                        def handle_request(request):
                            url = request.url
                            if 'captcha' in url.lower() or 'smartcaptcha' in url.lower():
                                return
                            if 'streaming.disk.yandex.net' in url or 'streaming.disk.yandex.ru' in url:
                                if '/hls/' in url or url.endswith('.m3u8'):
                                    video_urls.append(url)
                        
                        page.on('request', handle_request)
                        element.click(timeout=10000)
                        page.wait_for_timeout(3000)
                        # Note: Playwright doesn't have page.off() - handler will be cleaned up automatically
                        
                        if video_urls:
                            href = video_urls[0]
                            # Close overlay
                            try:
                                page.keyboard.press('Escape')
                                page.wait_for_timeout(500)
                            except:
                                pass
                    except Exception as e:
                        if verbose:
                            print(f"    Warning: Could not get link for {name}: {e}")
                
                if not href:
                    if verbose:
                        print(f"    No href found for {name}")
                    continue
                
                # Construct full URL
                if href.startswith('/'):
                    if 'disk.yandex.ru' in folder_url or 'disk.yandex.ru' in href:
                        full_url = f"https://disk.yandex.ru{href}"
                    else:
                        full_url = f"https://yadi.sk{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                
                if verbose:
                    print(f"    ✓ Found file: {name} -> {full_url}")
                return full_url
                
            except Exception as e:
                if verbose:
                    print(f"    Warning: Error processing element: {e}")
                continue
        
        if verbose:
            print(f"    ✗ File not found: {file_name}")
        return None
        
    except Exception as e:
        if verbose:
            print(f"  Error finding file {file_name}: {e}")
        return None


def is_file_downloaded(relative_path: str, tree_file_path: str) -> Tuple[bool, bool]:
    """
    Check if file is already downloaded (fully or partially) according to tree.md.
    
    Args:
        relative_path: Relative path of the file
        tree_file_path: Path to tree.md file
    
    Returns:
        Tuple of (is_fully_downloaded, is_partially_downloaded)
    """
    if not os.path.exists(tree_file_path):
        return (False, False)
    
    try:
        with open(tree_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for fully downloaded (✓ or [x])
        import re
        # Check for [x] marker
        if re.search(rf'\[x\] `{re.escape(relative_path)}`', content):
            return (True, False)
        # Check for ✓ marker (can be on same line or separate)
        if re.search(rf'✓.*`{re.escape(relative_path)}`', content) or \
           (re.search(rf'✓', content) and relative_path in content and 
            any(line.strip().startswith('✓') and relative_path in line for line in content.split('\n'))):
            return (True, False)
        
        # Check for partially downloaded [p]
        if f'[p] `{relative_path}`' in content:
            import re
            if re.search(rf'\[p\] `{re.escape(relative_path)}`', content):
                return (False, True)
        
        return (False, False)
    except Exception as e:
        return (False, False)


if __name__ == '__main__':
    # Load environment variables
    load_env_file()
    
    try:
        
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description='Download videos from public Yandex Disk folder and upload to your Yandex Disk',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument('public_folder_url', nargs='?', help='Public Yandex Disk folder URL')
        parser.add_argument('destination_path', nargs='?', help='Destination path on your Yandex Disk (must start with /)')
        parser.add_argument('--oauth-token', help='OAuth token for Yandex Disk API (overrides .env)')
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
        parser.add_argument('--dry-run', action='store_true', help='Dry run mode (parse only, no download/upload)')
        parser.add_argument('--test', action='store_true', help='Test mode (process only first video)')
        parser.add_argument('--parse-only', action='store_true', help='Parse-only mode (create tree.md and folder structure, no download/upload)')
        parser.add_argument('--folder', help='Process only files from specified folder (e.g., "Замещающий ребенок")')
        parser.add_argument('--use-tree', action='store_true', help='Use file list from tree.md instead of parsing (requires tree.md to exist)')
        parser.add_argument('--upload-only', action='store_true', help='Upload only mode: skip downloading, upload already downloaded files from local cache')
        
        args = parser.parse_args()
        
        # Get configuration
        # In upload-only mode, public_folder_url is not required
        if args.upload_only:
            public_folder_url = args.public_folder_url or get_public_folder_url() if args.public_folder_url or os.getenv('YANDEX_PUBLIC_FOLDER_URL') else None
        else:
            public_folder_url = args.public_folder_url or get_public_folder_url()
        
        destination_path = args.destination_path or (None if args.parse_only else get_destination_path())
        oauth_token = args.oauth_token or (None if args.parse_only else get_oauth_token())
        
        # Initialize download_immediately flag (will be set in parsing mode)
        download_immediately = False
        
        # Validate arguments (skip URL validation in upload-only mode)
        if not args.upload_only and not validate_public_url(public_folder_url):
            print(f"Error: Invalid public folder URL: {public_folder_url}")
            print("URL must be a valid Yandex Disk public folder link (disk.yandex.ru/d/... or yadi.sk/d/...)")
            sys.exit(EXIT_INVALID_ARGS)
        
        if not args.parse_only and destination_path and not validate_destination_path(destination_path):
            print(f"Error: Invalid destination path: {destination_path}")
            print("Destination path must start with / (e.g., /Videos/MyFolder)")
            sys.exit(EXIT_INVALID_ARGS)
        
        if args.verbose:
            print(f"Public folder URL: {public_folder_url}")
            if not args.parse_only:
                print(f"Destination path: {destination_path}")
            print(f"Dry run: {args.dry_run}")
            print(f"Test mode: {args.test}")
            print(f"Parse only: {args.parse_only}")
            if args.folder:
                print(f"Folder filter: {args.folder}")
            if args.use_tree:
                print(f"Using tree.md: Yes")
            if args.upload_only:
                print(f"Upload only mode: Yes (will skip downloading, upload existing local files)")
        
        # Initialize browser
        browser = None
        context = None
        page = None
        playwright_instance = None
        folder_info = []  # Initialize folder_info for use-tree mode
        
        # Use tree.md if requested
        if args.use_tree:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            tree_file_path = os.path.join(script_dir, 'tree.md')
            
            if not os.path.exists(tree_file_path):
                print(f"Error: tree.md not found at {tree_file_path}")
                print("Please run with --parse-only first to create tree.md")
                sys.exit(EXIT_INVALID_ARGS)
            
            # Read files from tree.md
            print("Reading file list from tree.md...")
            tree_files = read_files_from_tree(tree_file_path, folder_filter=args.folder)
            
            if not tree_files:
                print("No files found in tree.md")
                sys.exit(EXIT_SUCCESS)
            
            print(f"Found {len(tree_files)} file(s) in tree.md")
            
            # In upload-only mode, skip browser and just use file list
            if args.upload_only:
                # Just create video_files list from tree.md without browser
                video_files = []
                for tree_file in tree_files:
                    video_files.append({
                        'name': tree_file['name'],
                        'download_url': None,  # Not needed for upload-only
                        'relative_path': tree_file['relative_path'],
                        'order': len(video_files)
                    })
                if args.verbose:
                    print(f"Upload-only mode: using {len(video_files)} files from tree.md")
                print(f"DEBUG: Created {len(video_files)} video_files in upload-only mode")
            else:
                # Initialize browser for finding files
                from playwright.sync_api import sync_playwright
                playwright_instance = sync_playwright().start()
                
                # Try to use system Chrome instead of Chromium
                try:
                    import shutil
                    chrome_paths = [
                        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                        '/Applications/Chromium.app/Contents/MacOS/Chromium',
                        shutil.which('google-chrome'),
                        shutil.which('chromium'),
                        shutil.which('chromium-browser'),
                    ]
                    chrome_executable = None
                    for path in chrome_paths:
                        if path and os.path.exists(path):
                            chrome_executable = path
                            if args.verbose:
                                print(f"Using system browser: {path}")
                            break
                    
                    browser = playwright_instance.chromium.launch(
                        headless=False,
                        executable_path=chrome_executable,
                        args=[
                            '--enable-features=VaapiVideoDecoder',
                            '--use-gl=egl',
                            '--enable-hardware-acceleration',
                        ]
                    )
                except Exception as e:
                    if args.verbose:
                        print(f"Could not use system Chrome, using Playwright Chromium: {e}")
                    browser = playwright_instance.chromium.launch(headless=False)
                
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    java_script_enabled=True,
                )
                page = context.new_page()
                
                # Navigate to root folder
                page.goto(public_folder_url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(3000)
                
                # For each file, find it on the page and get download URL
                video_files = []
                for tree_file in tree_files:
                    relative_path = tree_file['relative_path']
                    file_name = tree_file['name']
                    
                    # Determine folder path and URL
                    if '/' in relative_path:
                        folder_path = '/'.join(relative_path.split('/')[:-1])
                        # Build folder URL (simplified - assumes same structure)
                        # For now, use root URL and navigate by clicking folders
                        folder_url = public_folder_url
                    else:
                        folder_path = ""
                        folder_url = public_folder_url
                    
                    if args.verbose:
                        print(f"Finding file: {relative_path}")
                    
                    # Find file on page
                    download_url = find_file_on_page(page, file_name, folder_url, folder_path, args.verbose)
                    
                    if download_url:
                        video_files.append({
                            'name': file_name,
                            'download_url': download_url,
                            'relative_path': relative_path,
                            'order': len(video_files)
                        })
                        if args.verbose:
                            print(f"  ✓ Found: {relative_path}")
                    else:
                        print(f"  ✗ Could not find: {relative_path}")
            
            # After creating video_files in upload-only mode, continue to processing
            if args.upload_only:
                if args.verbose:
                    print(f"Upload-only mode: {len(video_files)} files ready for upload")
                # Skip browser initialization, continue to processing
                folder_info = []  # Initialize folder_info for upload-only mode
                # Continue to processing section below (skip normal parsing)
                # video_files is already set, so we'll skip the else block
        else:
            # Normal parsing mode
            try:
                if args.verbose:
                    print("Parsing public folder...")
                
                # Get paths and tokens (will be set later if not in parse-only mode)
                script_dir = os.path.dirname(os.path.abspath(__file__))
                tree_file_path_for_parse = os.path.join(script_dir, 'tree.md')
                cache_dir_for_parse = os.path.join(script_dir, 'videos')
                
                # Enable immediate download/upload (unless parse-only mode)
                download_immediately = not args.parse_only
                
                items, folder_info, browser, context, page, playwright_instance = parse_public_folder(
                    public_folder_url, "", args.verbose, 
                    test_mode=args.test, 
                    processed_folder_urls=set(),
                    cache_dir=cache_dir_for_parse if download_immediately else None,
                    tree_file_path=tree_file_path_for_parse if download_immediately else None,
                    destination_path=destination_path if download_immediately else None,
                    oauth_token=oauth_token if download_immediately else None,
                    download_immediately=download_immediately
                )
                
                # Filter video files (will be empty if download_immediately=True)
                video_files = filter_video_files(items)
            except Exception as e:
                print(f"Error during parsing: {e}")
                sys.exit(EXIT_ERROR)
            
            # Filter by folder if specified
            if args.folder:
                folder_name = args.folder
                original_count = len(video_files)
                video_files = [v for v in video_files if v.get('relative_path', v['name']).startswith(folder_name + '/') or v.get('relative_path', v['name']) == folder_name]
                if args.verbose:
                    print(f"Filtered to folder '{folder_name}': {len(video_files)}/{original_count} files")
                if not video_files:
                    print(f"No video files found in folder '{folder_name}'")
                    if not args.parse_only:
                        # Cleanup browser before exit
                        if context:
                            try:
                                context.close()
                            except:
                                pass
                        if browser:
                            try:
                                browser.close()
                            except:
                                pass
                        if playwright_instance:
                            try:
                                playwright_instance.stop()
                            except:
                                pass
                        sys.exit(EXIT_SUCCESS)
            
            # Even if no videos found, continue to create folder structure
            if not video_files:
                if not args.parse_only:
                    print("No video files found in folder.")
                    # Cleanup browser before exit
                    if context:
                        try:
                            context.close()
                        except:
                            pass
                    if browser:
                        try:
                            browser.close()
                        except:
                            pass
                    if playwright_instance:
                        try:
                            playwright_instance.stop()
                        except:
                            pass
                    sys.exit(EXIT_SUCCESS)
                else:
                    print("No video files found in folder, but continuing to create folder structure...")
        
        # Common processing section for both use-tree and normal parsing modes
        # Sort by order
        if 'video_files' in locals() and video_files:
            video_files.sort(key=lambda x: x.get('order', 0))
        else:
            if 'video_files' not in locals():
                video_files = []
        
        total_found = len(video_files)
        
        # Test mode: process only first video
        if args.test and not args.parse_only:
            print("TEST MODE: Processing only the first video")
            video_files = video_files[:1]
            print(f"Found {total_found} video file(s) in folder (test mode: processing 1)")
        else:
            if args.upload_only:
                print(f"Found {total_found} video file(s) from tree.md (upload-only mode)")
            else:
                print(f"Found {total_found} video file(s) in folder (including nested subfolders)")
        
        total_videos = len(video_files)
        
        # Get tree file path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tree_file_path = os.path.join(script_dir, 'tree.md')
        
        # Create structure tree in tree.md (only if not using tree.md)
        if not args.use_tree:
            if video_files:
                # Get folder_info if available (only in parsing mode)
                folder_info = folder_info if 'folder_info' in locals() else []
                create_structure_tree(video_files, folder_info, tree_file_path, args.verbose)
                print(f"Structure tree created/updated: {tree_file_path}")
            elif 'folder_info' in locals() and folder_info:
                # Create folder structure tree if no videos but folders exist
                print(f"Creating folder structure tree (no videos found, but {len(folder_info)} folder(s) found)...")
                tree_structure = {}
                for folder in folder_info:
                    folder_path = folder.get('path', folder.get('name', ''))
                    path_parts = folder_path.split('/')
                    current = tree_structure
                    for part in path_parts:
                        if part not in current:
                            current[part] = {'type': 'folder', 'children': {}}
                        current = current[part]['children']
                
                def build_tree_markdown(node, indent=0, prefix=''):
                    lines = []
                    items = sorted(node.items())
                    for i, (name, value) in enumerate(items):
                        is_last = i == len(items) - 1
                        current_prefix = '└── ' if is_last else '├── '
                        next_prefix = prefix + ('    ' if is_last else '│   ')
                        
                        if isinstance(value, dict):
                            if value.get('type') == 'folder':
                                lines.append(f"{prefix}{current_prefix}{name}/")
                                lines.extend(build_tree_markdown(value.get('children', {}), indent + 1, next_prefix))
                    
                    return lines
                
                tree_lines = build_tree_markdown(tree_structure)
                
                with open(tree_file_path, 'w', encoding='utf-8') as f:
                    f.write("# Структура папок и файлов\n\n")
                    f.write("```\n")
                    for line in tree_lines:
                        f.write(line + '\n')
                    f.write("```\n\n")
                    f.write("## Статус загрузки\n\n")
                    f.write("- ✓ или [x] = файл полностью загружен (скачан и залит на Яндекс Диск)\n")
                    f.write("- [p] = файл загружен частично (скачан на компьютер, но не залит на Яндекс Диск)\n")
                    f.write("- [ ] = файл не загружен\n\n")
                    f.write("## Файлы\n\n")
                    f.write("(Видеофайлы не найдены)\n")
                print(f"Structure tree created: {tree_file_path}")
        
        # Create folder structure in videos/ directory
        cache_dir = os.path.join(script_dir, 'videos')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Collect all folder paths from video files and folder_info
        all_folder_paths = set()
        
        # Add folders from video files
        for video in video_files:
            relative_path = video.get('relative_path', video['name'])
            path_parts = relative_path.split('/')
            
            if len(path_parts) > 1:
                for i in range(1, len(path_parts)):
                    folder_path = '/'.join(path_parts[:i])
                    all_folder_paths.add(folder_path)
        
        # Add folders from folder_info
        import re
        cleaned_folder_paths = set()
        # folder_info may not be defined in upload-only mode
        if 'folder_info' in locals() and folder_info:
            for folder in folder_info:
                folder_path = folder.get('path', folder.get('name', ''))
                if folder_path:
                    path_parts = folder_path.split('/')
                    cleaned_parts = []
                    for part in path_parts:
                        cleaned_part = re.sub(r'\s*\d{1,2}\.\d{1,2}\.\d{2,4}.*$', '', part).strip()
                        if not cleaned_part or len(cleaned_part) < 2:
                            cleaned_part = part
                        cleaned_parts.append(cleaned_part)
                    cleaned_path = '/'.join(cleaned_parts)
                    cleaned_folder_paths.add(cleaned_path)
                    for i in range(1, len(cleaned_parts)):
                        parent_path = '/'.join(cleaned_parts[:i])
                        cleaned_folder_paths.add(parent_path)
        
        if cleaned_folder_paths:
            all_folder_paths.update(cleaned_folder_paths)
        
        # Create folder structure
        final_folder_paths = set()
        for folder_path in all_folder_paths:
            path_parts = folder_path.split('/')
            cleaned_parts = []
            for part in path_parts:
                cleaned_part = re.sub(r'\s*\d{1,2}\.\d{1,2}\.\d{2,4}.*$', '', part).strip()
                if not cleaned_part or len(cleaned_part) < 2:
                    cleaned_part = part
                cleaned_parts.append(cleaned_part)
            final_path = '/'.join(cleaned_parts)
            final_folder_paths.add(final_path)
        
        for folder_path in sorted(final_folder_paths):
            path_parts = folder_path.split('/')
            sanitized_folder_parts = [sanitize_folder_name(part) for part in path_parts]
            local_folder_path = os.path.join(cache_dir, *sanitized_folder_parts)
            os.makedirs(local_folder_path, exist_ok=True)
            if args.verbose:
                print(f"  Created folder: {local_folder_path}")
        
        if args.parse_only:
            print(f"\nParse-only mode: tree.md and folder structure in {cache_dir} created.")
            print("Browser will remain open for 10 seconds for inspection, then will close automatically.")
            print("Press Ctrl+C to close immediately.")
            try:
                import time
                time.sleep(10)
            except KeyboardInterrupt:
                print("\nClosing browser...")
            # Cleanup browser
            if 'context' in locals() and context:
                try:
                    context.close()
                except:
                    pass
            if 'browser' in locals() and browser:
                try:
                    browser.close()
                except:
                    pass
            if 'playwright_instance' in locals() and playwright_instance:
                try:
                    playwright_instance.stop()
                except:
                    pass
            sys.exit(EXIT_SUCCESS)
        
        # If download_immediately was enabled, videos are already processed
        download_immediately_used = 'download_immediately' in locals() and download_immediately
        if download_immediately_used and total_videos == 0:
            print("\nAll videos have been processed immediately during parsing.")
            print("No additional download/upload needed.")
            # Cleanup browser
            if 'context' in locals() and context:
                try:
                    context.close()
                except:
                    pass
            if 'browser' in locals() and browser:
                try:
                    browser.close()
                except:
                    pass
            if 'playwright_instance' in locals() and playwright_instance:
                try:
                    playwright_instance.stop()
                except:
                    pass
            sys.exit(EXIT_SUCCESS)
        
        # Download and upload videos
        if args.dry_run:
            print("\nDRY RUN MODE: Would download and upload the following videos:")
            for video in video_files:
                print(f"  - {video.get('relative_path', video['name'])}")
            sys.exit(EXIT_SUCCESS)
        
        print(f"\nStarting download and upload of {total_videos} video(s)...")
        print(f"DEBUG: About to start processing {total_videos} videos")
        if args.verbose:
            print(f"Upload-only mode: {args.upload_only}")
            print(f"Total videos to process: {total_videos}")
        
        successful = 0
        failed = 0
        
        for idx, video in enumerate(video_files, 1):
            video_name = video['name']
            download_url = video.get('download_url')
            relative_path = video.get('relative_path', video_name)
            
            # Clean relative_path: remove leading slash and newlines
            relative_path = relative_path.lstrip('/').replace('\n', ' ').replace('\r', ' ').strip()
            
            # In upload-only mode, download_url is not required
            if not args.upload_only and not download_url:
                print(f"Warning: No download URL for {relative_path}, skipping...")
                failed += 1
                continue
            
            # Check if file is already downloaded
            is_fully_downloaded, is_partially_downloaded = is_file_downloaded(relative_path, tree_file_path)
            if is_fully_downloaded:
                print(f"Skipping {relative_path} ({idx}/{total_videos}) - already fully downloaded")
                successful += 1
                continue
            
            # Build local path
            # Clean path parts: remove empty parts and newlines
            path_parts = [part.strip().replace('\n', ' ').replace('\r', ' ') for part in relative_path.split('/') if part.strip()]
            sanitized_parts = [sanitize_folder_name(part) if i < len(path_parts) - 1 else sanitize_filename(part) 
                               for i, part in enumerate(path_parts)]
            
            if len(path_parts) > 1:
                folder_parts = sanitized_parts[:-1]
                local_folder_path = os.path.join(cache_dir, *folder_parts)
                os.makedirs(local_folder_path, exist_ok=True)
            
            local_path = os.path.join(cache_dir, *sanitized_parts)
            
            # In upload-only mode, skip download and check if file exists locally
            if args.upload_only:
                if os.path.exists(local_path) and os.path.getsize(local_path) > 1024 * 1024:  # File exists and > 1MB
                    print(f"File {relative_path} ({idx}/{total_videos}) found locally - skipping download, proceeding to upload")
                    skip_download = True
                else:
                    print(f"File {relative_path} ({idx}/{total_videos}) not found locally - skipping (use without --upload-only to download)")
                    failed += 1
                    continue
            else:
                skip_download = is_partially_downloaded
                if skip_download:
                    print(f"File {relative_path} ({idx}/{total_videos}) is partially downloaded - skipping download, proceeding to upload")
            
            # Download video
            if not skip_download:
                print(f"\nDownloading {relative_path} ({idx}/{total_videos})...")
                if download_video(download_url, local_path, args.verbose, page):
                    mark_file_partially_downloaded(relative_path, tree_file_path, args.verbose)
                else:
                    print(f"ERROR: Failed to download {relative_path}")
                    print("Stopping execution due to download failure (per sequential processing algorithm)")
                    # Cleanup browser before exit
                    if 'context' in locals() and context:
                        try:
                            context.close()
                        except:
                            pass
                    if 'browser' in locals() and browser:
                        try:
                            browser.close()
                        except:
                            pass
                    if 'playwright_instance' in locals() and playwright_instance:
                        try:
                            playwright_instance.stop()
                        except:
                            pass
                    sys.exit(EXIT_ERROR)
            else:
                if not os.path.exists(local_path):
                    print(f"Warning: Partially downloaded file not found at {local_path}, re-downloading...")
                    if not download_video(download_url, local_path, args.verbose, page):
                        print(f"ERROR: Failed to re-download {relative_path}")
                        print("Stopping execution due to download failure (per sequential processing algorithm)")
                        # Cleanup browser before exit
                        if 'context' in locals() and context:
                            try:
                                context.close()
                            except:
                                pass
                        if 'browser' in locals() and browser:
                            try:
                                browser.close()
                            except:
                                pass
                        if 'playwright_instance' in locals() and playwright_instance:
                            try:
                                playwright_instance.stop()
                            except:
                                pass
                        sys.exit(EXIT_ERROR)
            
            # Upload to Yandex Disk
            if destination_path and oauth_token:
                # Remove leading slash from relative_path if present to avoid double slashes
                clean_relative_path = relative_path.lstrip('/')
                # Build full destination path properly
                if destination_path.endswith('/'):
                    full_destination = f"{destination_path}{clean_relative_path}"
                else:
                    full_destination = f"{destination_path}/{clean_relative_path}"
                print(f"Uploading {relative_path} to {full_destination}...")
                try:
                    # Create folder structure on Yandex Disk
                    if len(path_parts) > 1:
                        folder_path = '/'.join(path_parts[:-1])
                        # Remove leading slash from folder_path if present
                        folder_path = folder_path.lstrip('/')
                        create_folder_structure(destination_path, folder_path, oauth_token, args.verbose)
                    
                    upload_to_yandex_disk(local_path, full_destination, oauth_token, args.verbose)
                    mark_file_downloaded(relative_path, tree_file_path, args.verbose)
                    successful += 1
                    
                    # Delete local file after successful upload
                    try:
                        os.remove(local_path)
                        if args.verbose:
                            print(f"  Deleted local file: {local_path}")
                    except Exception as e:
                        if args.verbose:
                            print(f"  Warning: Could not delete local file: {e}")
                except Exception as e:
                    print(f"ERROR: Failed to upload {relative_path}: {e}")
                    print("Stopping execution due to upload failure (per sequential processing algorithm)")
                    # Cleanup browser before exit
                    if 'context' in locals() and context:
                        try:
                            context.close()
                        except:
                            pass
                    if 'browser' in locals() and browser:
                        try:
                            browser.close()
                        except:
                            pass
                    if 'playwright_instance' in locals() and playwright_instance:
                        try:
                            playwright_instance.stop()
                        except:
                            pass
                    sys.exit(EXIT_ERROR)
            else:
                print(f"Skipping upload (no destination path or OAuth token)")
                successful += 1
        
        print(f"\nCompleted: {successful} successful, {failed} failed")
        
        if 'successful' in locals() and 'failed' in locals():
            sys.exit(EXIT_SUCCESS if successful > 0 or failed == 0 else EXIT_ERROR)
        else:
            sys.exit(EXIT_SUCCESS)
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(EXIT_ERROR)
    except Exception as e:
        print(f"Error: {e}")
        if 'args' in locals() and args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(EXIT_ERROR)
    finally:
        # Cleanup browser
        if 'context' in locals() and context:
            try:
                context.close()
            except:
                pass
        if 'browser' in locals() and browser:
            try:
                browser.close()
            except:
                pass
        if 'playwright_instance' in locals() and playwright_instance:
            try:
                playwright_instance.stop()
            except:
                pass
