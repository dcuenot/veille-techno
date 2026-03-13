from unittest.mock import patch, MagicMock

from src.collector.github_trending import GitHubTrendingSource

SAMPLE_HTML = """
<html><body>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/user/repo-one">user / repo-one</a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">A cool project description</p>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/org/repo-two">org / repo-two</a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">Another project</p>
</article>
</body></html>
"""

@patch("src.collector.github_trending.requests.get")
def test_github_trending_fetches_repos(mock_get: MagicMock):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_HTML
    mock_get.return_value = mock_response

    source = GitHubTrendingSource(name="GitHub Trending", category="tech")
    articles = source.fetch()

    assert len(articles) == 2
    assert "repo-one" in articles[0].title
    assert articles[0].url == "https://github.com/user/repo-one"
    assert articles[0].summary == "A cool project description"

@patch("src.collector.github_trending.requests.get")
def test_github_trending_returns_empty_on_error(mock_get: MagicMock):
    mock_get.side_effect = Exception("Scraping failed")
    source = GitHubTrendingSource(name="GitHub Trending", category="tech")
    articles = source.fetch()
    assert articles == []
