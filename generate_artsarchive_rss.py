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
# 모바일 모드로 인식되어 날짜 열이 숨겨지는 것을 방지하기 위해 PC 해상도 고정
chrome_options.add_argument('--window-size=1920,1080') 
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

print("웹페이지에 접속하여 자바스크립트 렌더링을 기다립니다...")
driver.get(url)
time.sleep(8)  # 로딩이 느릴 수 있으므로 넉넉하게 8초 대기

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

links = soup.find_all('a')
added_links = set()
items_found = 0

for a in links:
    href = a.get('href', '')
    title = a.get_text(separator=' ', strip=True)
    
    # 의미 없는 링크 패스
    if not href or len(title) < 5 or title in ['이전 페이지', '다음 페이지', '본문 바로가기', '주메뉴 바로가기']:
        continue

    # -----------------------------------
    # 핵심 개선: 날짜 찾기 로직 (5단계 상위 부모까지 넓게 탐색)
    # -----------------------------------
    date_str = ""
    curr_parent = a.parent
    for _ in range(5): 
        if not curr_parent:
            break
        # 현재 그룹 안에서 2026-02-19 또는 2026.02.19 형태의 날짜 찾기
        date_match = re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}', curr_parent.get_text(separator=' '))
        if date_match:
            date_str = date_match.group().replace('.', '-').replace('/', '-')
            break
        curr_parent = curr_parent.parent # 못 찾으면 한 단계 더 큰 컨테이너로 이동
            
    # 아무리 부모를 뒤져도 날짜가 없으면 게시판 목록이 아니므로 패스
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

    # 항목 추가
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
