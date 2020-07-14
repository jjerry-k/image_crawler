# %%
from bs4 import BeautifulSoup
import urllib3
from pprint import pprint

# %%
http = urllib3.PoolManager()
url = 'https://www.google.com/search?q=cat&sxsrf=ALeKk00gYYCaB11TlQGVpvCbViRwsBIwIQ:1594734972464&source=lnms&tbm=isch&sa=X&ved=2ahUKEwjtoa3c8szqAhWoGKYKHfxMDX4Q_AUoAXoECBcQAw&biw=1726&bih=1267'

# %%
response = http.request('GET', url)

# print(source)
# %%
soup = BeautifulSoup(response.data, features="html.parser")

img = soup.find("img")  # 이미지 태그
# img_src = img.get("src") # 이미지 경로
# img_url = base_url + img_src # 다운로드를 위해 base_url과 합침
# img_name = img_src.replace("/", "") # 이미지 src에서 / 없애기
# print(soup)
print(img) 

img = soup.find_all("img")
pprint(img)
print(len(img))