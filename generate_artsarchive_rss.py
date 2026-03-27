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
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

print("웹페이지에 접속하여 자바스크립트 렌더링을 기다립니다...")
driver.get(url)
time.sleep(8)

html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')
driver.quit()

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
    
    # 1. 명백한 쓰레기 데이터 1차 필터링
    if not title or len(title) < 5:
        continue
    if href.startswith(('tel:', 'mailto:')):
        continue
        
    junk_words = ['처음', '마지막', '이전', '다음', '본문 바로가기', '주메뉴 바로가기', '누리집보기', '대표전화', '기록원 소개', '한국문화예술위원회']
    if any(junk in title for junk in junk_words):
        continue

    # 2. 좁은 범위 내에서 날짜 찾기 (전체 페이지 탐색 방지)
    date_str = ""
    
    # 가장 확실한 표 형태(tr, li)인 경우 우선 확인
    row_container = a.find_parent(['tr', 'li'])
    
    # 표 형태가 아닌 div 구조라면, 텍스트 길이가 300자 미만인 부모까지만 탐색
    if not row_container:
        curr = a.parent
        for _ in range(4):
            if not curr or curr.name in ['body', 'html']:
                break
            # 부모 텍스트가 300자 미만일 때만 '게시판의 한 줄(Row)'로 인정
            if len(curr.get_text(strip=True)) < 300:
                if re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}', curr.get_text()):
                    row_container = curr
                    break
            curr = curr.parent

    # 유효한 컨테이너(한 줄)를 찾았다면 그 안에서 날짜 추출
    if row_container:
        date_match = re.search(r'(20\d{2}[-./]\d{2}[-./]\d{2})', row_container.get_text())
        if date_match:
            date_str = date_match.group(1).replace('.', '-').replace('/', '-')

    # 좁은 범위 내에 날짜가 없다면 게시글이 아님
    if not date_str:
        continue

    # 3. 데이터 정제 및 고유 링크 생성
    title = re.sub(r'^(공지|안내)\s*', '', title).strip()

    if href.startswith('/'):
        link = base_url + href
    elif 'javascript' in href or href == '#' or not href:
        onclick = a.get('onclick') or ''
        nums = re.findall(r"\d+", onclick)
        link = f"{url}?id={nums[0]}" if nums else f"{url}#{hashlib.md5(title.encode()).hexdigest()[:8]}"
    else:
        link = href

    if link in added_links:
        continue
    added_links.add(link)

    # 4. RSS 추가
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
