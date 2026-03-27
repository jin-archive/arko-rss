import time
import re
import hashlib
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

url = "https://artsarchive.arko.or.kr/guide/notice"
base_url = "https://artsarchive.arko.or.kr"

print("크롬 브라우저를 시작합니다...")
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

print("웹페이지에 접속하여 자바스크립트 렌더링을 기다립니다...")
driver.get(url)
time.sleep(5)  # 데이터가 화면에 그려질 때까지 5초 대기

html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')
driver.quit()

# RSS 피드 초기화
fg = FeedGenerator()
fg.id(url)
fg.title('아르코예술기록원 공지사항 RSS')
fg.author({'name': '아르코예술기록원'})
fg.link(href=url, rel='alternate')
fg.description('아르코예술기록원의 최신 공지사항을 제공합니다.')
fg.language('ko')

# <a> 태그를 모두 찾아서 게시글 형태인 것만 걸러내기
links = soup.find_all('a')
added_links = set()
items_found = 0

for a in links:
    href = a.get('href', '')
    title = a.get_text(separator=' ', strip=True)
    
    # 너무 짧은 링크나 메뉴 링크는 건너뜀
    if not href or len(title) < 5 or title in ['이전 페이지', '다음 페이지', '본문 바로가기', '주메뉴 바로가기']:
        continue
    if href == '#' and not a.get('onclick'):
        continue

    # 해당 링크를 감싸고 있는 부모 태그(보통 행 역할을 함)를 찾아 날짜를 추출
    parent = a.find_parent(['tr', 'li', 'div', 'ul'])
    date_str = ""
    if parent:
        # 2026-02-19 형태의 텍스트 찾기
        date_match = re.search(r'20\d{2}-\d{2}-\d{2}', parent.get_text())
        if date_match:
            date_str = date_match.group()
            
    # 게시글 목록이라면 반드시 날짜가 있으므로, 날짜가 없는 링크는 무시
    if not date_str:
        continue
        
    # 제목 앞의 '공지' 뱃지 텍스트 깔끔하게 지우기
    title = re.sub(r'^(공지|안내)\s*', '', title).strip()

    # 링크 조합
    if href.startswith('/'):
        link = base_url + href
    elif 'javascript' in href or href == '#':
        onclick = a.get('onclick') or ''
        nums = re.findall(r"\d+", onclick)
        link = f"{url}?id={nums[0]}" if nums else f"{url}#{hashlib.md5(title.encode()).hexdigest()[:8]}"
    else:
        link = href

    # 중복 제거
    if link in added_links:
        continue
    added_links.add(link)

    # 항목 추가 (들어오는 순서대로 차곡차곡)
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
            
    items_found += 1

print(f"탐색 완료: 총 {items_found}개의 공지사항을 찾았습니다.")
fg.rss_file('artsarchive_rss.xml')
