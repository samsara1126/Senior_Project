from newspaper import Article, Config
import requests

def scrape_article_data(url: str):

    config = Config()
    config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    config.request_timeout = 15 
    try:
        article = Article(url, language='en')
        article.download()
        article.parse()

        text = article.text
        top_image_url = article.top_image

        image_bytes = None
        # 메인 이미지가 존재하면 다운로드하여 Bytes로 변환
        if top_image_url:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(top_image_url, headers=headers)
            if response.status_code == 200:
                image_bytes = response.content

        return {
            "title": article.title,
            "text": text,
            "image_url": top_image_url,
            "image_bytes": image_bytes
        }
    except Exception as e:
        return {"error": str(e)}