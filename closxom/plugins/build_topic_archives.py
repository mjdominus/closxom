"""Plugin to build topic/tag archive pages."""

from collections import defaultdict
from closxom.plugin.plugin import Plugin
from closxom.skrap import PageSkrap


class BuildTopicArchivesPlugin(Plugin):
    """Creates PageSkrap products for topic/tag archives.

    Groups articles by their tags/topics and creates archive pages.
    """

    @classmethod
    def name(cls):
        return "build-topic-archives"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return ["page"]

    def run(self):
        """Create topic archive pages."""
        articles = self.db.find_all_published_articles()

        # Group articles by topic/tag
        topic_archives = defaultdict(list)

        for article in articles:
            # Get tags from metadata
            tags = article.meta.get('tags', [])

            # Also check for 'topic' or 'category' field
            if 'topic' in article.meta:
                topic = article.meta['topic']
                if isinstance(topic, str):
                    tags.append(topic)
                elif isinstance(topic, list):
                    tags.extend(topic)

            if 'category' in article.meta:
                category = article.meta['category']
                if isinstance(category, str):
                    tags.append(category)
                elif isinstance(category, list):
                    tags.extend(category)

            # Parse tags if they're a comma-separated string
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',')]

            # Add article to each topic archive
            for tag in tags:
                if tag:
                    topic_archives[tag].append(article.id)

        pages_created = 0

        # Create a page for each topic
        for topic, article_ids in topic_archives.items():
            # Sort by date (newest first)
            article_ids_sorted = self.sort_articles_by_date(article_ids, reverse=True)

            # Create URL-friendly topic name
            topic_slug = topic.lower().replace(' ', '-')

            page = PageSkrap(
                name=f"archive:topic:{topic_slug}",
                owner=self.name(),
                meta={
                    'article_ids': article_ids_sorted,
                    'output_path': f"topic/{topic_slug}/index.html",
                    'page_type': 'topic_archive',
                    'title': f"Articles about {topic}",
                    'topic': topic
                }
            )

            self.db.save_skrap(page)
            pages_created += 1

        return pages_created

    def sort_articles_by_date(self, article_ids, reverse=False):
        """Sort article IDs by their publication date."""
        articles_with_dates = []

        for article_id in article_ids:
            article = self.db.find_skrap_by_id(article_id)
            if article and 'date' in article.meta:
                articles_with_dates.append((article.meta['date'], article_id))

        articles_with_dates.sort(reverse=reverse)
        return [aid for (_, aid) in articles_with_dates]
