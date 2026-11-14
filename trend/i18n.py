"""English and Turkish texts for the app, plus number formatting per language.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. English is the default language (the submission language);
Turkish is offered for local readers.
"""
from __future__ import annotations

from trend.variables import Variable

LANGUAGES = {"en": "EN", "tr": "TR"}

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "eyebrow": "NASA Earth data · Statistical investigation",
        "title": "Earth System Trend Detective",
        "subtitle": (
            "Pick a clue and a period. The detective checks NASA's satellite records and tells you "
            "whether the change is real or could just be chance."
        ),
        "language": "Language",
        "region_label": "Region under investigation",
        "no_data_region": "No evidence has been collected for this region yet.",
        "step1": "Step 1 · Choose a clue",
        "step1_caption": "Each card is one measurement from NASA Earth data over its full record.",
        "per_decade": "per decade",
        "evidence_pending": "Evidence pending",
        "investigate": "Investigate",
        "selected": "Selected",
        "case_label": "Case file · {region} · {variable}",
        "question": "Is the {subject} in {region} changing?",
        "question_body": "**{name}:** {definition} Each point on the chart is one {subject}.",
        "step2": "Step 2 · Choose the period",
        "period_label": "Years to investigate",
        "too_short": (
            "Not enough evidence: a trend test needs at least {min} complete years, and this period "
            "has {n}. Pick a longer period."
        ),
        "step3": "Step 3 · Real or chance?",
        "headline_up": "Unlikely to be chance: a real upward trend",
        "headline_down": "Unlikely to be chance: a real downward trend",
        "headline_chance": "Could be chance: no clear trend",
        "meter_question": (
            "If there were no real trend, how often would a trend this strong appear just by chance?"
        ),
        "meter_left": "Unlikely to be chance",
        "meter_right": "Could easily be chance",
        "meter_threshold": "5% line",
        "chance_tiny": "less than 0.1% of the time",
        "chance_value": "about {pct}% of the time",
        "how_much": "HOW MUCH",
        "total_change": "TOTAL CHANGE",
        "evidence_used": "EVIDENCE USED",
        "years_count": "{n} complete years",
        "ci": "95% CI {low} to {high}",
        "along_trend": "along the trend line",
        "verdict_sig": (
            "In **{region}**, the {subject} **{verb} by about {rate} {unit} per decade** from {start} "
            "to {end}, about {total} {unit} in total along the trend line. If there were no real "
            "trend, a trend this strong would appear by chance {chance}."
        ),
        "verb_up": "rose",
        "verb_down": "fell",
        "verdict_nosig": (
            "In **{region}**, **no significant trend was detected** in the {subject} from {start} to "
            "{end}. The values go up and down, but the overall direction cannot be told apart from "
            "natural year-to-year variation ({p})."
        ),
        "warn_short": (
            "Only {n} years of data. Trend tests are less reliable with fewer than {rec} years."
        ),
        "step4": "Step 4 · The evidence",
        "based_on": "Based on {n} complete years ({start} to {end}).",
        "not_used": " Not used because incomplete: {years}.",
        "step5": "Step 5 · The second witness",
        "witness_agrees": (
            "✅ **The second witness agrees:** the {method} test, which does not assume a straight "
            "line, finds {found} ({p}; Sen's slope {sen} {unit} per decade)."
        ),
        "witness_disagrees": (
            "⚠️ **The second witness disagrees:** the {method} test, which does not assume a "
            "straight line, finds {found} ({p}; Sen's slope {sen} {unit} per decade). "
            "Treat this verdict with caution."
        ),
        "found_increasing": "an increasing trend",
        "found_decreasing": "a decreasing trend",
        "found_none": "no significant trend",
        "cross_exam": (
            "Cross-examination: leaving out the newest year ({year}), whose data can still be revised, "
            "gives {rate} {unit} per decade ({p}, {sig})."
        ),
        "significant": "significant",
        "not_significant": "not significant",
        "case_notes": "Case notes",
        "keep_in_mind": "Keep in mind",
        "monthly_title": "Monthly values (with the seasonal cycle)",
        "monthly_caption": (
            "Monthly values still include the seasonal cycle, so they swing up and down every year."
        ),
        "table_title": "Data table and downloads",
        "months_used": "Months used",
        "source_recorded": "Source recorded when the data was fetched: {source}",
        "dl_annual": "Download the annual series (CSV)",
        "dl_results": "Download the case results (CSV)",
        "methods_title": "How the detective works (methods and limitations)",
        "data_label": "Data",
        "footer": (
            "Team Avni · NASA Space Apps Challenge 2026 · Built with AI assistance (Claude by "
            "Anthropic); see the README for details. Not affiliated with or endorsed by NASA."
        ),
        "band_name": "95% confidence band of the trend line",
        "trend_name": "Linear trend ({rate})",
        "month_axis": "Month",
    },
    "tr": {
        "eyebrow": "NASA Dünya verisi · İstatistiksel soruşturma",
        "title": "Dünya Sistemi Trend Dedektifi",
        "subtitle": (
            "Bir ipucu ve bir dönem seç. Dedektif NASA'nın uydu kayıtlarını inceler ve değişimin "
            "gerçek mi, yoksa tesadüf mü olduğunu söyler."
        ),
        "language": "Dil",
        "region_label": "İncelenen bölge",
        "no_data_region": "Bu bölge için henüz delil toplanmadı.",
        "step1": "1. adım · Bir ipucu seç",
        "step1_caption": "Her kart, NASA Dünya verisinden bir ölçümü tüm kayıt boyunca gösterir.",
        "per_decade": "on yılda",
        "evidence_pending": "Delil bekleniyor",
        "investigate": "İncele",
        "selected": "Seçili",
        "case_label": "Dava dosyası · {region} · {variable}",
        "question": "{region} bölgesinde {subject} değişiyor mu?",
        "question_body": "**{name}:** {definition} Grafikteki her nokta: {subject}.",
        "step2": "2. adım · Dönemi seç",
        "period_label": "İncelenecek yıllar",
        "too_short": (
            "Yeterli delil yok: trend testi için en az {min} tam yıl gerekiyor, bu dönemde {n} yıl "
            "var. Daha uzun bir dönem seç."
        ),
        "step3": "3. adım · Gerçek mi, tesadüf mü?",
        "headline_up": "Tesadüf olması çok zor: gerçek bir artış trendi",
        "headline_down": "Tesadüf olması çok zor: gerçek bir azalış trendi",
        "headline_chance": "Tesadüf olabilir: belirgin bir trend yok",
        "meter_question": (
            "Gerçek bir trend olmasaydı, bu kadar güçlü bir trend ne sıklıkla tesadüfen ortaya çıkardı?"
        ),
        "meter_left": "Tesadüf olması zor",
        "meter_right": "Kolayca tesadüf olabilir",
        "meter_threshold": "%5 sınırı",
        "chance_tiny": "%0,1'den az",
        "chance_value": "yaklaşık %{pct}",
        "how_much": "NE KADAR",
        "total_change": "TOPLAM DEĞİŞİM",
        "evidence_used": "KULLANILAN DELİL",
        "years_count": "{n} tam yıl",
        "ci": "%95 güven aralığı: {low} ile {high}",
        "along_trend": "trend çizgisi boyunca",
        "verdict_sig": (
            "**{region}** bölgesinde {subject}, {start}–{end} arasında **on yılda yaklaşık {rate} "
            "{unit} {verb}**; trend çizgisi boyunca toplam yaklaşık {total} {unit}. Gerçek bir trend "
            "olmasaydı, bu kadar güçlü bir trendin tesadüfen ortaya çıkma ihtimali {chance} olurdu."
        ),
        "verb_up": "arttı",
        "verb_down": "azaldı",
        "verdict_nosig": (
            "**{region}** bölgesinde {subject} için {start}–{end} arasında **anlamlı bir trend tespit "
            "edilmedi**. Değerler inip çıkıyor, ama genel yön doğal yıldan yıla değişimden ayırt "
            "edilemiyor ({p})."
        ),
        "warn_short": (
            "Sadece {n} yıllık veri var. {rec} yıldan kısa dönemlerde trend testleri daha az güvenilir."
        ),
        "step4": "4. adım · Delil",
        "based_on": "{n} tam yıla dayanıyor ({start}–{end}).",
        "not_used": " Eksik olduğu için kullanılmadı: {years}.",
        "step5": "5. adım · İkinci tanık",
        "witness_agrees": (
            "✅ **İkinci tanık doğruluyor:** düz bir çizgi varsaymayan {method} testinin sonucu: "
            "{found} ({p}; Sen eğimi on yılda {sen} {unit})."
        ),
        "witness_disagrees": (
            "⚠️ **İkinci tanık doğrulamıyor:** düz bir çizgi varsaymayan {method} testinin sonucu: "
            "{found} ({p}; Sen eğimi on yılda {sen} {unit}). Bu hükme temkinli yaklaş."
        ),
        "found_increasing": "artan trend",
        "found_decreasing": "azalan trend",
        "found_none": "anlamlı trend yok",
        "cross_exam": (
            "Çapraz sorgu: verisi henüz değişebilecek en yeni yılı ({year}) çıkarınca sonuç on yılda "
            "{rate} {unit} ({p}, {sig})."
        ),
        "significant": "anlamlı",
        "not_significant": "anlamlı değil",
        "case_notes": "Dava notları",
        "keep_in_mind": "Dikkat edilecekler",
        "monthly_title": "Aylık değerler (mevsim döngüsüyle)",
        "monthly_caption": "Aylık değerlerde mevsim döngüsü hâlâ var, bu yüzden her yıl inip çıkıyorlar.",
        "table_title": "Veri tablosu ve indirme",
        "months_used": "Kullanılan ay",
        "source_recorded": "Veri çekilirken kaydedilen kaynak: {source}",
        "dl_annual": "Yıllık seriyi indir (CSV)",
        "dl_results": "Dava sonuçlarını indir (CSV)",
        "methods_title": "Dedektif nasıl çalışır? (yöntem ve sınırlamalar)",
        "data_label": "Veri",
        "footer": (
            "Avni Takımı · NASA Space Apps Challenge 2026 · Yapay zekâ (Anthropic'in Claude'u) "
            "yardımıyla geliştirildi; ayrıntılar README'de. NASA ile bağlantılı değildir ve NASA "
            "tarafından onaylanmamıştır."
        ),
        "band_name": "Trend çizgisinin %95 güven bandı",
        "trend_name": "Doğrusal trend ({rate})",
        "month_axis": "Ay",
    },
}

STATUS: dict[str, dict[str, tuple[str, str]]] = {
    "en": {
        "confirmed": ("Confirmed", "A real trend: both tests agree."),
        "disputed": ("Disputed", "The headline test sees a trend, the second witness does not."),
        "noevidence": ("No evidence", "No significant trend detected."),
        "weak": ("Weak clue", "Only the second witness sees a trend."),
        "open": ("Open case", "Evidence still being collected."),
    },
    "tr": {
        "confirmed": ("Kanıtlandı", "Gerçek bir trend: iki test de aynı fikirde."),
        "disputed": ("Tartışmalı", "Ana test trend görüyor, ikinci tanık görmüyor."),
        "noevidence": ("Delil yok", "Anlamlı bir trend tespit edilmedi."),
        "weak": ("Zayıf ipucu", "Trendi sadece ikinci tanık görüyor."),
        "open": ("Açık dosya", "Deliller hâlâ toplanıyor."),
    },
}

REGION_NAMES = {"tr": {"colorado": "Colorado, ABD"}}

VARIABLE_TEXT: dict[str, dict[str, dict]] = {
    "tr": {
        "air_temperature": {
            "name": "Hava sıcaklığı",
            "definition": "Yerden yaklaşık 2 metre yükseklikteki havanın ne kadar sıcak olduğu.",
            "annual_label": "Yıllık ortalama hava sıcaklığı",
            "unit": "°C",
            "annual_unit": "°C",
            "year_axis_label": "Yıl",
            "caveats": [
                "Reanaliz verisidir: milyonlarca gözlemle birleştirilmiş bir hava modeli, yaklaşık "
                "50 km'lik ızgara.",
                "NASA POWER'daki en yeni aylar neredeyse gerçek zamanlı bir üründen gelebilir ve "
                "sonradan düzeltilebilir.",
            ],
        },
        "snowfall": {
            "name": "Kar yağışı",
            "definition": "Ne kadar kar yağdığı; eridiğinde oluşturacağı su yüksekliği olarak ölçülür.",
            "annual_label": "Su yılı (Ekim–Eylül) toplam kar yağışı",
            "unit": "ayda mm su",
            "annual_unit": "mm su",
            "year_axis_label": "Su yılı (Ekim–Eylül, bitiş yılıyla adlandırılır)",
            "caveats": [
                "Bu kar yağışı MERRA-2 reanalizinden gelir (gözlemlerle yönlendirilen bir hava "
                "modeli); doğrudan kar ölçümü ya da kar derinliği değildir.",
                "Reanaliz trendleri, on yıllar içinde gözlem sistemindeki değişimleri de kısmen "
                "yansıtabilir.",
                "NASA POWER'daki en yeni aylar neredeyse gerçek zamanlı bir üründen gelebilir ve "
                "sonradan düzeltilebilir.",
            ],
        },
        "no2": {
            "name": "Hava kirliliği (NO₂)",
            "definition": (
                "Atmosferin alt katmanındaki azot dioksit; çoğunlukla taşıtlardan, santrallerden ve "
                "sanayiden gelen bir gaz."
            ),
            "annual_label": "Yıllık ortalama troposferik NO₂ sütunu",
            "unit": "10¹⁵ molekül/cm²",
            "annual_unit": "10¹⁵ molekül/cm²",
            "year_axis_label": "Yıl",
            "caveats": [
                "Eyalet genelindeki ortalama kırsal alanların etkisinde kalır, bu yüzden şehir "
                "kirliliği seyrelir.",
                "OMI aletindeki 'satır anomalisi' kullanılabilir ölçüm sayısını azaltır.",
                "2020'de COVID-19 salgınındaki azalan faaliyetle bağlantılı bir düşüş var.",
                "OMI aleti yaşlanıyor ve Aura uydusunun yörüngesi son yıllarda kayıyor; yaklaşık "
                "2022 sonrası değişimlere ekstra temkinle bak.",
            ],
        },
        "ndvi": {
            "name": "Bitki yeşilliği (NDVI)",
            "definition": (
                "Bitkilerin ne kadar yeşil ve yoğun olduğu; -1 ile 1 arasında bir ölçek, yüksek değer "
                "daha fazla yeşil bitki demek."
            ),
            "annual_label": "Büyüme mevsimi (Mayıs–Eylül) ortalama NDVI",
            "unit": "NDVI (birimsiz)",
            "annual_unit": "NDVI",
            "year_axis_label": "Yıl",
            "caveats": [
                "Terra uydusunun yörüngesi yaklaşık 2020'den beri kayıyor; bu, son değerleri biraz "
                "etkileyebilir.",
            ],
        },
    }
}

METHODS = {
    "en": """
- **Area average:** the value for {region} is the average of all data grid cells whose centres lie
  inside or on the edge of the region's box, weighted by the cosine of latitude. Cells centred on
  the edge reach about a quarter of a degree beyond the box.
- **One value per year:** monthly values are combined into one value per year, which removes the
  seasonal cycle. A year is used only if all of its months are available.
- **Headline test:** a straight line is fitted with ordinary least squares (OLS). We report its
  slope, the 95% confidence interval of the slope and the p-value of a two-sided t-test. The
  **p-value** is the chance of seeing a trend at least this strong if there were really no trend.
  We call a trend significant ("unlikely to be chance") when p < 0.05.
- **Year-to-year persistence:** when a year's departure from the trend line tends to be followed by
  a similar departure (positive autocorrelation), the uncertainty is widened using an effective
  sample size (Santer et al., 2000), so the result is not overconfident.
- **Second witness:** the Mann-Kendall test checks for a steady rise or fall without assuming a
  straight line; Sen's slope is a robust estimate of the rate. If the residuals are correlated from
  one year to the next, the Hamed-Rao corrected version is used.
- **Stamps:** *Confirmed* = significant and the second witness agrees; *Disputed* = significant but
  the second witness disagrees; *No evidence* = no significant trend; *Weak clue* = only the second
  witness sees a trend.
- **Total change** is the slope multiplied by the number of years, not the last value minus the first.
- **Confidence band:** the shaded band is the 95% confidence band of the fitted line, not a range for
  individual years.
- **Short periods:** at least {min_years} years are required; fewer than 20 years gives a warning.
- **Many tests:** if you test many measurements, regions and periods, about 1 in 20 tests can look
  significant by chance alone.
- **No significant trend detected** does not mean "no change"; a longer record may reveal one.
""",
    "tr": """
- **Bölge ortalaması:** {region} değeri, merkezi bölge kutusunun içinde ya da kenarında kalan tüm
  veri ızgara hücrelerinin enlemin kosinüsüyle ağırlıklandırılmış ortalamasıdır. Kenarda merkezlenen
  hücreler kutunun yaklaşık çeyrek derece dışına uzanır.
- **Yılda tek değer:** aylık değerler her yıl için tek bir değerde birleştirilir; böylece mevsim
  döngüsü ortadan kalkar. Bir yıl yalnızca tüm ayları mevcutsa kullanılır.
- **Ana test:** en küçük kareler yöntemiyle (OLS) düz bir çizgi oturtulur. Eğimi, eğimin %95 güven
  aralığını ve iki yönlü t-testinin p-değerini veririz. **p-değeri**, gerçekte hiç trend yokken en
  az bu kadar güçlü bir trend görme ihtimalidir. p < 0,05 olduğunda trendi anlamlı ("tesadüf olması
  zor") kabul ederiz.
- **Yıldan yıla süreklilik:** bir yılın trend çizgisinden sapması, ardından gelen yılda benzer bir
  sapmayla devam ediyorsa (pozitif otokorelasyon), belirsizlik etkin örneklem büyüklüğüyle büyütülür
  (Santer ve ark., 2000); böylece sonuç olduğundan iddialı çıkmaz.
- **İkinci tanık:** Mann-Kendall testi, düz bir çizgi varsaymadan istikrarlı bir artış ya da azalış
  olup olmadığına bakar; Sen eğimi, değişim hızının sağlam bir tahminidir. Artıklar yıldan yıla
  ilişkiliyse Hamed-Rao düzeltmeli versiyonu kullanılır.
- **Damgalar:** *Kanıtlandı* = anlamlı ve ikinci tanık doğruluyor; *Tartışmalı* = anlamlı ama ikinci
  tanık doğrulamıyor; *Delil yok* = anlamlı trend yok; *Zayıf ipucu* = trendi sadece ikinci tanık
  görüyor.
- **Toplam değişim**, eğimin yıl sayısıyla çarpımıdır; son değer eksi ilk değer değildir.
- **Güven bandı:** gölgeli bant, oturtulan çizginin %95 güven bandıdır; tek tek yılların aralığı
  değildir.
- **Kısa dönemler:** en az {min_years} yıl gerekir; 20 yıldan kısa dönemlerde uyarı verilir.
- **Çok sayıda test:** çok sayıda ölçüm, bölge ve dönem test edersen, yaklaşık her 20 testten biri
  sadece tesadüfen anlamlı görünebilir.
- **Anlamlı trend tespit edilmedi** demek "değişim yok" demek değildir; daha uzun bir kayıt bir trend
  ortaya çıkarabilir.
""",
}


def t(lang: str, key: str, **values) -> str:
    """Translated text for ``key``, falling back to English."""
    text = TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"][key])
    return text.format(**values) if values else text


def status_text(lang: str, status: str) -> tuple[str, str]:
    return STATUS.get(lang, STATUS["en"])[status]


def region_name(lang: str, region_key: str, default: str) -> str:
    return REGION_NAMES.get(lang, {}).get(region_key, default)


def variable_text(lang: str, variable: Variable) -> dict:
    """Display texts for a variable in the chosen language (English comes from the catalog)."""
    english = {
        "name": variable.name,
        "definition": variable.definition,
        "annual_label": variable.annual_label,
        "unit": variable.unit,
        "annual_unit": variable.annual_unit,
        "year_axis_label": variable.year_axis_label,
        "caveats": list(variable.caveats),
    }
    return {**english, **VARIABLE_TEXT.get(lang, {}).get(variable.key, {})}


def num(value: float, lang: str, decimals: int = 2, signed: bool = False) -> str:
    """Format a number with a decimal comma in Turkish and a decimal point in English."""
    text = f"{value:+.{decimals}f}" if signed else f"{value:.{decimals}f}"
    return text.replace(".", ",") if lang == "tr" else text


def p_phrase(p: float, lang: str) -> str:
    """'p < 0.001' or 'p = 0.046', with a decimal comma in Turkish."""
    if p < 0.001:
        return "p < 0,001" if lang == "tr" else "p < 0.001"
    return f"p = {num(p, lang, 3)}"


def chance_phrase(p: float, lang: str) -> str:
    """How often a trend this strong would appear by chance, in words."""
    if p < 0.001:
        return t(lang, "chance_tiny")
    return t(lang, "chance_value", pct=num(p * 100, lang, 1))


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]
