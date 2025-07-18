from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import time
import os
import traceback
from dotenv import load_dotenv
import pandas as pd
from deep_translator import GoogleTranslator
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt

# === Inisialisasi ===
load_dotenv()
analyzer = SentimentIntensityAnalyzer()

def translate_comment(comment):
    if not comment:
        return "No Comment"
    try:
        translated_text = GoogleTranslator(source='auto', target='en').translate(comment)
        print(f"Translated: {translated_text}")
        return translated_text
    except Exception as e:
        print(f"Error translating: {comment} ({e})")
        return comment

# === Login Instagram ===
driver = webdriver.Chrome()
driver.get("https://www.instagram.com/accounts/login/")
time.sleep(3)

username = os.getenv('IG_USERNAME')
password = os.getenv('IG_PASSWORD')
driver.find_element(By.NAME, "username").send_keys(username)
driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
time.sleep(6)

# === Kunjungi Halaman Hashtag ===
hashtag = "diesnatalis60uajy"
driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
time.sleep(7)

# === Ambil Link Postingan ===
post_links = set()
for _ in range(1):  # Ubah range sesuai jumlah scroll
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(6)
    posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
    for post in posts:
        post_links.add(post.get_attribute("href"))

print(f"Total post collected: {len(post_links)}")

# === Ambil Komentar Setiap Post ===
comments_data = []

for link in post_links:
    driver.get(link)
    time.sleep(6)

    # === Ambil username dengan berbagai pendekatan ===
    post_username = "Unknown"
    try:
        url_parts = link.split('/')
        if len(url_parts) > 3:
            potential_username = url_parts[3]
            if potential_username and potential_username not in ['p', 'reel', 'tv']:
                post_username = potential_username
                print(f"Username from URL: {post_username}")
    except:
        pass

    if post_username == "Unknown":
        username_selectors = [
            "//header//a[contains(@href, '/') and not(contains(@href, '/p/')) and not(contains(@href, '/reel/'))]",
            "//article//header//a[not(contains(@href, '/p/')) and not(contains(@href, '/reel/'))]",
            "//a[contains(@role, 'link') and contains(@href, '/') and not(contains(@href, '/p/')) and not(contains(@href, '/reel/')) and not(contains(@href, '/explore/'))]"
        ]
        for selector in username_selectors:
            try:
                username_elements = driver.find_elements(By.XPATH, selector)
                for elem in username_elements:
                    href = elem.get_attribute("href")
                    if href:
                        href_parts = href.rstrip('/').split('/')
                        if len(href_parts) > 3:
                            potential_username = href_parts[3]
                            if potential_username and potential_username not in ['p', 'reel', 'tv', 'explore', 'accounts', 'stories']:
                                post_username = potential_username
                                print(f"Username from href: {post_username}")
                                break

                    text = elem.text.strip()
                    if text and 1 < len(text) < 50 and 'follow' not in text.lower():
                        post_username = text
                        print(f"Username from text: {post_username}")
                        break
                if post_username != "Unknown":
                    break
            except Exception as e:
                print(f"Selector error: {selector} - {e}")

    # === Scroll dan ambil komentar ===
    try:
        scroll_div = driver.find_element(By.CLASS_NAME, 'x5yr21d.xw2csxc.x1odjw0f.x1n2onr6')
        last_height = driver.execute_script("return arguments[0].scrollHeight", scroll_div)

        while True:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
            time.sleep(2)
            new_height = driver.execute_script("return arguments[0].scrollHeight", scroll_div)
            if new_height == last_height:
                break
            last_height = new_height

        comments = driver.find_elements(By.XPATH, "(//span[@class='x1lliihq x1plvlek xryxfnj x1n2onr6 "
                                                   "x1ji0vk5 x18bv5gf x193iq5w xeuugli x1fj9vlw x13faqbe "
                                                   "x1vvkbs x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty "
                                                   "x1943h6x x1i0vuye xvs91rp xo1l8bm x5n08af x10wh9bi "
                                                   "xpm28yp x8viiok x1o7cslx'])")

        for comment in comments:
            text = comment.text.strip()
            if not text or text.lower().endswith("likes") or len(text) < 2:
                continue

            translated = translate_comment(text)
            comments_data.append({
                "username": post_username,
                "post_url": link,
                "comment": text,
                "translated_comment": translated
            })

    except Exception as e:
        print(f"Error on post {link}: {e}")
        traceback.print_exc()

driver.quit()

# === Simpan Data Awal ===
df = pd.DataFrame(comments_data)
if df.empty:
    print("❌ Tidak ada komentar yang berhasil dikumpulkan.")
    exit()

# === Analisis Sentimen ===
def get_sentiment_scores(text):
    return analyzer.polarity_scores(str(text))

scores = df['translated_comment'].apply(get_sentiment_scores)
scores_df = pd.DataFrame(list(scores))
df = pd.concat([df, scores_df], axis=1)

def classify_sentiment(comp):
    if comp >= 0.05:
        return 'Positive'
    elif comp <= -0.05:
        return 'Negative'
    else:
        return 'Neutral'

df['sentiment'] = df['compound'].apply(classify_sentiment)

# === Statistik Sentimen ===
sentiment_summary = df.groupby('sentiment').agg(
    jumlah_komentar=('sentiment', 'count'),
    rata_rata_compound=('compound', 'mean')
)

# Lengkapi kategori yang tidak muncul
for cat in ['Positive', 'Neutral', 'Negative']:
    if cat not in sentiment_summary.index:
        sentiment_summary.loc[cat] = {'jumlah_komentar': 0, 'rata_rata_compound': 0.0}

sentiment_summary = sentiment_summary.loc[['Positive', 'Neutral', 'Negative']]

# === Gabungkan Statistik ke File CSV ===
# Simpan komentar + analisis
df.to_csv("translated_comments_with_sentiment.csv", index=False, sep=';', encoding='utf-8-sig')

# Tambahkan statistik ke file yang sama (tanpa header, dengan baris kosong pemisah)
with open("translated_comments_with_sentiment.csv", "a", encoding='utf-8-sig') as f:
    f.write('\n\nSentiment Statistics Summary\n')
    sentiment_summary.to_csv(f, sep=';', encoding='utf-8-sig')

print("✅ File lengkap disimpan dengan statistik: translated_comments_with_sentiment.csv")


# === Definisi warna berdasarkan kategori sentimen ===
colors = {
    'Positive': '#4CAF50',  # Hijau
    'Neutral': '#FFC107',   # Kuning
    'Negative': '#F44336'   # Merah
}

# Buat urutan kategori tetap (meski 0)
kategori = ['Positive', 'Neutral', 'Negative']
statistik = df['sentiment'].value_counts().reindex(kategori, fill_value=0)

jumlah_komentar = statistik.values.tolist()
label = statistik.index.tolist()
warna = [colors.get(k, '#999999') for k in label]

# Pie chart dengan jumlah komentar dan persentase
plt.figure(figsize=(6, 6))
wedges, texts, autotexts = plt.pie(
    jumlah_komentar,
    labels=label,
    colors=warna,
    startangle=140,
    autopct=lambda pct: (
        f"{pct:.1f}%\n({int(round(pct/100. * sum(jumlah_komentar)))} komen)"
        if pct > 0 else "0%"
    ),
    wedgeprops={'edgecolor': 'black'},
    normalize=True,  # agar persentase tetap muncul meskipun total = 0
    textprops={'fontsize': 10}
)

plt.title("Distribusi Sentimen Komentar", fontsize=14)
plt.tight_layout()
plt.show()

# === BAR CHART: Rata-rata compound per sentimen ===
plt.figure(figsize=(8, 5))
bars = plt.bar(
    sentiment_summary.index,
    sentiment_summary['rata_rata_compound'],
    color=[colors.get(s, '#999999') for s in sentiment_summary.index]
)

plt.title('Rata-rata Skor Compound per Sentimen')
plt.ylabel('Compound Score')
plt.ylim(-1, 1)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Tambahkan label nilai di atas bar
for bar in bars:
    yval = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        yval + 0.03 if yval >= 0 else yval - 0.08,
        f"{yval:.2f}",
        ha='center',
        va='bottom' if yval >= 0 else 'top',
        fontsize=10
    )

plt.xticks(rotation=0)
plt.tight_layout()
plt.show()
