"""
6613 turkanime.tv slug'ı arasında tranimaci animelerinin karsıliklarını bul.
Hem slug kelime kesisimi hem de doğrudan HTTP test.
"""
import json, sqlite3, re, urllib.request, urllib.error, time

DB = '/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db'
SLUGS_FILE = '/mnt/c/Kuroshin/scripts/turkanime_slugs.json'
TURKANIME_BASE = 'https://www.turkanime.tv/video'
HEADERS = {'User-Agent': 'Mozilla/5.0 Chrome/120.0', 'Accept': 'text/html,*/*'}

with open(SLUGS_FILE) as f:
    turk_slugs = set(json.load(f))

# El ile olusturulan mapping: tranimaci_slug -> turkanime_slug (olasi adaylar)
# Japanca isim -> turkanime slug (genellikle Japanca)
MANUAL_CANDIDATES = {
    # tranimaci slug                       -> [turkanime slug candidates]
    'spy-x-family': ['spy-x-family'],                                    # tam eslesme
    'tate-no-yuusha-no-nariagari': ['tate-no-yuusha-no-nariagari'],     # tam eslesme
    'high-school-dxd-new': ['high-school-dxd-new'],                     # tam eslesme
    'code-geass-lelouch-of-the-rebellion-r2': ['code-geass-r2', 'code-geass-hangyaku-no-lelouch-r2'],
    'assassination-classroom-second-season': ['ansatsu-kyoushitsu-2nd-season', 'assassination-classroom-season-2'],
    'bleach-thousand-year-blood-war': ['bleach-thousand-year-blood-war', 'bleach-sennen-kessen-hen'],
    'black-butler-book-of-murder': ['kuroshitsuji-book-of-murder'],
    'black-butler-public-school-arc': ['kuroshitsuji-public-school-arc'],
    'dan-da-dan-season-2': ['dandadan-season-2', 'dan-da-dan-2'],
    'classroom-of-the-elite-season-2': ['youkoso-jitsuryoku-shijou-shugi-no-kyoushitsu-e-2nd-season', 'classroom-of-the-elite-2'],
    'kaguya-sama-love-is-war': ['kaguya-sama-wa-kokurasetai-ultra-romantic', 'kaguya-sama-wa-kokurasetai-tensai-tachi-no-renai-zunousen'],
    'kakegurui-xx': ['kakegurui-xx'],
    'bofuri-i-don-t-want-to-get-hurt-so-i-ll-max-out-my-defense-season-2': ['itai-no-wa-iya-nanode-bougyoryoku-ni-kyokufuri-shitai-to-omoimasu-2', 'bofuri-season-2'],
    'love-chunibyo-other-delusions-glimmering-explosive-festival-slapstick-noel': ['chuunibyou-demo-koi-ga-shitai-ren', 'chuunibyou-demo-koi-ga-shitai-take-on-me'],
    'isekai-cheat-magician-magicians-and-the-starry-night-festival': ['isekai-cheat-magician'],
    'is-it-wrong-to-try-to-pick-up-girls-in-a-dungeon-ii': ['dungeon-ni-deai-wo-motomeru-no-wa-machigatteiru-darou-ka-ii', 'danmachi-ii'],
    'hell-s-paradise-season-2': ['jigokuraku-2nd-season', 'hell-s-paradise-jigokuraku-season-2'],
    'kabaneri-of-the-iron-fortress-the-battle-of-unato': ['kabaneri-of-the-iron-fortress-the-battle-of-unato', 'koutetsujou-no-kabaneri-unato-kessen'],
    'blood-blockade-battlefront-beyond': ['kekkai-sensen-beyond'],
    'konosuba-god-s-blessing-on-this-wonderful-world-2': ['kono-subarashii-sekai-ni-shukufuku-wo-3', 'konosuba-season-3'],
    'komi-can-t-communicate-part-2': ['komi-san-wa-komyushou-desu-2nd-season', 'komi-san-part-2'],
    'by-the-grace-of-the-gods-2': ['kami-tachi-ni-hirowareta-otoko-2nd-season', 'by-the-grace-of-the-gods-2'],
    'the-daily-life-of-the-immortal-king-season-2': ['xian-wang-de-richang-shenghuo-2', 'the-daily-life-of-the-immortal-king-2'],
    'high-school-of-the-dead-drifters-of-the-dead': ['high-school-of-the-dead-drifters-of-the-dead', 'highschool-of-the-dead-ova'],
    'as-a-reincarnated-aristocrat-i-ll-use-my-appraisal-skill-to-rise-in-the-world-season-2': ['tensei-kizoku-no-isekai-boukenroku-2', 'reincarnated-aristocrat-season-2'],
    'ishura-season-2': ['ishura-2nd-season', 'ishura-season-2'],
    'another-the-other': ['another'],
    'jojo-s-bizarre-adventure-2000': ['jojo-no-kimyou-na-bouken-2000'],
    'quanzhi-gaoshou-specials': ['quanzhi-gaoshou-specials', 'the-king-s-avatar-specials'],
    'the-king-s-avatar-for-the-glory': ['the-king-s-avatar-for-the-glory'],
    'let-this-grieving-soul-retire-cour-2': ['rougo-ni-sonaete-isekai-de-8-manmai-no-kinka-wo-tamemasu-cour-2', 'let-this-grieving-soul-retire-2nd-cour'],
    'reborn-as-a-vending-machine-i-now-wander-the-dungeon-season-2': ['jidou-hanbaiki-ni-umarekawatta-ore-wa-meikyuu-wo-samayou-season-2'],
    # Miyazaki filmleri
    'my-neighbor-totoro-tonari-no-totoro': ['tonari-no-totoro', 'my-neighbor-totoro'],
    'spirited-away-sen-to-chihiro-no-kamikakushi': ['spirited-away', 'sen-to-chihiro-no-kamikakushi'],
    'howls-moving-castle-yuruyen-sato': ['howl-s-moving-castle', 'hauru-no-ugoku-shiro'],
    '5-centimeters': ['5-centimeters-per-second', 'byousoku-5-centimeter'],
    # Chin anime
    'long-zu-dragon-raja': ['long-zu-dragon-raja', 'long-zu'],
    'immortal-king': ['xian-wang-de-richang-shenghuo', 'the-daily-life-of-the-immortal-king'],
    'dark-healer': ['dark-healer'],
    'assassin-isekai': ['assassin-isekai'],
    'assessment-assassin': ['assessment-assassin'],
    'punishment-hero': ['punishment-hero'],
    'seventh-prince': ['seventh-prince'],
    'rookie-older-adventurer': ['rookie-older-adventurer'],
    'teach-you-a-lesson': ['teach-you-a-lesson'],
    'isekai-one-turn-kill-neesan': ['isekai-one-turn-kill-neesan', 'isekai-de-neesan-to-issho-ni-level-up'],
    'lv2-kara-cheat-datta-motoyuusha-kouho-no-mattari-isekai-life': ['lv2-kara-cheat-datta-motoyuusha-kouho-no-mattari-isekai-life'],
    'isekai-de-cheat-skill-wo-te-ni-shita-ore-wa-genjitsu-sekai-wo-mo-musou-suru-level-up-wa-jinsei-wo-mo-kaeta': [
        'isekai-de-cheat-skill-wo-te-ni-shita-ore-wa-genjitsu-sekai-wo-mo-musou-suru-level-up-wa-jinsei-wo-kaeta'
    ],
    'bakis-path-2-kisim': ['baki-hanma-2'],
}

def head_ok(url, timeout=8):
    req = urllib.request.Request(url, headers=HEADERS, method='HEAD')
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False

# Sitemap'te bulunanlar (hızlı kontrol)
sitemap_eslesti = {}  # tranimaci_slug -> turkanime_slug
http_eslesti = {}
bulunamadi = []

print('Sitemap kontrolü (hizli):')
for tslug, candidates in MANUAL_CANDIDATES.items():
    found = None
    for cand in candidates:
        if cand in turk_slugs:
            found = cand
            break
    if found:
        sitemap_eslesti[tslug] = found
        print(f'  SITEMAP ✅ {tslug[:50]:50} -> {found}')
    else:
        bulunamadi.append((tslug, candidates))

print(f'\nSitemap eslesti: {len(sitemap_eslesti)}')
print(f'HTTP test gerekli: {len(bulunamadi)}')

print('\nHTTP HEAD testi (yavaş):')
for tslug, candidates in bulunamadi:
    found = None
    for cand in candidates:
        url = f'{TURKANIME_BASE}/{cand}-1-bolum'
        if head_ok(url):
            found = cand
            break
        time.sleep(0.3)
    if found:
        http_eslesti[tslug] = found
        print(f'  HTTP ✅ {tslug[:50]:50} -> {found}')
    else:
        print(f'  HTTP ❌ {tslug[:50]:50} (denendi: {candidates})')

all_found = {**sitemap_eslesti, **http_eslesti}
print(f'\n{"="*80}')
print(f'TOPLAM BULUNAN: {len(all_found)} / {len(MANUAL_CANDIDATES)}')

# JSON kaydet
out = '/mnt/c/Kuroshin/scripts/tranimaci_to_turkanime_map.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(all_found, f, ensure_ascii=False, indent=2)
print(f'Kaydedildi: {out}')
