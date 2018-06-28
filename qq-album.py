import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
import os
import time
import shutil
import threading

os.chdir(os.path.dirname(os.path.abspath(__file__)))

QQ_ID = '你的QQ号'
QQ_PWD = '你的QQ密码'
CRAWL_ID = '需要爬取相册的QQ号'

IGNORE_ALBUMS = [] # 如果 CRAWL_ALBUMS 非空，则忽略
CRAWL_ALBUMS = [] # 若空，则爬取除了 IGNORE_ALBUMS 里的所有相册

MAX_THREADS = 30 # For downloading images

try:
    os.mkdir(CRAWL_ID)
except FileExistsError:
    pass
finally:
    os.chdir(CRAWL_ID)

def get_url(url):
    try:
        driver.get(url)
    except TimeoutException:
        pass
    except Exception as e:
        return e

def click_element(element):
    try:
        element.click()
    except TimeoutException:
        pass
    except Exception as e:
        return e

def login():
    driver.get('http://i.qq.com/')
    driver.switch_to_frame('login_frame')
    driver.find_element_by_css_selector('#switcher_plogin').click()
    usrInp = driver.find_element_by_css_selector('#u')
    pwdInp = driver.find_element_by_css_selector('#p')
    usrInp.clear()
    pwdInp.clear()
    usrInp.send_keys(QQ_ID)
    pwdInp.send_keys(QQ_PWD)
    driver.find_element_by_css_selector('#login_button').click()
    # while driver.title == 'QQ空间-分享生活，留住感动':
    #     time.sleep(0.5)
    usrTitle = '[http://{}.qzone.qq.com]'.format(QQ_ID)
    try:
        WebDriverWait(driver, 10).until(EC.title_contains(usrTitle))
    except TimeoutException:
        print('Login timeout!')
        exit()

def get_albums():
    url = 'https://user.qzone.qq.com/{}/4'.format(CRAWL_ID)
    get_url(url)
    driver.switch_to_frame('app_canvas_frame')
    albums = []
    for album in driver.find_elements_by_css_selector('.js-album-list-ul > li'):
        name = album.find_element_by_css_selector('.album-tit > a')
        albums.append(name.text)
    return albums

def get_photos(album):
    print('Crawling "{}"...'.format(album))
    url = 'https://user.qzone.qq.com/{}/4'.format(CRAWL_ID)
    get_url(url)
    driver.switch_to_frame('app_canvas_frame')
    for i in driver.find_elements_by_css_selector('.js-album-list-ul > li'):
        link = i.find_element_by_css_selector('.album-tit > a')
        if link.text == album:
            click_element(link)
            break
    else: # 无法找到指定相册，返回空列表
        print('Unable to find album "{}"'.format(album))
        return []
    imgs = []
    while True:
        imgs += get_page_photos()
        try:
            driver.find_element_by_css_selector('a#pager_next_1').click()
        except NoSuchElementException:
            break
    return imgs

def get_page_photos():
    driver.switch_to_default_content() # 切换回主框架，以便滚动
    driver.execute_script('window.scrollTo(0, 250)');
    for i in range(5):
        time.sleep(0.8)
        driver.execute_script('window.scrollBy(0, 450)');
    # time.sleep(0.8)
    driver.switch_to_frame('app_canvas_frame') # 切换回相册框架，以便定位图片
    imgs = []
    for img in driver.find_elements_by_css_selector('.j-pl-photoitem > div'):
        name = img.find_element_by_css_selector('.item-tit > span').text
        src = img.find_element_by_css_selector('.j-pl-photoitem-img').get_attribute('src') or \
              img.find_element_by_css_selector('.j-pl-photoitem-img').get_attribute('data-src')
        imgs.append((src, name))
    return imgs

def download_img(src, name):
    if not name.endswith('.jpg'):
        name += '.jpg'
    try:
        req = requests.get(src, stream=True)
    except Exception:
        print('[ERROR] {} ({})'.format(src, name))
        return
    if req.status_code == 200:
        with open(name, 'wb') as file:
            req.raw.decode_content = True
            shutil.copyfileobj(req.raw, file)
    else:
        print('[{}] {} ({})'.format(req.status_code, src, name))

def threading_download(imgs, albumName):
    print('Downloading "{}"...'.format(albumName))
    threadPool = []
    counter = 1
    for src, name in imgs:
        if src == None:
            print(name)
            continue
        src = src.replace('/m/', '/b/').replace('null', '').split('&')[0]
        imgName = '{0}/{0} - {1}.jpg'.format(albumName, counter)
        counter += 1
        t = threading.Thread(target=download_img, args=(src, imgName))
        threadPool.append(t)
        if len(threadPool) == MAX_THREADS:
            for thread in threadPool:
                thread.start()
            thread.join()
            threadPool = []
    if threadPool:
        for thread in threadPool:
            thread.start()
        thread.join()

driver = webdriver.Chrome()
driver.set_window_size(1440, 900)
driver.set_window_position(0, 0)
driver.implicitly_wait(10)
driver.set_page_load_timeout(4)

login()
albums = get_albums()
if CRAWL_ALBUMS:
    for album in CRAWL_ALBUMS:
        if album not in albums:
            continue
        os.mkdir(album)
        imgs = get_photos(album)
        threading_download(imgs, album)
else:
    for album in albums:
        if album in IGNORE_ALBUMS:
            continue
        os.mkdir(album)
        imgs = get_photos(album)
        threading_download(imgs, album)

driver.quit()
print('Done')
