import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import re

url = "https://artsarchive.arko.or.kr/guide/notice"
base_url = "https://artsarchive.arko.or.kr"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=15)
response.raise_for_status()
soup = BeautifulSoup(response.text, 'html.parser')

fg = FeedGenerator()
fg.id(url)
fg.title('아르코예술기록원 공지사항 RSS')
fg.author({'name': '아르코예술기록원'})
fg.link(href=url, rel='alternate')
fg.description('아르코예술기록원의 최신 공지사항을 제공합니다.')
fg.language('ko')

rows = soup.find_all('tr')

for row in rows:
    link_element = row.find('a')
    if not link_element:
        continue

    title = link_element.get_text(separator=' ', strip=True)
    if not title or title == '제목':
        continue
        
    # '공지' 같은 뱃지 텍스트 제거
    title = re.sub(r'^공지\s*', '', title)

    href = link_element.get('href', '')
    if href.startswith('/'):
        link = base_url + href
    else:
        link = f"{url}#{hash(title)}" if 'javascript' in href or href == '#' else href

    # 날짜 추출 (형식: 2026-02-19)
    date_str = ""
    date_match = re.search(r'20\d{2}-\d{2}-\d{2}', row.get_text())
    if date_match:
        date_str = date_match.group()

    fe = fg.add_entry(order='append')
    fe.id(link)
    fe.title(title)
    fe.link(href=link)
    
    if date_str:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            kst = pytz.timezone('Asia/Seoul')
            dt = kst.localize(dt)
            fe.pubDate(dt)
        except ValueError:
            pass

xml_filename = 'artsarchive_rss.xml'
fg.rss_file(xml_filename)
print(f"생성 완료: {xml_filename}")
