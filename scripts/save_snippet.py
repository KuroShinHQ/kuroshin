# Let's save the user's prompt text to a file so we can parse it and merge it exactly with the existing data.
user_pasted_text = """
  {
    "title": "Hugo",
    "type": "tv-show",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Nostalji", "İnteraktif Oyun", "Telefon", "Çocukluk"]
  },
  {
    "title": "Bakugan Battle Brawlers",
    "type": "anime",
    "status": "completed",
    "personal_rating": "9.5/10",
    "tags": ["Strateji", "Kart Oyunu", "Canavarlar", "Isekai", "Elementler"]
  },
  {
    "title": "Beyblade",
    "type": "anime",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Kutsal Canavarlar", "Turnuva", "Çocukluk"]
  },
  {
    "title": "Dexter's Laboratory",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Bilim", "Laboratuvar", "Komedi", "Cartoon Network"]
  },
  {
    "title": "Totally Spies! (Ajanlar)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Casusluk", "Ajan", "Aksiyon", "Jetix"]
  },
  {
    "title": "Ed, Edd n Eddy",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Mahalle", "Komedi", "Absürt", "Cartoon Network"]
  },
  {
    "title": "Megas XLR",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Mecha", "Dev Robot", "Modifiye", "Efsane"]
  },
  {
    "title": "Ben 10 (Klasik, Alien Force, Ultimate Alien, Omniverse)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "9.5/10",
    "tags": ["Omnitrix", "Uzaylılar", "Aksiyon", "Cartoon Network", "Tüm Jenerasyonlar"]
  },
  {
    "title": "Generator Rex",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Nanoteknoloji", "Mutasyon", "Aksiyon", "Sci-Fi"]
  },
  {
    "title": "Adventure Time",
    "type": "cartoon",
    "status": "watching",
    "personal_rating": "10/10",
    "tags": ["Post-Apokaliptik", "Fantezi", "Macera", "Yaşayan Sistem"]
  },
  {
    "title": "Space Goofs (Uzay Çılgınları)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Uzaylılar", "Dünya", "Komedi"]
  },
  {
    "title": "Max Steel",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Nano Suit", "Zırh", "Aksiyon", "Sci-Fi"]
  },
  {
    "title": "Teletubbies",
    "type": "tv-show",
    "status": "dropped",
    "personal_rating": "3.0/10",
    "tags": ["Çocuk Programı", "Sevilmedi"]
  },
  {
    "title": "Regular Show (Sürekli Dizi)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "9.5/10",
    "tags": ["Komedi", "Absürt", "Kült", "Cartoon Network"]
  },
  {
    "title": "Samurai Jack",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Aksiyon", "Distopya", "Samuray", "Efsane"]
  },
  {
    "title": "The Amazing World of Gumball",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Komedi", "Absürt", "Aile"]
  },
  {
    "title": "The Marvelous Misadventures of Flapjack",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Karanlık Atmosfer", "Macera", "Denizcilik"]
  },
  {
    "title": "DreamWorks Dragons (Ejderha Binicileri)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Ejderhalar", "Macera", "Fantezi"]
  },
  {
    "title": "The Secret Saturdays",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Kriptidler", "Gizem", "Macera"]
  },
  {
    "title": "Total Drama Island (Drama Adası)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Yarışma", "Parodi", "Gençlik"]
  },
  {
    "title": "Green Lantern: The Animated Series",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["DC", "Uzay", "Süper Kahraman"]
  },
  {
    "title": "Justice League / Justice League Unlimited",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["DC", "Süper Kahraman", "Ekip"]
  },
  {
    "title": "Sonic X / Sonic Serileri",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Hız", "Kirpi", "Aksiyon"]
  },
  {
    "title": "Transformers Prime / Animated",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Robotlar", "Sci-Fi", "Aksiyon"]
  },
  {
    "title": "Johnny Bravo",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "7.5/10",
    "tags": ["Komedi", "Nostalji"]
  },
  {
    "title": "Star Wars: The Clone Wars",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "7.5/10",
    "tags": ["Star Wars", "Sci-Fi", "Uzay"]
  },
  {
    "title": "Teen Titans Go!",
    "type": "cartoon",
    "status": "watching",
    "personal_rating": "6.0/10",
    "tags": ["DC", "Parodi", "Eh İşte"]
  },
  {
    "title": "Ninjago: Masters of Spinjitzu",
    "type": "cartoon",
    "status": "watching",
    "personal_rating": "6.0/10",
    "tags": ["Lego", "Ninja", "Elementler", "Eh İşte"]
  },
  {
    "title": "Over the Garden Wall (Bahçe Duvarının Ötesinde)",
    "type": "cartoon",
    "status": "dropped",
    "personal_rating": "4.0/10",
    "tags": ["Gizem", "Sevilmedi"]
  },
  {
    "title": "Steven Universe",
    "type": "cartoon",
    "status": "dropped",
    "personal_rating": "3.0/10",
    "tags": ["Kristal Taşlar", "Sevilmedi"]
  },
  {
    "title": "We Bare Bears (Kafadan Ayılar)",
    "type": "cartoon",
    "status": "dropped",
    "personal_rating": "4.5/10",
    "tags": ["Komedi", "Sevilmedi"]
  },
  {
    "title": "Uncle Grandpa / Clarence",
    "type": "cartoon",
    "status": "dropped",
    "personal_rating": "3.0/10",
    "tags": ["Cartoon Network", "Sevilmedi"]
  },
  {
    "title": "Tom and Jerry / Scooby-Doo / Looney Tunes / Powerpuff Girls",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "6.5/10",
    "tags": ["Klasik Nostalji", "Eh İşte"]
  },
  {
    "title": "Kim Possible",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Casusluk", "Aksiyon", "Disney Channel", "Efsane"]
  },
  {
    "title": "Gravity Falls (Esrarengiz Kasaba)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "9.5/10",
    "tags": ["Gizem", "Doğaüstü", "Macera", "Kült"]
  },
  {
    "title": "Phineas and Ferb (Fineas ve Förb)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Mühendislik", "Zeka", "Komedi", "Yaz Tatili"]
  },
  {
    "title": "American Dragon: Jake Long (Genç Ejder)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Ejderha", "Dönüşüm", "Aksiyon", "Gizli Kimlik"]
  },
  {
    "title": "The Emperor's New School (Şaşkın İmparator'un Okulu)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Komedi", "Okul", "Mitoloji"]
  },
  {
    "title": "Aladdin (Çizgi Dizi)",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Fantezi", "Büyü", "Macera"]
  },
  {
    "title": "Mickey Mouse / Monsters At Work",
    "type": "cartoon",
    "status": "watching",
    "personal_rating": "6.0/10",
    "tags": ["Disney Klasikleri", "Eh İşte"]
  },
  {
    "title": "My Little Pony / Winnie the Pooh / Yogi Bear / Broken Karaoke",
    "type": "cartoon",
    "status": "dropped",
    "personal_rating": "3.0/10",
    "tags": ["Sevilmedi", "Çocuksu", "Müzikal"]
  },
  {
    "title": "Inception",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Bilimkurgu", "Rüya", "Zihin Çalma", "Aksiyon"]
  },
  {
    "title": "The Lord of the Rings (Yüzüklerin Efendisi Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Fantezi", "Mitoloji", "Destansı", "Başyapıt"]
  },
  {
    "title": "Batman Serisi (Kara Şövalye ve Tüm Filmler)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["DC", "Süper Kahraman", "Karanlık Atmosfer", "Aksiyon"]
  },
  {
    "title": "I Am Legend (Ben Efsaneyim)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Post-Apokaliptik", "Virüs", "Hayatta Kalma", "Zombi"]
  },
  {
    "title": "Pirates of the Caribbean (Karayip Korsanları Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Kaptan Jack Sparrow", "Korsanlar", "Macera", "Mitoloji"]
  },
  {
    "title": "Transformers Serisi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Mecha", "Robotlar", "Aksiyon", "Bilimkurgu"]
  },
  {
    "title": "Terminator Serisi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Zaman Yolculuğu", "Robotlar", "Aksiyon", "Kült"]
  },
  {
    "title": "Real Steel (Çelik Yumruk)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Robot Dövüşleri", "Aksiyon", "Dram", "Gelecek"]
  },
  {
    "title": "Pacific Rim (Pasifik Savaşı Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Jaeger", "Kaiju", "Dev Robotlar", "Aksiyon"]
  },
  {
    "title": "Ghost Rider (Hayalet Sürücü)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Marvel", "Anti-Kahraman", "Doğaüstü", "Bayıldım"]
  },
  {
    "title": "Percy Jackson Serisi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Mitoloji", "Yunan Tanrıları", "Fantastik", "Bayıldım"]
  },
  {
    "title": "Sherlock Holmes Serisi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Gizem", "Zeka", "Dedektif", "Bayıldım"]
  },
  {
    "title": "Spider-Man (Tobey Maguire Üçlemesi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "9.5/10",
    "tags": ["Nostalji", "Marvel", "Örümcek Adam", "Çocukluk"]
  },
  {
    "title": "Limitless (Film)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "9.5/10",
    "tags": ["NZT-48", "Zeka", "Güçlenme", "Kült"]
  },
  {
    "title": "Avatar",
    "type": "movie",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Sci-Fi", "Pandora", "Görsel Şölen", "Uzay"]
  },
  {
    "title": "Twilight (Alacakaranlık Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Vampirler", "Kurt Adamlar", "Fantastik"]
  },
  {
    "title": "Ice Age (Buz Devri Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Animasyon", "Nostalji", "Komedi", "Çocukluk"]
  },
  {
    "title": "Avengers / Iron Man / Thor / Captain America / Doctor Strange / Venom / Deadpool",
    "type": "movie",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Marvel Evreni", "Süper Kahramanlar", "Aksiyon"]
  },
  {
    "title": "Edge of Tomorrow (Yarının Sınırında)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Zaman Döngüsü", "Uzaylı İstilası", "Progression", "Aksiyon"]
  },
  {
    "title": "The Mummy / The Scorpion King Serisi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Mitoloji", "Antik Mısır", "Macera", "Scorpion King"]
  },
  {
    "title": "Undisputed (Yenilmez Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Dövüş", "Boyka", "Hapishane", "Aksiyon"]
  },
  {
    "title": "The Maze Runner (Labirent Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Distopya", "Kaçış", "Gizem", "Hayatta Kalma"]
  },
  {
    "title": "Planet of the Apes (Maymunlar Cehennemi Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Evrim", "Bilimkurgu", "Distopya"]
  },
  {
    "title": "3 Idiots",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Eğitim Sistemi", "Dostluk", "Komedi"]
  },
  {
    "title": "Harry Potter Serisi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Büyü", "Hogwarts", "Fantastik"]
  },
  {
    "title": "The Hobbit: An Unexpected Journey",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Orta Dünya", "Fantezi", "Macera"]
  },
  {
    "title": "The Hunger Games (Açlık Oyunları Serisi)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Distopya", "Hayatta Kalma", "Yarışma"]
  },
  {
    "title": "Fast & Furious / Ölüm Yarışı / Taşıyıcı / Tetikçi / John Wick",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Araba", "Silah", "Saf Aksiyon"]
  },
  {
    "title": "World War Z / Resident Evil Serisi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Zombi", "Virüs İstilası", "Aksiyon"]
  },
  {
    "title": "Abimm",
    "type": "movie",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Türk Sineması", "Dram", "Kardeşlik", "Üzücü"]
  },
  {
    "title": "A.R.O.G / G.O.R.A / Yahşi Batı / Cem Yılmaz Fundamentals",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Türk Sineması", "Komedi", "Cem Yılmaz"]
  },
  {
    "title": "Düğün Dernek / Kolpaçino / Maskeli Beşler / Recep İvedik Üçlemesi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Türk Sineması", "Komedi", "Absürt"]
  },
  {
    "title": "Kurtlar Vadisi Irak / Gladio / Filistin",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Türk Sineması", "Aksiyon", "Polat Alemdar"]
  },
  {
    "title": "Fetih 1453 / 300 Spartalı / Matrix Serisi",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Tarih", "Savaş", "Simülasyon", "Siberpunk"]
  },
  {
    "title": "Kung Fu Panda / Shrek / Madagaskar / Alvin ve Sincaplar / Asteriks ve Oniriks",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Animasyon", "Komedi", "Macera"]
  },
  {
    "title": "Joker (2019) / Split (Parçalanmış)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Psikolojik", "Gerilim", "Karanlık"]
  },
  {
    "title": "Howl's Moving Castle (Yüruyen Şato)",
    "type": "movie",
    "status": "completed",
    "personal_rating": "7.5/10",
    "tags": ["Anime Film", "Studio Ghibli", "Travmatik Etki"]
  },
  {
    "title": "Hababam Sınıfı (Yeni) / New York'ta Beş Minare / Hacivat Karagöz Neden Öldürüldü?",
    "type": "movie",
    "status": "completed",
    "personal_rating": "6.0/10",
    "tags": ["Türk Sineması", "Eh İşte"]
  },
  {
    "title": "The Incredibles / Up / Toy Story / Finding Nemo / Corpse Bride / Lion King",
    "type": "movie",
    "status": "completed",
    "personal_rating": "6.0/10",
    "tags": ["Pixar/Disney Animasyonları", "Eh İşte"]
  },
  {
    "title": "Esaretin Bedeli / Titanic / Fight Club / Yeşil Yol / V for Vendetta / Akıl Oyunları",
    "type": "movie",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Kült Filmler", "Plan listesi"]
  },
  {
    "title": "Sevginin Gücü / The Godfather / Gladyatör / Hancock / WALL-E / Zamana Karşı",
    "type": "movie",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Kült Filmler", "Plan listesi"]
  },
  {
    "title": "Para Avcısı / Diriliş / Fury / Malefiz / Amerikan Sapığı / Chihiro Gidişi / Dabbe Serisi / Koleksiyoncu / İhtiyarlara Yer Yok",
    "type": "movie",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Kült / Korku / Strateji Filmleri"]
  },
  {
    "title": "Hannibal",
    "type": "series",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Psikolojik Gerilim", "Suç", "Zeka", "Bayıldım"]
  },
  {
    "title": "You",
    "type": "series",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Joe Goldberg", "Psikolojik Gerilim", "Takip", "Bayıldım"]
  },
  {
    "title": "Love, Death & Robots",
    "type": "series",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Bilimkurgu", "Antoloji", "Siberpunk", "Yaşayan Sistemler", "Bayıldım"]
  },
  {
    "title": "What If...?",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Marvel", "Alternatif Evrenler", "Sistem Kırılımları", "Bayıldım"]
  },
  {
    "title": "Dexter",
    "type": "series",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Seri Katil", "Suç", "Gizem", "İyiydi"]
  },
  {
    "title": "Geniş Aile / Kardeş Payı / Komedi Dükkanı",
    "type": "series",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Türk Dizisi / Programı", "Komedi", "Absürt"]
  },
  {
    "title": "Rick and Morty",
    "type": "cartoon",
    "status": "completed",
    "personal_rating": "9.0/10",
    "tags": ["Bilimkurgu", "Boyutlar Arası", "Absürt Komedi", "Zeka"]
  },
  {
    "title": "Teach You a Lesson",
    "type": "series",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["İntikam", "Ders Verme", "Sistem", "Güzeldi"]
  },
  {
    "title": "Çok Güzel Hareketler Bunlar / Adanalı / Galip Derviş",
    "type": "series",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Türk Dizisi / Programı", "Polisiye", "Zeka", "Skeç"]
  },
  {
    "title": "The Walking Dead / Mr. Robot / Squid Game",
    "type": "series",
    "status": "watching",
    "personal_rating": "6.0/10",
    "tags": ["Zombi", "Hacker", "Hayatta Kalma Oyunu", "İlk Sezonlar"]
  },
  {
    "title": "Öyle Bir Geçer Zaman ki / Muhteşem Yüzyıl / Kurtlar Vadisi (Pusu) / Behzat Ç.",
    "type": "series",
    "status": "completed",
    "personal_rating": "6.0/10",
    "tags": ["Türk Dizisi", "Dram", "Polisiye", "Eh İşte"]
  },
  {
    "title": "Yahşi Cazibe / Çocuklar Duymasın / Doktorlar / Selena / Pis Yedili / 1 Kadın 1 Erkek",
    "type": "series",
    "status": "completed",
    "personal_rating": "6.0/10",
    "tags": ["Türk Dizisi", "Sitcom", "Gençlik", "Eh İşte"]
  },
  {
    "title": "Arka Sokaklar / Yaprak Dökümü / Seksenler / Sihirli Annem",
    "type": "series",
    "status": "dropped",
    "personal_rating": "3.0/10",
    "tags": ["Türk Dizisi", "Sevmezdim", "Bırakıldı"]
  },
  {
    "title": "Game of Thrones / Breaking Bad (Walter White) / Sherlock / Doctor Who / La Casa de Papel / The Mentalist / Dark / Black Mirror / The Witcher / House M.D.",
    "type": "series",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek Diziler", "Kült Yabancı Seriler", "Plan Listesi"]
  },
  {
    "title": "Steins;Gate",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Zaman Yolculuğu", "Bilimkurgu", "Zeka Oyunları", "Bayıldım"]
  },
  {
    "title": "Death Note",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Akıl Oyunları", "Kira", "Zeka", "Bayıldım"]
  },
  {
    "title": "One Punch Man (OPM)",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Saitama", "Overpowered", "Parodi", "Bayıldım"]
  },
  {
    "title": "Akame ga Kill!",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Suikastçı", "Karanlık Fantezi", "Aksiyon", "Bayıldım"]
  },
  {
    "title": "No Game No Life",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Oyun Dünyası", "Isekai", "Strateji", "Deha", "Bayıldım"]
  },
  {
    "title": "Attack on Titan (Shingeki no Kyojin)",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Devler", "Askeri Strateji", "Kült", "Sistem Kırılımı", "Bayıldım"]
  },
  {
    "title": "Fullmetal Alchemist: Brotherhood",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Simya", "Eşdeğer Değişim", "Askeri", "Başyapıt", "Bayıldım"]
  },
  {
    "title": "The Eminence in Shadow (Kage no Jitsuryokusha ni Naritakute!)",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Overpowered", "Cid Kagenou", "Komedi", "Bayıldım"]
  },
  {
    "title": "Gintama",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Parodi", "Samuray", "Absürt Komedi", "Bayıldım"]
  },
  {
    "title": "KonoSuba: God's Blessing on This Wonderful World!",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Parodi", "Komedi", "Absürt Ekip", "Bayıldım"]
  },
  {
    "title": "Overlord",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Ainz Ooal Gown", "Overpowered", "Karanlık Fantezi", "Bayıldım"]
  },
  {
    "title": "Youjo Senki (The Saga of Tanya the Evil)",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Askeri Strateji", "Büyü/Savaş", "Tanya", "Bayıldım"]
  },
  {
    "title": "Baki Serisi (Tüm Sezonlar)",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Dövüş Sanatları", "Saf Kas / Güç", "Aksiyon", "Bayıldım"]
  },
  {
    "title": "Shinchou Yuusha / Combatants Will Be Dispatched! / Uncle from Another World",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Isekai / Parodi", "Tedbirli Kahraman", "Sega Amca", "Bayıldım"]
  },
  {
    "title": "Highschool of the Dead (HOTD)",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Zombi İstilası", "Ecchi", "Hayatta Kalma", "Aksiyon", "Bayıldım"]
  },
  {
    "title": "Noragami / Kaguya-sama: Love is War / Dark Gathering",
    "type": "anime",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Tanrılar", "Aşk Savaşı / Zeka", "Hayalet Toplama Korku", "Bayıldım"]
  },
  {
    "title": "Frieren: Beyond Journey's End / Solo Leveling / Sword Art Online / Hunter x Hunter (2011) / Mob Psycho 100",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Zindan/Sistem", "Progression", "Nen", "Psişik Powers", "Güzel"]
  },
  {
    "title": "Assassination Classroom / Bleach / Seven Deadly Sins / Naruto / Tokyo Ghoul / Dr. STONE / DanMachi / Slime Tensei",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Shounen Klasikleri", "Bilim Zeka", "Şehir Kurma", "Zindan Sistemleri"]
  },
  {
    "title": "The Devil is a Part-Timer! / High School DxD / Shinmai Maou / Rosario to Vampire / Redo of Healer",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Ters Isekai", "Ecchi / Harem", "Karanlık İntikam", "Şifacı"]
  },
  {
    "title": "Dororo / Monster / Jigokuraku / Claymore / Kabaneri / Arifureta / Assassin Isekai / Netoge no Yome",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Karanlık Atmosfer", "Zeka Gizem", "Overpowered Isekai", "Oyun Evliliği"]
  },
  {
    "title": "Dandadan / Kekkai Sensen / Mashle / Shangri-La Frontier / Kuroshitsuji / Tomodachi Game / Maou Gakuin / Plunderer",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Yeni Nesil Aksiyon", "Zeka Oyunları", "Demon Lord", "Sistem"]
  },
  {
    "title": "Dungeon Meshi / Tsuki ga Michibiku / Ishuzoku Reviewers / Zom 100 / Wajutsushi (The Most Notorious Talker) / Gokudols",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Klan Yönetimi", "Yemek Fantezi", "Zombi", "Absürt Komedi"]
  },
  {
    "title": "Isekai de Cheat Skill / Record of Ragnarok / Full Dive RPG / Meikyuu Black Company / Maou-sama Retry! / Isekai Shikkaku",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Cheat Skills", "Turnuva Tanrılar", "Zindan Kapitalizm", "Kara Mizah"]
  },
  {
    "title": "Shin no Nakama / Trapped in a Dating Sim / I'm Quitting Heroing / Reincarnated as a Sword / Genjitsu Shugi Yuusha",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Slow Life", "Mecha Otome", "Kılıç Isekai", "Krallık Yönetimi"]
  },
  {
    "title": "Mo Dao Zu Shi / Kami-tachi ni Hirowareta Otoko / Monster Musume / Uzaki-chan / Toradora! / Komi-san / Tomo-chan / Nagatoro / Danshi Koukousei / Isekai One Turn Kill Neesan",
    "type": "anime",
    "status": "completed",
    "personal_rating": "8.0/10",
    "tags": ["Donghua Yetişim", "Slice of Life", "Okul Romantik", "Abla Isekai"]
  },
  {
    "title": "Oregairu / Kakegurui / Mirai Nikki / Bocchi the Rock! / Chuunibyou / Shimoneta / School Days / To LOVE-Ru / Immortal King / Faraway Paladin / Dead Mount / Assessment Assassin / Demon Lord 2099 / Mynoghra / Shin Shinka no Mi",
    "type": "anime",
    "status": "completed",
    "personal_rating": "6.0/10",
    "tags": ["Kumar", "Yandere", "Anksiyete", "Overpowered Çin", "Cyberpunk", "Eh İşte"]
  },
  {
    "title": "Bofuri / Log Horizon / Tonari no Totoro / Isekai no Seikishi Monogatari",
    "type": "anime",
    "status": "dropped",
    "personal_rating": "4.0/10",
    "tags": ["Oyun Dünyası", "Ghibli Yavaş", "Sevmedim"]
  },
  {
    "title": "Chainsaw Man / Demon Slayer / Fate Serisi / JoJo Serisi / Neon Genesis Evangelion / Death March / Ghost in the Shell / 5 Centimeters / Gurren Lagann / Berserk / King's Avatar / Villager A / Genius Prince / Punishment Hero / Failure Frame / Lord of the Mysteries / Seventh Prince / Rookie Older Adventurer / Lv2 Cheat / Faraway Paladin 2 / Tower of God / Infinite Gacha / Appraisal Skill / Ishura / Mynoghra 4X / Last Boss / Seitokai / Dawn of the Witch / Let This Grieving Soul Retire / Farmer Skill / Tales of Zestiria / Dark Healer / Mysterious Maid",
    "type": "anime",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek Animeler", "Dev Planlama Listesi", "Zeka / Mecha / Isekai / Sistem"]
  },
  {
    "title": "Omniscient Reader's Viewpoint (ORV)",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Sistem / Kıyamet", "Kim Dokja", "Senaryolar", "Progression Fantezi", "Bayıldım"]
  },
  {
    "title": "Latna Saga: Survival of a Sword King in a Fantasy World",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Overpowered", "Hatalı Sistem", "Saf Güç / Kas", "Kılıç Kralı", "Bayıldım"]
  },
  {
    "title": "The Greatest Estate Developer",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Isekai Mühendislik", "Lloyd Frontera", "Komedi / İnşaat", "Sistem", "Bayıldım"]
  },
  {
    "title": "FFF-Class Trashero",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Anti-Kahraman", "Isekai Parodi", "Sistem", "Kang Han-Soo", "Bayıldım"]
  },
  {
    "title": "Pick Me Up! (Infinite Gacha)",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Mobil Oyun Isekai", "Gacha / Hayatta Kalma", "Karanlık Atmosfer", "Sistem", "Bayıldım"]
  },
  {
    "title": "Murim Login",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Murim / Avcı", "Sistem Kapsülü", "Gelişim / Progression", "Komedi", "Bayıldım"]
  },
  {
    "title": "Tyrant of the Tower Defense Game",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Kule Savunması", "Strateji / Ölüm Kalım", "Zorlu Sistem", "Deha", "Bayıldım"]
  },
  {
    "title": "Nano Machine",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "10/10",
    "tags": ["Murim / Bilimkurgu", "Nanoteknoloji", "Overpowered", "Gelişim", "Bayıldım"]
  },
  {
    "title": "Solo Leveling",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Zindan / Sistem", "Sung Jin-Woo", "Gelişim", "Gölge Ordusu", "Güzeldi"]
  },
  {
    "title": "Trash of the Count's Family (Lout of Count's Family)",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Reenkarnasyon", "Strateji", "Ejderha Evcil Hayvan", "Güzeldi"]
  },
  {
    "title": "The Archmage Returns After 4000 Years",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Büyücü / Geri Dönüş", "Lucas Trowman", "Tanrısal Güç", "Güzeldi"]
  },
  {
    "title": "A Returner's Magic Should Be Special",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Zaman Döngüsü / Regressor", "Gölge Dünyası", "Strateji", "Güzeldi"]
  },
  {
    "title": "SSS-Class Revival Hunter",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Ölerek Geri Dönme", "Kule Tırmanma", "Sistem Yetenekleri", "Güzeldi"]
  },
  {
    "title": "The Knight Only Lives Today / Revenge of the Baskerville Bloodhound / Hardcore Leveling Warrior: Earth Game / The Infinite Mage / The Grand Mudang Saga / I'm Not That Kind of Talent",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["İntikam", "Kılıç Şövalye", "Sistem Oyunları", "Murim Reenkarnasyon", "Güzeldi"]
  },
  {
    "title": "The World After the Fall / Chronicles of the Demon Faction / Return of the Disaster-Class Hero / The Beginning After The End / Doom Breaker (Suicidal Battle God) / Swordmaster's Youngest Son",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Kule Sonrası", "Murim Faksiyonu", "Kralın Reenkarnasyonu", "Karanlık Regressor"]
  },
  {
    "title": "Standard Of Reincarnation / To Be An Actor / Mercenary Enrollment / Overgeared / Damn Reincarnation / Overpowered Sword / Player Who Returned After 10000 Years / Reincarnated Murim Lord",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "8.5/10",
    "tags": ["Paralı Asker", "Ekipman Delisi", "Reenkarnasyon / Oyun", "10000 Yıl Cehennem", "Güzeldi"]
  },
  {
    "title": "My Blasted Reincarnated Life",
    "type": "manhwa",
    "status": "completed",
    "personal_rating": "6.0/10",
    "tags": ["Reenkarnasyon", "Eh İşte"]
  },
  {
    "title": "Reborn as a Scholar / Dungeon Reset / Heavenly Demon Reborn! / The Extra's Academy Survival Guide / Myst, Might, Mayhem / The Stellar Swordmaster",
    "type": "manhwa",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek Manhvalar", "Zindan Sıfırlama", "Murim Gelişimi", "Akademi Hayatta Kalma"]
  },
  {
    "title": "Absolute Regression / A Regressor's Tale of Cultivation / Dungeon Odyssey / The Ember Knight / Level Up with the Gods / The Novel's Extra (Remake) / The Lazy Lord Masters the Sword",
    "type": "manhwa",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek Manhvalar", "Geri Sarma", "Yetişim", "Tanrılarla Seviye Atlama", "Uyuşuk Soylu"]
  },
  {
    "title": "Nebula's Civilization / Bad Born Blood / Chronicles of a Doomed Prodigy / Too Many Heroes / The Academy's Undercover Professor / Second Life Ranker / The Skeleton Soldier Failed to Defend the Dungeon",
    "type": "manhwa",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek Manhvalar", "Medeniyet Tanrısı", "İskelet Asker", "Kule İntikam", "Sonsuz Döngü"]
  },
  {
    "title": "Yongsa High: Dungeon Raiders / Absolute Reign / I Killed the Main Player / Shadow of the Supreme / My Avatars' Path to Greatness / The Legendary Moonlight Sculptor / Returning With Absolutely Nothing / Masters of Lightning Knives",
    "type": "manhwa",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek Manhvalar", "Sanal Gerçeklik", "Ana Oyuncuyu Öldürmek", "Zindan Okulu"]
  },
  {
    "title": "Return of the War God / Martial Divine Demon / After Ten Millennia in Hell / The Bastard of Swordborne / My S-Class Hunters / Demon King of the Royal Class / Cassmire / The Sichuan Tang Clan's Entomologist / Reincarnation of the Fist King / Cheonhwa Archive's Young Master / The Legendary Spearman Returns / The Return Of The 8th Class Mage",
    "type": "manhwa",
    "status": "planning",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek Manhvalar", "Murim Gelişimi", "S-Sınıfı Avcılar", "Klan Böcek Bilimcisi"]
  }

  {
    "title": "Hugo",
    "type": "tv-show",
    "status": "completed",
    "release_year": "1992",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Nostalji", "İnteraktif Oyun", "Telefon", "Çocukluk"],
    "sites": []
  },
  {
    "title": "Bakugan Battle Brawlers",
    "type": "anime",
    "status": "completed",
    "release_year": "2007",
    "my_progress": "Tüm Sezonlar",
    "personal_rating": "9.5/10",
    "tags": ["Strateji", "Kart Oyunu", "Canavarlar", "Isekai / Elementler"],
    "sites": []
  },
  {
    "title": "Beyblade",
    "type": "anime",
    "status": "completed",
    "release_year": "2001",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Kutsal Canavarlar", "Turnuva", "Çocukluk"],
    "sites": []
  },
  {
    "title": "Dexter's Laboratory",
    "type": "cartoon",
    "status": "completed",
    "release_year": "1996",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Bilim", "Laboratuvar", "Komedi", "Cartoon Network"],
    "sites": []
  },
  {
    "title": "Totally Spies! (Ajanlar)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2001",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Casusluk", "Ajan", "Aksiyon", "Jetix"],
    "sites": []
  },
  {
    "title": "Ed, Edd n Eddy",
    "type": "cartoon",
    "status": "completed",
    "release_year": "1999",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Mahalle", "Komedi", "Absürt", "Cartoon Network"],
    "sites": []
  },
  {
    "title": "Megas XLR",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2004",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Mecha", "Dev Robot", "Modifiye", "Efsane"],
    "sites": []
  },
  {
    "title": "Ben 10",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2005",
    "my_progress": "Klasik Seri",
    "personal_rating": "9.5/10",
    "tags": ["Omnitrix", "Uzaylılar", "Aksiyon", "Cartoon Network"],
    "sites": []
  },
  {
    "title": "Generator Rex",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2010",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Nanoteknoloji", "Mutasyon", "Aksiyon", "Sci-Fi"],
    "sites": []
  },
  {
    "title": "Adventure Time",
    "type": "cartoon",
    "status": "watching",
    "release_year": "2010",
    "my_progress": "Yeni Bölümler Dahil",
    "personal_rating": "10/10",
    "tags": ["Post-Apokaliptik", "Fantezi", "Macera", "Yaşayan Sistem"],
    "sites": []
  },
  {
    "title": "Space Goofs (Uzay Çılgınları)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "1997",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Uzaylılar", "Dünya", "Komedi"],
    "sites": []
  },
  {
    "title": "Limitless",
    "type": "series",
    "status": "completed",
    "release_year": "2015",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["NZT-48", "Zeka Gelişimi", "Aksiyon", "Sci-Fi"],
    "sites": []
  },
  {
    "title": "Avengers / Wolverine / Spider-Man Serileri",
    "type": "cartoon / movie",
    "status": "completed",
    "release_year": "2000s",
    "my_progress": "Genel İzleme",
    "personal_rating": "8.5/10",
    "tags": ["Marvel", "Süper Kahraman", "Aksiyon"],
    "sites": []
  },
  {
    "title": "Yu-Gi-Oh!",
    "type": "anime",
    "status": "completed",
    "release_year": "2000",
    "my_progress": "Klasik Seri",
    "personal_rating": "10/10",
    "tags": ["Kart Savaşı", "Düello", "Firavun", "Efsane"],
    "sites": []
  },
  {
    "title": "Max Steel",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2013",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Nano Suit", "Zırh", "Aksiyon", "Sci-Fi"],
    "sites": []
  },
  {
    "title": "Teletubbies",
    "type": "tv-show",
    "status": "dropped",
    "release_year": "1997",
    "my_progress": "Bırakıldı",
    "personal_rating": "3.0/10",
    "tags": ["Çocuk Programı", "Sevilmedi"],
    "sites": []
  },
  {
    "title": "Regular Show (Sürekli Dizi)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2010",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.5/10",
    "tags": ["Komedi", "Absürt", "Kült", "Cartoon Network"],
    "sites": []
  },
  {
    "title": "Samurai Jack",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2001",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Aksiyon", "Distopya", "Samuray", "Efsane"],
    "sites": []
  },
  {
    "title": "The Amazing World of Gumball",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2011",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Komedi", "Absürt", "Aile"],
    "sites": []
  },
  {
    "title": "The Marvelous Misadventures of Flapjack",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2008",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Karanlık Atmosfer", "Macera", "Denizcilik"],
    "sites": []
  },
  {
    "title": "DreamWorks Dragons (Ejderha Binicileri)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2012",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Ejderhalar", "Macera", "Fantezi"],
    "sites": []
  },
  {
    "title": "The Secret Saturdays",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2008",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Kriptidler", "Gizem", "Macera"],
    "sites": []
  },
  {
    "title": "Total Drama Island (Drama Adası)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2007",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Yarışma", "Parodi", "Gençlik"],
    "sites": []
  },
  {
    "title": "Green Lantern: The Animated Series",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2011",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["DC", "Uzay", "Süper Kahraman"],
    "sites": []
  },
  {
    "title": "Justice League / Justice League Unlimited",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2001",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["DC", "Süper Kahraman", "Ekip"],
    "sites": []
  },
  {
    "title": "Sonic X / Sonic Serileri",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2003",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Hız", "Kirpi", "Aksiyon"],
    "sites": []
  },
  {
    "title": "Transformers Prime / Animated",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2010",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Robotlar", "Sci-Fi", "Aksiyon"],
    "sites": []
  },
  {
    "title": "Johnny Bravo",
    "type": "cartoon",
    "status": "completed",
    "release_year": "1997",
    "my_progress": "Tamamlandı",
    "personal_rating": "7.5/10",
    "tags": ["Komedi", "Nostalji"],
    "sites": []
  },
  {
    "title": "Star Wars: The Clone Wars",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2008",
    "my_progress": "Genel İzleme",
    "personal_rating": "7.5/10",
    "tags": ["Star Wars", "Sci-Fi", "Uzay"],
    "sites": []
  },
  {
    "title": "Teen Titans Go!",
    "type": "cartoon",
    "status": "watching",
    "release_year": "2013",
    "my_progress": "Eh İşte",
    "personal_rating": "6.0/10",
    "tags": ["DC", "Parodi", "Çocuksu"],
    "sites": []
  },
  {
    "title": "Ninjago: Masters of Spinjitzu",
    "type": "cartoon",
    "status": "watching",
    "release_year": "2011",
    "my_progress": "Eh İşte",
    "personal_rating": "6.0/10",
    "tags": ["Lego", "Ninja", "Elementler"],
    "sites": []
  },
  {
    "title": "Over the Garden Wall (Bahçe Duvarının Ötesinde)",
    "type": "cartoon",
    "status": "dropped",
    "release_year": "2014",
    "my_progress": "Bırakıldı",
    "personal_rating": "4.0/10",
    "tags": ["Gizem", "Sevilmedi"],
    "sites": []
  },
  {
    "title": "Steven Universe",
    "type": "cartoon",
    "status": "dropped",
    "release_year": "2013",
    "my_progress": "Bırakıldı",
    "personal_rating": "3.0/10",
    "tags": ["Kristal Taşlar", "Sevilmedi"],
    "sites": []
  },
  {
    "title": "We Bare Bears (Kafadan Ayılar)",
    "type": "cartoon",
    "status": "dropped",
    "release_year": "2015",
    "my_progress": "Bırakıldı",
    "personal_rating": "4.5/10",
    "tags": ["Komedi", "Sevilmedi"],
    "sites": []
  },
  {
    "title": "Uncle Grandpa / Clarence",
    "type": "cartoon",
    "status": "dropped",
    "release_year": "2013",
    "my_progress": "Bırakıldı",
    "personal_rating": "3.0/10",
    "tags": ["Cartoon Network", "Sevilmedi"],
    "sites": []
  },
  {
    "title": "Tom and Jerry / Scooby-Doo / Looney Tunes / Powerpuff Girls",
    "type": "cartoon",
    "status": "completed",
    "release_year": "Classic",
    "my_progress": "Genel İzleme (Eh İşte)",
    "personal_rating": "6.5/10",
    "tags": ["Klasik Nostalji"],
    "sites": []
  },
  {
    "title": "Kim Possible",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2002",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Casusluk", "Aksiyon", "Disney Channel", "Efsane"],
    "sites": []
  },
  {
    "title": "Gravity Falls (Esrarengiz Kasaba)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2012",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.5/10",
    "tags": ["Gizem", "Doğaüstü", "Macera", "Kült"],
    "sites": []
  },
  {
    "title": "Phineas and Ferb (Fineas ve Förb)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2007",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Mühendislik", "Zeka", "Komedi", "Yaz Tatili"],
    "sites": []
  },
  {
    "title": "American Dragon: Jake Long (Genç Ejder)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2005",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Ejderha", "Dönüşüm", "Aksiyon", "Gizli Kimlik"],
    "sites": []
  },
  {
    "title": "The Emperor's New School (Şaşkın İmparator'un Okulu)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "2006",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Komedi", "Okul", "Mitoloji/Antik"],
    "sites": []
  },
  {
    "title": "Aladdin (Çizgi Dizi)",
    "type": "cartoon",
    "status": "completed",
    "release_year": "1994",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Fantezi", "Büyü", "Macera"],
    "sites": []
  },
  {
    "title": "Mickey Mouse / Monsters At Work (Sevimli Canavarlar)",
    "type": "cartoon",
    "status": "watching",
    "release_year": "Classic/Modern",
    "my_progress": "Eh İşte",
    "personal_rating": "6.0/10",
    "tags": ["Disney Klasikleri"],
    "sites": []
  },
  {
    "title": "My Little Pony",
    "type": "cartoon",
    "status": "dropped",
    "release_year": "2010",
    "my_progress": "Bırakıldı",
    "personal_rating": "3.0/10",
    "tags": ["Sevilmedi"],
    "sites": []
  },
  {
    "title": "The Many Adventures of Winnie the Pooh (Tigger ve Pooh)",
    "type": "cartoon",
    "status": "dropped",
    "release_year": "Classic",
    "my_progress": "Bırakıldı",
    "personal_rating": "3.5/10",
    "tags": ["Çocuksu", "Sevilmedi"],
    "sites": []
  },
  {
    "title": "The Yogi Bear Show",
    "type": "cartoon",
    "status": "dropped",
    "release_year": "Classic",
    "my_progress": "Bırakıldı",
    "personal_rating": "3.0/10",
    "tags": ["Hanna-Barbera", "Sevilmedi"],
    "sites": []
  },
  {
    "title": "Disney Broken Karaoke",
    "type": "cartoon",
    "status": "dropped",
    "release_year": "2019",
    "my_progress": "Bırakıldı",
    "personal_rating": "2.0/10",
    "tags": ["Müzikal", "Kısa Seri", "Sevilmedi"],
    "sites": []
  },
  {
    "title": "Inception",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Bilimkurgu", "Rüya", "Zihin Çalma", "Aksiyon"],
    "sites": []
  },
  {
    "title": "The Lord of the Rings (Yüzüklerin Efendisi Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Fantezi", "Mitoloji", "Destansı", "Başyapıt"],
    "sites": []
  },
  {
    "title": "Batman Serisi (Kara Şövalye ve Tüm Filmler)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["DC", "Süper Kahraman", "Karanlık Atmosfer", "Aksiyon"],
    "sites": []
  },
  {
    "title": "I Am Legend (Ben Efsaneyim)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Post-Apokaliptik", "Virüs", "Hayatta Kalma", "Zombi"],
    "sites": []
  },
  {
    "title": "Pirates of the Caribbean (Karayip Korsanları Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Kaptan Jack Sparrow", "Korsanlar", "Macera", "Mitoloji"],
    "sites": []
  },
  {
    "title": "Transformers Serisi",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Mecha", "Robotlar", "Aksiyon", "Bilimkurgu"],
    "sites": []
  },
  {
    "title": "Terminator Serisi",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Zaman Yolculuğu", "Robotlar", "Aksiyon", "Kült"],
    "sites": []
  },
  {
    "title": "Real Steel (Çelik Yumruk)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Robot Dövüşleri", "Aksiyon", "Dram", "Gelecek"],
    "sites": []
  },
  {
    "title": "Pacific Rim (Pasifik Savaşı Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Jaeger", "Kaiju", "Dev Robotlar", "Aksiyon"],
    "sites": []
  },
  {
    "title": "Ghost Rider (Hayalet Sürücü)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Marvel", "Anti-Kahraman", "Doğaüstü", "Alevli Zincir"],
    "sites": []
  },
  {
    "title": "Percy Jackson Serisi",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Mitoloji", "Yunan Tanrıları", "Fantastik", "Macera"],
    "sites": []
  },
  {
    "title": "Sherlock Holmes Serisi",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Gizem", "Zeka", "Dedektif", "Aksiyon"],
    "sites": []
  },
  {
    "title": "Spider-Man (Tobey Maguire Üçlemesi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.5/10",
    "tags": ["Nostalji", "Marvel", "Örümcek Adam", "Çocukluk"],
    "sites": []
  },
  {
    "title": "Limitless (Film)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.5/10",
    "tags": ["NZT-48", "Zeka", "Güçlenme", "Kült"],
    "sites": []
  },
  {
    "title": "Avatar",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Sci-Fi", "Pandora", "Görsel Şölen", "Uzay"],
    "sites": []
  },
  {
    "title": "Twilight (Alacakaranlık Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Vampirler", "Kurt Adamlar", "Fantastik"],
    "sites": []
  },
  {
    "title": "Ice Age (Buz Devri Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Animasyon", "Nostalji", "Komedi", "Çocukluk"],
    "sites": []
  },
  {
    "title": "Avengers / Iron Man / Thor / Captain America / Doctor Strange / Venom / Deadpool",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Marvel", "Süper Kahraman Evreni", "Aksiyon"],
    "sites": []
  },
  {
    "title": "Edge of Tomorrow (Yarının Sınırında)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Zaman Döngüsü", "Uzaylı İstilası", "Progression", "Aksiyon"],
    "sites": []
  },
  {
    "title": "The Mummy / The Scorpion King Serisi (Mumya ve Akrepler Kralı)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Mitoloji", "Antik Mısır", "Macera", "Aksiyon"],
    "sites": []
  },
  {
    "title": "Undisputed (Yenilmez Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Dövüş", "Boyka", "Hapishane", "Aksiyon"],
    "sites": []
  },
  {
    "title": "The Maze Runner (Labirent: Ölümcül Kaçış Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Distopya", "Kaçış", "Gizem", "Hayatta Kalma"],
    "sites": []
  },
  {
    "title": "Planet of the Apes (Maymunlar Cehennemi Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Evrim", "Bilimkurgu", "Distopya", "Savaş"],
    "sites": []
  },
  {
    "title": "3 Idiots",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Eğitim Sistemi", "Dostluk", "Komedi", "Dram"],
    "sites": []
  },
  {
    "title": "Harry Potter Serisi",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Büyü", "Hogwarts", "Fantastik"],
    "sites": []
  },
  {
    "title": "The Hobbit: An Unexpected Journey",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Orta Dünya", "Fantezi", "Macera"],
    "sites": []
  },
  {
    "title": "The Hunger Games (Açlık Oyunları Serisi)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Distopya", "Hayatta Kalma", "Yarışma"],
    "sites": []
  },
  {
    "title": "Fast & Furious / Ölüm Yarışı / Taşıyıcı / Tetikci / John Wick",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Araba / Silah", "Saf Aksiyon", "Yarış"],
    "sites": []
  },
  {
    "title": "World War Z / Resident Evil Serisi",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Zombi İstilası", "Kıyamet Günü", "Aksiyon"],
    "sites": []
  },
  {
    "title": "Abimm",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Türk Sineması", "Dram", "Kardeşlik", "Duygusal/Üzücü"],
    "sites": []
  },
  {
    "title": "A.R.O.G / G.O.R.A / Yahşi Batı / Cem Yılmaz Fundamentals",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Türk Sineması", "Komedi", "Cem Yılmaz"],
    "sites": []
  },
  {
    "title": "Düğün Dernek / Kolpaçino / Maskeli Beşler / Recep İvedik Üçlemesi",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Türk Sineması", "Komedi", "Absürt"],
    "sites": []
  },
  {
    "title": "Kurtlar Vadisi Irak / Gladio / Filistin",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Türk Sineması", "Aksiyon", "Politik", "Polat Alemdar"],
    "sites": []
  },
  {
    "title": "Fetih 1453",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Tarih", "Savaş", "İstanbul'un Fethi"],
    "sites": []
  },
  {
    "title": "300 (300 Spartalı)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Savaş", "Tarih", "Epik Aksiyon"],
    "sites": []
  },
  {
    "title": "Matrix Serisi",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Simülasyon", "Bilimkurgu", "Siberpunk"],
    "sites": []
  },
  {
    "title": "Kung Fu Panda / Shrek / Madagaskar / Alvin ve Sincaplar / Asena ve Oniriks",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Animasyon", "Komedi", "Macera"],
    "sites": []
  },
  {
    "title": "Joker (2019) / Split (Parçalanmış)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Psikolojik", "Gerilim", "Karanlık"],
    "sites": []
  },
  {
    "title": "Howl's Moving Castle (Yürüyen Şato)",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "7.5/10",
    "tags": ["Anime Film", "Studio Ghibli", "Travmatik Etki"],
    "sites": []
  },
  {
    "title": "Hababam Sınıfı (Yeni Nesil) / New York'ta Beş Minare / Hacivat Karagöz Neden Öldürüldü?",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Türk Sineması", "Eh İşte"],
    "sites": []
  },
  {
    "title": "The Incredibles / Up / Toy Story / Finding Nemo / Corpse Bride / Lion King / Shark Tale",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Pixar/Disney Animasyonları", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Cars",
    "type": "movie",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Animasyon", "Arabalar", "Sevdim"],
    "sites": []
  },
  {
    "title": "The Shawshank Redemption (Esaretin Bedeli)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Hapishane", "Kült", "Dram"],
    "sites": []
  },
  {
    "title": "Titanic",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Romantik", "Dram", "Tarihi Felaket"],
    "sites": []
  },
  {
    "title": "Fight Club (Dövüş Kulübü)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Psikolojik", "Yeraltı", "Kült"],
    "sites": []
  },
  {
    "title": "The Green Mile (Yeşil Yol)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Dram", "Doğaüstü", "Hapishane"],
    "sites": []
  },
  {
    "title": "V for Vendetta",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Dystopia", "Anarşizm", "Politik"],
    "sites": []
  },
  {
    "title": "A Beautiful Mind (Akıl Oyunları)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Biyografi", "Matematik", "Zihin"],
    "sites": []
  },
  {
    "title": "Léon: The Professional (Sevginin Gücü)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Suikastçı", "Suç", "Dram"],
    "sites": []
  },
  {
    "title": "The Godfather",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Mafya", "Suç", "Kült Klasik"],
    "sites": []
  },
  {
    "title": "Gladiator",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Roma", "İntikam", "Tarihi Altyapı"],
    "sites": []
  },
  {
    "title": "Hancock",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Anti-Kahraman", "Komedi", "Süper Kahraman"],
    "sites": []
  },
  {
    "title": "WALL-E",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Bilimkurgu", "Robot", "Gelecek"],
    "sites": []
  },
  {
    "title": "In Time (Zamana Karşı)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Zaman Para Birimidir", "Bilimkurgu", "Aksiyon"],
    "sites": []
  },
  {
    "title": "The Wolf of Wall Street (Para Avcısı)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Borsa", "Biyografi", "Suç/Komedi"],
    "sites": []
  },
  {
    "title": "The Revenant (Diriliş)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Hayatta Kalma", "İntikam", "Doğa"],
    "sites": []
  },
  {
    "title": "Fury",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "2. Dünya Savaşı", "Tank", "Askeri"],
    "sites": []
  },
  {
    "title": "Maleficent (Malefiz)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Fantastik", "Büyü", "Masal"],
    "sites": []
  },
  {
    "title": "American Psycho (Amerikan Sapığı)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Psikolojik Gerilim", "Kült", "Patrick Bateman"],
    "sites": []
  },
  {
    "title": "Spirited Away (Sen to Chihiro no Kamikakushi)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Anime Film", "Studio Ghibli", "Fantezi"],
    "sites": []
  },
  {
    "title": "Dabbe Serisi",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Türk Korku", "Cin", "Doğaüstü"],
    "sites": []
  },
  {
    "title": "The Collector (Koleksiyoncu) / No Country for Old Men (İhtiyarlara Yer Yok)",
    "type": "movie",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Gerilim", "Suç", "Av"],
    "sites": []
  },
  {
    "title": "Hannibal",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Psikolojik Gerilim", "Suç", "Zeka", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Dexter",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Seri Katil", "Suç", "Gizem", "İyiydi"],
    "sites": []
  },
  {
    "title": "Geniş Aile",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Türk Dizisi", "Komedi", "Cevahir ve Koyu Bilal"],
    "sites": []
  },
  {
    "title": "Kardeş Payı",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Türk Dizisi", "Komedi", "Mucit Kardeşler", "Selçuk Aydemir"],
    "sites": []
  },
  {
    "title": "Komedi Dükkanı (Tolga Çevik)",
    "type": "tv-show",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Türk Programı", "Doğaçlama Tiyatro", "Arkadaşım", "Komedi"],
    "sites": []
  },
  {
    "title": "Çok Güzel Hareketler Bunlar (1. Kuşak)",
    "type": "tv-show",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Türk Programı", "Tiyatro", "Skeç", "BKM Mutfak"],
    "sites": []
  },
  {
    "title": "Adanalı",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Türk Dizisi", "Aksiyon", "Polisiye", "Maraz Ali"],
    "sites": []
  },
  {
    "title": "Galip Derviş",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Türk Dizisi", "Polisiye", "Gizem", "Zeka/Monk Uyarlaması"],
    "sites": []
  },
  {
    "title": "The Walking Dead",
    "type": "series",
    "status": "watching",
    "my_progress": "İlk Birkaç Sezon",
    "personal_rating": "6.0/10",
    "tags": ["Zombi Kıyameti", "Hayatta Kalma", "İlk Birkaç Sezon"],
    "sites": []
  },
  {
    "title": "Mr. Robot",
    "type": "series",
    "status": "watching",
    "my_progress": "Sub-titles / Devam Ediyor",
    "personal_rating": "6.0/10",
    "tags": ["Siber Güvenlik", "Hacker", "Psikolojik"],
    "sites": []
  },
  {
    "title": "Öyle Bir Geçer Zaman ki / Muhteşem Yüzyıl / Kurtlar Vadisi (Pusu dönemi)",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Türk Dizisi", "Dram/Tarih/Aksiyon", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Behzat Ç. Bir Ankara Polisiyesi",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Türk Dizisi", "Polisiye", "Ankara", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Yahşi Cazibe / Çocuklar Duymasın / Doktorlar / Selena / Pis Yedili / 1 Kadın 1 Erkek",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Türk Dizisi", "Sitcom/Gençlik/Dram", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Arka Sokaklar",
    "type": "series",
    "status": "dropped",
    "my_progress": "Bırakıldı",
    "personal_rating": "4.0/10",
    "tags": ["Türk Dizisi", "Polisiye", "Pek Sevmezdi"],
    "sites": []
  },
  {
    "title": "Yaprak Dökümü / Seksenler / Sihirli Annem",
    "type": "series",
    "status": "dropped",
    "my_progress": "Bırakıldı",
    "personal_rating": "3.0/10",
    "tags": ["Türk Dizisi", "Dram/Nostalji/Fantastik", "Sevmezdim"],
    "sites": []
  },
  {
    "title": "Game of Thrones",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Fantezi", "Politik Savaş", "Ejderhalar"],
    "sites": []
  },
  {
    "title": "Breaking Bad",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Walter White", "Kimya", "Suç İmparatorluğu", "Kült"],
    "sites": []
  },
  {
    "title": "Sherlock",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Dedektif", "Zeka", "Modern Londra"],
    "sites": []
  },
  {
    "title": "Doctor Who",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Zaman Yolculuğu", "Sci-Fi", "TARDIS"],
    "sites": []
  },
  {
    "title": "La Casa de Papel",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Soygun", "Strateji", "Profesör"],
    "sites": []
  },
  {
    "title": "The Mentalist",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Gözlem/Zeka", "Polisiye", "Red John"],
    "sites": []
  },
  {
    "title": "Dark (2017)",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Zaman Döngüsü", "Gizem", "Paradoks"],
    "sites": []
  },
  {
    "title": "You (Joe Goldberg)",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Joe Goldberg", "Psikolojik Gerilim", "Takip/Takıntı", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Rick and Morty",
    "type": "cartoon",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "9.0/10",
    "tags": ["Bilimkurgu", "Boyutlar Arası", "Absürt Komedi", "Zeka"],
    "sites": []
  },
  {
    "title": "Teach You a Lesson",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["İntikam", "Ders Verme", "Sistem/Okul", "Güzeldi"],
    "sites": []
  },
  {
    "title": "Squid Game",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Hayatta Kalma Oyunu", "Dystopia", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Black Mirror",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Teknoloji Distopyası", "Antoloji", "Sci-Fi"],
    "sites": []
  },
  {
    "title": "Love, Death & Robots",
    "type": "series",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Bilimkurgu", "Antoloji", "Siberpunk", "Yaşayan Sistemler", "Bayıldım"],
    "sites": []
  },
  {
    "title": "What If...?",
    "type": "cartoon",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Marvel", "Alternatif Evrenler", "Çoklu Evren", "Sistem Kırılımları", "Bayıldım"],
    "sites": []
  },
  {
    "title": "The Witcher",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Fantezi", "Geralt of Rivia", "Canavar Avcısı", "Mutasyon"],
    "sites": []
  },
  {
    "title": "House M.D.",
    "type": "series",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Medikal", "Gizem", "Zeka", "Gregory House"],
    "sites": []
  },
  {
    "title": "Steins;Gate",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Zaman Yolculuğu", "Bilimkurgu", "Paradoks", "Zeka Oyunları", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Death Note",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Akıl Oyunları", "Şinigami", "Kira", "Zeka", "Adalet", "Bayıldım"],
    "sites": []
  },
  {
    "title": "One Punch Man",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Saitama", "Overpowered", "Parodi", "Aksiyon", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Akame ga Kill!",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Suikastçı", "Karanlık Fantezi", "Aksiyon", "Dram", "Bayıldım"],
    "sites": []
  },
  {
    "title": "No Game No Life",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Oyun Dünyası", "Isekai", "Strateji", "Deha", "Blank", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Attack on Titan",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Devler", "Askeri Strateji", "Distopya", "Kült", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Fullmetal Alchemist: Brotherhood",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Simya", "Eşdeğer Değişmiş", "Askeri", "Macera", "Başyapıt", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Kiseijû: Sei no Kakuritsu (Parasyte -the maxim-)",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Parazit", "Mutasyon", "Sci-Fi", "Psikolojik Aksiyon", "Migi"],
    "sites": []
  },
  {
    "title": "Classroom of the Elite",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Kiyotaka Ayanokoji", "Okul Sistemi", "Strateji", "Zeka Oyunları"],
    "sites": []
  },
  {
    "title": "Charlotte",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Özel Güçler", "Göz Kayması", "Okul", "Dram/Aksiyon"],
    "sites": []
  },
  {
    "title": "Sakamoto Desu ga?",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Komedi", "Kusursuz Karakter", "Okul Life", "Absürt"],
    "sites": []
  },
  {
    "title": "Rakudai Kishi no Cavalry",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Büyülü Şövalyeler", "Turnuva", "Aksiyon", "Okul"],
    "sites": []
  },
  {
    "title": "Another",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Gizem", "Lanet/Korku", "Okul", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Elfen Lied",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Gore/Vahşet", "Psikolojik Bilimkurgu", "Vektörler", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Ghost in the Shell",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Siberpunk", "Felsefe", "Yapay Zeka", "Kült Sci-Fi"],
    "sites": []
  },
  {
    "title": "5 Centimeters per Second",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Anime Film", "Romantizm", "Dram", "Makoto Shinkai"],
    "sites": []
  },
  {
    "title": "Tengen Toppa Gurren Lagann",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Mecha", "Dev Robotlar", "Evrimsel Güçlenme", "Aksiyon"],
    "sites": []
  },
  {
    "title": "The Eminence in Shadow",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Overpowered", "Cid Kagenou", "Komedi", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Cyberpunk: Edgerunners",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Siberpunk", "Aksiyon", "Dram", "Studio Trigger", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Code Geass: Lelouch of the Rebellion",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Mecha", "Askeri Strateji", "Deha", "Lelouch", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Gintama",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Parodi", "Samuray", "Absürt Komedi", "Efsane", "Bayıldım"],
    "sites": []
  },
  {
    "title": "KonoSuba: God's Blessing on This Wonderful World!",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Parodi", "Komedi", "Absürt Ekip", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Overlord",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Ainz Ooal Gown", "Overpowered", "Karanlık Fantezi", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Youjo Senki (The Saga of Tanya the Evil)",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Askeri Strateji", "Büyü/Savaş", "Tanya", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Baki Serisi",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Dövüş Sanatları", "Saf Kas / Güç", "Aksiyon", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Shinchou Yuusha: Kono Yuusha ga Ore Tueee Kuse ni Shinchou Sugiru",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Isekai", "Aşırı Tedbirli Kahraman", "Komedi", "Aksiyon", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Sentouin, Haken shimasu!",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["KonoSuba Yazarından", "Komedi", "Bilimkurgu/Fantezi", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Isekai Ojisan",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Ters Isekai", "Sega", "Komedi", "Parodi", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Highschool of the Dead",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Zombi İstilası", "Ecchi", "Hayatta Kalma", "Aksiyon", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Noragami",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Mitoloji/Tanrılar", "Yato", "Aksiyon", "Komedi", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Kaguya-sama: Love is War",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "10/10",
    "tags": ["Akıl Oyunları", "Romantik Komedi", "Zeka", "Bayıldım"],
    "sites": []
  },
  {
    "title": "Frieren: Beyond Journey's End",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Fantezi", "Macera", "Zaman Akışı", "Büyü", "Güzel"],
    "sites": []
  },
  {
    "title": "Solo Leveling (Anime)",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["System/Zindan", "Progression", "Sung Jin-Woo", "Gelişim", "İyi"],
    "sites": []
  },
  {
    "title": "Sword Art Online",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["VRMMORPG", "Oyun Dünyası", "Aksiyon", "Kirito", "Güzeldi"],
    "sites": []
  },
  {
    "title": "Hunter x Hunter (2011)",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Nen Sistemi", "Macera", "Strateji", "Kült", "Güzeldi"],
    "sites": []
  },
  {
    "title": "Mob Psycho 100",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Psişik Güçler", "Aksiyon/Komedi", "ONE", "Güzeldi"],
    "sites": []
  },
  {
    "title": "Assassination Classroom",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Koro-sensei", "Okul/Suikast", "Komedi", "Dram", "İyiydi"],
    "sites": []
  },
  {
    "title": "Bleach / The Seven Deadly Sins / Naruto / Tokyo Ghoul",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Shounen Klasikleri", "Aksiyon", "Güç Sistemleri"],
    "sites": []
  },
  {
    "title": "Dr. STONE",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Bilim/Zeka", "Taş Devri", "Medeniyet Kurma", "Güzeldi"],
    "sites": []
  },
  {
    "title": "DanMachi / Slime Tensei (Tensura)",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Zindan/Sistem", "Şehir Kurma", "Isekai", "Güzel"],
    "sites": []
  },
  {
    "title": "The Devil is a Part-Timer!",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Ters Isekai", "Komedi", "Mcdonalds", "Güzeldi"],
    "sites": []
  },
  {
    "title": "High School DxD / Shinmai Maou no Testament / Rosario to Vampire",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Ecchi", "Harem", "Şeytanlar/Güçlenme", "Güzeldi"],
    "sites": []
  },
  {
    "title": "Kaifuku Jutsushi no Yarinaoshi (Redo of Healer)",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Karanlık İntikam", "Şifacı", "Sınır İhlali", "Güzeldi"],
    "sites": []
  },
  {
    "title": "Dororo / Monster / Jigokuraku / Claymore / Kabaneri of the Iron Fortress",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Karanlık Atmosfer", "Tarihi/Gizem", "Aksiyon", "Güzel"],
    "sites": []
  },
  {
    "title": "Arifureta / Sekai Saikou no Ansatsusha / Netoge no Yome",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Isekai", "Overpowered", "Zindan/Oyun", "İyiydi"],
    "sites": []
  },
  {
    "title": "Dandadan / Jigokuraku / Kekkai Sensen / Mashle / Shangri-La Frontier",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Yeni Nesil Aksiyon", "Komedi", "Sistem/Oyun", "Güzel"],
    "sites": []
  },
  {
    "title": "Toradora! / Komi-san / Tomo-chan wa Onnanoko! / Nagatoro-san / Danshi Koukousei",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Slice of Life", "Okul", "Romantik Komedi", "İyiydi"],
    "sites": []
  },
  {
    "title": "Kuroshitsuji (Black Butler) / Tomodachi Game / Maou Gakuin / Plunderer",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Zeka Oyunları", "Demon Lord", "Gizem/Aksiyon"],
    "sites": []
  },
  {
    "title": "Dungeon Meshi / Tsuki ga Michibiku Isekai / Ishuzoku Reviewers",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Yemek/Fantezi", "Isekai", "Fantezi Irklar", "Güzel"],
    "sites": []
  },
  {
    "title": "Zom 100",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Zombi Kıyameti", "Renkler", "Özgürlük", "İyiydi"],
    "sites": []
  },
  {
    "title": "Yahari Ore no Seishun (Oregairu) / Kakegurui / Mirai Nikki",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Okul Psikolojisi", "Kumar", "Yandere/Hayatta Kalma", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Bocchi the Rock! / Chuunibyou / Shimoneta / School Days / To LOVE-Ru",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Sosyal Anksiyete", "Mizah/Ecchi", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Itai no wa Iya nanode Bougyoryoku (Bofuri) / Log Horizon",
    "type": "anime",
    "status": "dropped",
    "my_progress": "Bırakıldı",
    "personal_rating": "4.0/10",
    "tags": ["Oyun Dünyası", "Aşırı Savunma", "Sevmedim"],
    "sites": []
  },
  {
    "title": "My Neighbor Totoro",
    "type": "anime",
    "status": "dropped",
    "my_progress": "Bırakıldı",
    "personal_rating": "4.0/10",
    "tags": ["Studio Ghibli", "Yavaş Akış", "Sevmedim"],
    "sites": []
  },
  {
    "title": "Chainsaw Man",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Karanlık Shounen", "Denji", "Vahşet/Aksiyon"],
    "sites": []
  },
  {
    "title": "Demon Slayer",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Nefes Teknikleri", "Ufotable Animasyon", "Samuray"],
    "sites": []
  },
  {
    "title": "Fate Serisi",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Kutsal Kase Savaşı", "Hizmetkarlar", "Büyü/Strateji"],
    "sites": []
  },
  {
    "title": "JoJo's Bizarre Adventure",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Stand Güçleri", "Maskülen/Absürt", "Kült"],
    "sites": []
  },
  {
    "title": "Neon Genesis Evangelion",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Mecha", "Psikolojik Bunalım", "Felsefi", "Efsane"],
    "sites": []
  },
  {
    "title": "Death March kara Hajimaru Isekai Kyousoukyoku",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Isekai", "Yazılımcı/Sistem", "Harem"],
    "sites": []
  },
  {
    "title": "Isekai de Cheat Skill wo Te ni Shita Ore wa, Genjitsu Sekai wo mo Musou Suru",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Isekai", "Overpowered", "Gerçek Dünya / Diğer Dünya", "Gelişim", "İyiydi"],
    "sites": []
  },
  {
    "title": "Shuumatsu no Walküre (Record of Ragnarok)",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.5/10",
    "tags": ["Tanrılar vs İnsanlar", "Turnuva", "Saf Aksiyon", "Güzeldi"],
    "sites": []
  },
  {
    "title": "Shin no Nakama ja Nai to Yuusha no Party wo Oidasareta node, Henkyou de Slow Life suru Koto ni Shimashita",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Slow Life", "Kahraman Partisinden Kovulma", "Fantezi", "İyiydi"],
    "sites": []
  },
  {
    "title": "Otome Game Sekai wa Mob ni Kibishii Sekai desu",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Isekai", "Mecha / Otome Game", "Alaycı Ana Karakter", "İyiydi"],
    "sites": []
  },
  {
    "title": "Isekai Cheat Magician / Yuusha, Yamemasu",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Fantezi", "Büyü", "Eski Kahraman / Şeytan Kral Ordusu", "İyiydi"],
    "sites": []
  },
  {
    "title": "Undead Unluck / Tensei shitara Ken deshita",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Kılıç Olarak Isekai", "Özel Güçler / Kurallar", "Aksiyon", "İyiydi"],
    "sites": []
  },
  {
    "title": "Kinsou no Vermeil / Yuragi-sou no Yuuna-san / 100-man no Inochi",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Ecchi / Harem", "Şeytan / Doğaüstü", "Sistem / Görevler", "İyiydi"],
    "sites": []
  },
  {
    "title": "Genjitsu Shugi Yuusha no Oukoku Saikenki",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "8.0/10",
    "tags": ["Krallık Yönetimi", "Strateji", "Ekonomi / Siyaset", "Isekai", "İyiydi"],
    "sites": []
  },
  {
    "title": "The Daily Life of the Immortal King",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Donghua (Çin)", "Overpowered", "Okul", "Gizli Güç", "Eh İşte"],
    "sites": []
  },
  {
    "title": "The Faraway Paladin / Tondemo Skill de Isekai Hourou Meshi",
    "type": "anime",
    "status": "completed",
    "my_progress": "Tamamlandı",
    "personal_rating": "6.0/10",
    "tags": ["Isekai Yemek", "Reenkarnasyon / Mitoloji", "Eh İşte"],
    "sites": []
  },
  {
    "title": "Berserk",
    "type": "anime",
    "status": "planning",
    "my_progress": "İzlenecek",
    "personal_rating": "0.0/10",
    "tags": ["İzlenecek", "Karanlık Fantezi", "Guts", "Kült", "Vahşet / Trajedi"],
    "sites": []
  }
"""

with open("scripts/user_data_snippet.txt", "w", encoding="utf-8") as f:
    f.write(user_pasted_text)
print("Saved snippet.")
