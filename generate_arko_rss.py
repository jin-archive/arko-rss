import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import re

url = "https://www.arko.or.kr/board/list/4054"
base_url = "https://www.arko.or.kr"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=15)
response.raise_for_status()
soup = BeautifulSoup(response.text, 'html.parser')

fg = FeedGenerator()
fg.id(url)
fg.title('한국문화예술위원회 채용모집 RSS')
fg.author({'name': '한국문화예술위원회'})
fg.link(href=url, rel='alternate')
fg.description('한국문화예술위원회의 최신 채용 공고를 제공합니다.')
fg.language('ko')

# 게시판 행(tr) 탐색
rows = soup.find_all('tr')

for row in rows:
    link_element = row.find('a')
    if not link_element:
        continue

    # 제목 추출 및 정제
    title = link_element.get_text(separator=' ', strip=True)
    if not title or title == '제목': 
        continue

    # 링크 추출
    href = link_element.get('href', '')
    if href.startswith('/'):
        link = base_url + href
    else:
        # javascript 이동인 경우 대비 임시 링크 부여
        link = f"{url}#{hash(title)}" if 'javascript' in href or href == '#' else href

    # 날짜 추출 (형식: 2026.03.20)
    # 채용게시판은 마감일과 등록일 2개가 있으므로, 뒤에 있는 '등록일'을 기준으로 잡습니다.
    date_str = ""
    dates = re.findall(r'20\d{2}\.\d{2}\.\d{2}', row.get_text())
    if dates:
        date_str = dates[-1] # 발견된 날짜 중 가장 마지막 것(등록일) 선택

    fe = fg.add_entry(order='append')
    fe.id(link)
    fe.title(title)
    fe.link(href=link)
    
    if date_str:
        try:
            dt = datetime.strptime(date_str, '%Y.%m.%d')
            kst = pytz.timezone('Asia/Seoul')
            dt = kst.localize(dt)
            fe.pubDate(dt)
        except ValueError:
            pass

xml_filename = 'arko_rss.xml'
fg.rss_file(xml_filename)
print(f"생성 완료: {xml_filename}")
