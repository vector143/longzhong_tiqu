import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawl.investing_crawler import InvestingCommodityNewsCrawler


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200, headers: dict | None = None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


def test_fetch_article_content_prefers_json_ld_publish_time_over_sidebar_time(
    monkeypatch,
):
    html = """
    <html>
      <body>
        <article class="article">
          <header>
            <h1>Take Five: Deja vu?</h1>
          </header>
          <div class="articlePage">
            <p>LONDON, March 13 (Reuters) - War in the Middle East...</p>
          </div>
        </article>
        <aside>
          <div>Industry Spotlight</div>
          <time datetime="2025-08-12 06:58:08">Aug 12, 2025</time>
        </aside>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "datePublished": "2026-03-13T07:32:45.000+00:00",
            "dateModified": "2026-03-13T07:36:25.000+00:00"
          }
        </script>
      </body>
    </html>
    """
    crawler = InvestingCommodityNewsCrawler(session=requests.Session())
    monkeypatch.setattr(
        crawler.session, "get", lambda *args, **kwargs: DummyResponse(html)
    )

    result = crawler.fetch_article_content(
        "https://www.investing.com/news/economy-news/take-five-deja-vu-4559066"
    )

    assert result["success"] is True
    assert result["publish_time"] == "2026-03-13 07:36:25"


def test_fetch_article_content_prefers_article_header_time_over_global_time(
    monkeypatch,
):
    html = """
    <html>
      <body>
        <article class="article">
          <header>
            <h1>Take Five: Deja vu?</h1>
            <div>Published 03/13/2026, 03:32 AM Updated 03/13/2026, 03:36 AM</div>
          </header>
          <div class="articlePage">
            <p>LONDON, March 13 (Reuters) - War in the Middle East...</p>
          </div>
        </article>
        <aside>
          <div>Industry Spotlight</div>
          <time datetime="2025-08-12 06:58:08">Aug 12, 2025</time>
        </aside>
      </body>
    </html>
    """
    crawler = InvestingCommodityNewsCrawler(session=requests.Session())
    monkeypatch.setattr(
        crawler.session, "get", lambda *args, **kwargs: DummyResponse(html)
    )

    result = crawler.fetch_article_content(
        "https://www.investing.com/news/economy-news/take-five-deja-vu-4559066"
    )

    assert result["success"] is True
    assert result["publish_time"] == "2026-03-13 03:36:00"
