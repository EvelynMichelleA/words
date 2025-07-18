import datetime
from collections import Counter
import matplotlib.pyplot as plt
import pandas as pd
import requests
from bs4 import BeautifulSoup
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

base = datetime.date(2023, 1, 1)
date_list = [base + datetime.timedelta(days=x) for x in range(1)]
for date in date_list:
    url = 'https://indeks.kompas.com/?site=all&date=' + date.strftime("%Y-%m-%d")
    req = requests.get(url)
    soup = BeautifulSoup(req.text, 'lxml')
    a = soup.find_all('a', {'class': 'article-link'})
    kumpulan_link = []
    kumpulan_paragraf = []
for link in a:
    kumpulan_link.append(link['href'])
for link in kumpulan_link:
    halaman = requests.get(link)
    soup_baru = BeautifulSoup(halaman.text, 'lxml')
    paragraf = soup_baru.find_all('p')
    for kalimat in paragraf:
        kumpulan_paragraf.append(kalimat.text)
with open('paragraf.txt', 'w', encoding="utf-8") as f:
    for paragraf in kumpulan_paragraf:
        f.writelines(paragraf + '\\n')
words = ' '.join(kumpulan_paragraf).split()
factory = StopWordRemoverFactory()
stop_words = factory.get_stop_words() + [
    'juga:', 'baca', 'copyright', '2008', '-', '2023', 'pt.', 'kompas', 'cyber',
    'media', '(kompas', 'gramedia', 'digital', 'group).', 'all', 'rights', 'reserved.',
    'segera', 'lengkapi', 'data', 'dirimu', 'untuk', 'ikutan', 'program', '#jernihberkomentar.', 'Kompas.com'
]

filtered_words = [word for word in words if word.lower() not in stop_words]
filtered_word_freq = Counter(filtered_words)
filtered_word_freq_df = pd.DataFrame(list(filtered_word_freq.items()), columns=['word', 'frequency'])
filtered_word_freq_df = filtered_word_freq_df.sort_values(by='frequency', ascending=False)

top_filtered_words = filtered_word_freq_df.head(10)
plt.figure(figsize=(12, 6))
plt.bar(top_filtered_words['word'], top_filtered_words['frequency'])
plt.xlabel('Kata')
plt.ylabel('Frekuensi')
plt.title('10 Kata Paling Sering Muncul setelah Penghilangan dan Penambahan Stop Words dalam Artikel')
plt.show()