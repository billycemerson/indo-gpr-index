from bs4 import BeautifulSoup

class AntaraParser:
    @staticmethod
    def parse_list_page(html_content):
        """Extracts article metadata from a list page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.select('div.row')
        
        articles = []
        for row in rows:
            title_tag = row.select_one('h2.post_title a')
            date_tag = row.select_one('span.text-secondary')
            
            if not title_tag:
                continue
                
            articles.append({
                'title': title_tag.get_text(strip=True),
                'link': title_tag.get('href', ''),
                'date_text': date_tag.get_text(strip=True) if date_tag else ""
            })
        return articles