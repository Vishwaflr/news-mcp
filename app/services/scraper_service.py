"""
Web Scraper Service
Extracts full article content from URLs using httpx + BeautifulSoup + readability
"""
import httpx
from bs4 import BeautifulSoup
from readability import Document
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ScraperService:
    """
    Multi-strategy web scraper for extracting article content

    Uses:
    1. httpx for HTTP requests (fast, async-capable)
    2. BeautifulSoup for HTML parsing
    3. Readability algorithm for main content extraction
    """

    def __init__(self, timeout: float = 30.0, user_agent: Optional[str] = None):
        """
        Initialize scraper service

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent (defaults to news-mcp bot)
        """
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (compatible; news-mcp/1.0; +https://github.com/yourusername/news-mcp)"
        )

    async def scrape_article(
        self,
        url: str,
        extract_images: bool = False,
        extract_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape full article content from URL

        Args:
            url: Article URL to scrape
            extract_images: Whether to extract image URLs
            extract_metadata: Whether to extract author/published date

        Returns:
            {
                "success": bool,
                "url": str,
                "title": str | None,
                "content": str | None,
                "author": str | None,
                "published_date": datetime | None,
                "images": List[str] | None,
                "word_count": int,
                "scrape_status": str,  # "success", "paywall", "error", "timeout"
                "error": str | None,
                "scraped_at": datetime
            }
        """
        result = {
            "success": False,
            "url": url,
            "title": None,
            "content": None,
            "author": None,
            "published_date": None,
            "images": None,
            "word_count": 0,
            "scrape_status": "error",
            "error": None,
            "scraped_at": datetime.now()
        }

        try:
            # Fetch HTML content
            html = await self._fetch_html(url)

            if not html:
                result["error"] = "Failed to fetch HTML"
                result["scrape_status"] = "error"
                return result

            # Check for paywall indicators
            if self._is_paywall(html):
                result["error"] = "Paywall detected"
                result["scrape_status"] = "paywall"
                logger.info(f"Paywall detected: {url}")
                return result

            # Extract content using readability
            doc = Document(html)
            content_html = doc.summary()
            title = doc.title()

            # Convert HTML to clean text
            soup = BeautifulSoup(content_html, 'lxml')

            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'aside']):
                element.decompose()

            # Extract clean text
            content_text = soup.get_text(separator='\n', strip=True)

            # Clean up excessive newlines
            content_text = '\n'.join(line.strip() for line in content_text.splitlines() if line.strip())

            # Validate content quality
            if len(content_text) < 100:
                result["error"] = "Content too short (likely extraction failed)"
                result["scrape_status"] = "error"
                return result

            # Check if this looks like a landing page (many links, little text)
            link_density = len(soup.find_all('a')) / max(1, len(content_text.split()))
            if link_density > 0.3:  # More than 30% link-to-text ratio
                result["error"] = "Looks like a landing page (too many links, not an article)"
                result["scrape_status"] = "error"
                logger.warning(f"Landing page detected: {url} (link density: {link_density:.2f})")
                return result

            # Count words
            word_count = len(content_text.split())

            result.update({
                "success": True,
                "title": title,
                "content": content_text,
                "word_count": word_count,
                "scrape_status": "success"
            })

            # Extract metadata if requested
            if extract_metadata:
                metadata = self._extract_metadata(soup, html)
                result["author"] = metadata.get("author")
                result["published_date"] = metadata.get("published_date")

            # Extract images if requested
            if extract_images:
                result["images"] = self._extract_images(soup, url)

            logger.info(f"Scraped successfully: {url} ({word_count} words)")
            return result

        except httpx.TimeoutException:
            result["error"] = "Request timeout"
            result["scrape_status"] = "timeout"
            logger.warning(f"Scrape timeout: {url}")
            return result

        except Exception as e:
            result["error"] = str(e)
            result["scrape_status"] = "error"
            logger.error(f"Scrape failed for {url}: {e}")
            return result

    async def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers=headers
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def _is_paywall(self, html: str) -> bool:
        """Detect paywall indicators in HTML"""
        paywall_indicators = [
            'subscribe to read',
            'subscription required',
            'premium content',
            'sign in to continue',
            'this article is for subscribers',
            'continue reading with unlimited access',
            'paywall',
            'data-paywall',
            'subscriber-only',
            'premium-article'
        ]

        html_lower = html.lower()
        return any(indicator in html_lower for indicator in paywall_indicators)

    def _extract_metadata(self, soup: BeautifulSoup, html: str) -> Dict[str, Any]:
        """Extract author and published date from HTML"""
        metadata = {
            "author": None,
            "published_date": None
        }

        # Try meta tags first
        author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
        if author_meta:
            metadata["author"] = author_meta.get('content')

        # Try common author selectors
        if not metadata["author"]:
            author_selectors = [
                {'class': 'author'},
                {'class': 'byline'},
                {'rel': 'author'},
                {'itemprop': 'author'}
            ]
            for selector in author_selectors:
                author_elem = soup.find(attrs=selector)
                if author_elem:
                    metadata["author"] = author_elem.get_text(strip=True)
                    break

        # Try published date from meta tags
        date_meta = (
            soup.find('meta', {'property': 'article:published_time'}) or
            soup.find('meta', {'name': 'date'}) or
            soup.find('meta', {'name': 'publish-date'})
        )
        if date_meta:
            try:
                from dateutil import parser
                metadata["published_date"] = parser.parse(date_meta.get('content'))
            except:
                pass

        # Try time tag
        if not metadata["published_date"]:
            time_elem = soup.find('time', {'datetime': True})
            if time_elem:
                try:
                    from dateutil import parser
                    metadata["published_date"] = parser.parse(time_elem['datetime'])
                except:
                    pass

        return metadata

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract image URLs from article"""
        images = []

        # Find all images in article content
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                # Make relative URLs absolute
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"

                # Filter out tracking pixels and tiny images
                width = img.get('width')
                height = img.get('height')
                if width and height:
                    try:
                        if int(width) < 100 or int(height) < 100:
                            continue
                    except:
                        pass

                images.append(src)

        return images[:10]  # Limit to 10 images

    def is_valid_content(self, content: str, min_words: int = 50) -> bool:
        """
        Check if scraped content looks valid

        Args:
            content: Scraped text content
            min_words: Minimum word count to consider valid

        Returns:
            True if content looks legitimate
        """
        if not content:
            return False

        word_count = len(content.split())

        # Too short
        if word_count < min_words:
            return False

        # Check for error page indicators
        error_indicators = [
            '404 not found',
            'page not found',
            'access denied',
            'forbidden',
            'error 403',
            'error 404',
            'error 500'
        ]

        content_lower = content.lower()[:500]  # Check first 500 chars
        if any(indicator in content_lower for indicator in error_indicators):
            return False

        return True
