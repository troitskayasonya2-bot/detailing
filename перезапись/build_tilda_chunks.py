#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка фрагментов для вставки в T123 Тильды (ограничение размера поля)."""

import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
BLOCKS = BASE / "blocks"
OUT = BASE / "tilda-7-files"


def t123_wrap(inner: str) -> str:
    inner_stripped = inner.rstrip() + "\n"
    return (
        '<div class="t123">\n'
        '    <div class="t-container_100 ">\n'
        '        <div class="t-width t-width_100 ">\n'
        f"{inner_stripped}"
        "        </div>\n"
        "    </div>\n"
        "</div>\n"
    )


def slice_lines(path: Path, start_1: int, end_1: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(True)
    return "".join(lines[start_1 - 1 : end_1])


def shorten_vimeo_iframes(html: str) -> str:
    """Короче src у Vimeo — та же фоновая подача, меньше символов на строку (лимиты T123)."""

    def repl(m: re.Match[str]) -> str:
        vid = m.group(1)
        return (
            "src=\"https://player.vimeo.com/video/"
            + vid
            + "?background=1&amp;autoplay=1&amp;muted=1&amp;loop=1&amp;controls=0\""
        )

    return re.sub(
        r'src="https://player\.vimeo\.com/video/(\d+)[^"]*"',
        repl,
        html,
    )


def prices_shell_after_tabs() -> str:
    """Закрытие блока после заголовка/вкладок прайса (без таблиц) — см. rec2197559101 ~469."""
    return (
        "                                </div>\n"
        "                            </section>\n"
        "                        </div>\n"
    )


# Дубль в блоке 16 на случай, если стили из файла 14 не подхватились или их перебивает Тильда
PRICES_SHELL_HINT_CSS = """<style>
/* Стрелка «Листайте вправо»: фиксированный размер, не на весь экран */
.pride-tilda #prices.prices .prices__scroll-hint {
    width: fit-content !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
.pride-tilda #prices.prices .prices__scroll-hint svg,
.pride-tilda #prices.prices .prices__scroll-hint-icon {
    width: 18px !important;
    height: 18px !important;
    max-width: 18px !important;
    max-height: 18px !important;
    min-width: 0 !important;
    display: block !important;
    flex-shrink: 0 !important;
    box-sizing: border-box !important;
}
@media (max-width: 768px) {
    .pride-tilda #prices.prices .prices__scroll-hint {
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        margin: 6px 0 6px !important;
    }
}
@media (min-width: 769px) {
    .pride-tilda #prices.prices .prices__scroll-hint {
        display: none !important;
    }
}
/* Ящики merge 17–22: Тильда иногда срезает атрибут hidden — не показывать доноров внизу страницы */
.pride-prices-merge-src {
    display: none !important;
}
</style>
"""


PRICES_TABS_DELEGATION = '''<script>
(function() {
document.addEventListener("DOMContentLoaded", function() {
    var pricesRoot = document.getElementById("prices");
    if (!pricesRoot || pricesRoot.getAttribute("data-pride-price-delegated") === "1") return;
    pricesRoot.setAttribute("data-pride-price-delegated", "1");
    pricesRoot.addEventListener("click", function(e) {
        var tab = e.target.closest(".prices__tab");
        if (!tab || !pricesRoot.contains(tab)) return;
        var targetId = tab.getAttribute("data-tab");
        if (!targetId) return;
        pricesRoot.querySelectorAll(".prices__tab").forEach(function(t) {
            t.classList.remove("active");
            t.removeAttribute("aria-current");
        });
        pricesRoot.querySelectorAll(".prices__panel").forEach(function(p) {
            p.classList.remove("active");
        });
        tab.classList.add("active");
        tab.setAttribute("aria-current", "true");
        var panel = document.getElementById(targetId);
        if (panel) panel.classList.add("active");
    });
});
})();
</script>'''


# Лишние section#prices (двойная вставка блока 16 или старый целый Zero рядом с 14–22)
PRICES_DEDUPE_EXTRA_SECTIONS = '''<script>
(function() {
function dedupeExtraPrices() {
    var secs = document.querySelectorAll("section#prices");
    if (secs.length < 2) return;
    for (var i = secs.length - 1; i >= 1; i--) {
        var sec = secs[i];
        var wrap = sec.closest(".pride-tilda");
        sec.remove();
        if (wrap && wrap.parentNode && !wrap.querySelector("section")) wrap.remove();
    }
}
function run() {
    setTimeout(dedupeExtraPrices, 0);
}
if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", run, { once: true });
else run();
window.addEventListener("load", function() { setTimeout(dedupeExtraPrices, 0); });
})();
</script>'''


def prices_merge_fragment(inner: str, box_id: str) -> str:
    inner_stripped = inner.rstrip() + "\n"
    script = f"""<script>
(function() {{
function merge() {{
    var root = document.getElementById("prices");
    var box = document.getElementById("{box_id}");
    if (!root || !box) return false;
    var c = root.querySelector(".container");
    if (!c) return false;
    while (box.firstChild) c.appendChild(box.firstChild);
    box.remove();
    return true;
}}

function mergeWithRetry(attempt) {{
    if (merge()) return;
    if (attempt >= 12) return;
    setTimeout(function() {{ mergeWithRetry(attempt + 1); }}, 180);
}}

if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", function() {{ mergeWithRetry(0); }}, {{ once: true }});
}} else {{
    mergeWithRetry(0);
}}

window.addEventListener("load", function() {{ mergeWithRetry(0); }}, {{ once: true }});
}})();
</script>
"""
    return (
        f"<!-- Часть прайса → #prices .container (ящик `{box_id}`) -->\n"
        f'<div id="{box_id}" class="pride-prices-merge-src" hidden style="display:none!important" aria-hidden="true">\n'
        f"{inner_stripped}"
        f"</div>\n"
        f"{script}"
    )


def strip_prices_tabs_from_main_js(html: str) -> str:
    """Убирает привязку вкладок прайса: панели появляются позже через merge."""
    needle = """                            // --- PRICES TABS ---
                            const priceTabs = document.querySelectorAll('.prices__tab');
                            const pricePanels = document.querySelectorAll('.prices__panel');

                            priceTabs.forEach(tab => {
                                tab.addEventListener('click', () => {
                                    const target = tab.dataset.tab;
                                    if (!target)
                                        return;
                                    priceTabs.forEach(t => {
                                        t.classList.remove('active');
                                        t.removeAttribute('aria-current');
                                    });
                                    pricePanels.forEach(p => p.classList.remove('active'));
                                    tab.classList.add('active');
                                    tab.setAttribute('aria-current', 'true');
                                    document.getElementById(target)?.classList.add('active');
                                });
                            });

"""
    if needle in html:
        return html.replace(needle, "")
    return html


def strip_accidental_footer(html: str) -> str:
    """Убирает хвост экспорта <!--footer--> / открытый <footer (без закрытия)."""
    out_lines: list[str] = []
    for line in html.splitlines(True):
        s = line.strip()
        if s.startswith("<!--footer-->"):
            continue
        if s.startswith("<footer"):
            continue
        out_lines.append(line)
    return "".join(out_lines)


def main() -> None:
    OUT.mkdir(exist_ok=True)

    intro = (
        "<!-- Порядок вставки — по номеру в имени файла (01→27). Карта Яндекса в сборку не входит. "
        "Прайс: 16–22 подряд (оболочка + фрагменты, merge во #prices); вкладки в 10 вырезаны, делегирование в 22. "
        "Куда что класть: 01 шапка · 02–06 герой одним разрезом rec2197556211 (меняете герой в исходнике — заново все 02–06) · "
        "07–09 стили B · 10 главный JS · 11–13 услуги (rec878 слой) · 14 секция услуг+стили локальные · 15 портфель+скрипт слайдера · "
        "16–22 прайс · 23 vertical-media · 24 этапы · 25 отзывы/FAQ/контакты · 26 попапы/скролл/наверх · 27 подвал. "
        "Точечное: только текст/фото первого экрана без правок CSS часто достаточно заменить 06 после пересборки. "
        "-->\n\n"
    )

    outputs: list[tuple[str, str]] = []

    # ----- 01 Header -----
    header = (BLOCKS / "rec2203792551.html").read_text(encoding="utf-8") + (
        BLOCKS / "rec2215701581.html"
    ).read_text(encoding="utf-8")
    outputs.append(("01-header.html", intro + "<!-- 01 — Шапка -->\n" + header))

    # ----- 02–06 Hero (rec2197556211) -----
    hero_lines = (BLOCKS / "rec2197556211.html").read_text(encoding="utf-8").splitlines(True)
    # Конец среза: exclusive; последняя строка — закрывающий </script> портфельного блока (~стр. 4369 rec2197556211).
    # Было [5:4349] — обрыв после resize, без orientationchange/load/MutationObserver/})();/</script> → незакрытый script и ломана вёрстка T123.
    inner = "".join(hero_lines[5:4369])
    after_open = inner.index("<style>") + len("<style>")
    style_close = inner.index("</style>", after_open)
    css_full = inner[after_open:style_close]
    rest_after_style = inner[style_close + len("</style>") :]
    css_lines = css_full.splitlines(True)

    def hidx(fl: int) -> int:
        return fl - 17

    css_a = "".join(css_lines[: hidx(1099)])
    css_b = "".join(css_lines[hidx(1099) : hidx(1839)])
    css_c = "".join(css_lines[hidx(1839) : hidx(3492)])
    css_d = "".join(css_lines[hidx(3492) :])
    head_css = inner[:after_open]

    hero_bodies = [
        (
            "02-hero-part1-css-to-portfolio.html",
            "<!-- Герой 1/5: шрифты + CSS до SERVICES -->\n" + head_css + css_a + "</style>\n",
        ),
        ("03-hero-part2-css-services-to-chb.html", "<!-- Герой 2/5 -->\n<style>\n" + css_b + "</style>\n"),
        ("04-hero-part3-css-chb-layer.html", "<!-- Герой 3/5 -->\n<style>\n" + css_c + "</style>\n"),
        ("05-hero-part4-css-mobile-fixes.html", "<!-- Герой 4/5 -->\n<style>\n" + css_d + "</style>\n"),
        (
            "06-hero-part5-html-scripts.html",
            "<!-- Герой 5/5 (блок Tilda rec2197556211 хвост): только #hero и скрипты. Не добавляйте сюда разметку #services / #prices / портфеля — иначе дубли и поломка дизайна. Картинку героя правьте здесь или в blocks/rec2197556211.html пересборкой. JS neutralizeMainGold работает только внутри #services. -->\n"
            + rest_after_style,
        ),
    ]
    outputs += [(n, t123_wrap(b)) for n, b in hero_bodies]

    # ----- 07–09 Styles B (rec2203804861) -----
    sb_lines = (BLOCKS / "rec2203804861.html").read_text(encoding="utf-8").splitlines(True)
    # Нечувствительно к смещениям строк: режем до строки перед <!-- nominify end -->
    sb_end_exclusive = next(
        (i for i, line in enumerate(sb_lines, start=1) if "<!-- nominify end -->" in line),
        len(sb_lines),
    )
    sb_inner = "".join(sb_lines[5:sb_end_exclusive - 1])
    p0 = sb_inner.index("<style>") + len("<style>")
    p1 = sb_inner.index("</style>", p0)
    sb_css_lines = sb_inner[p0:p1].splitlines(True)

    def sb_ix(fl: int) -> int:
        return fl - 9

    sba = "".join(sb_css_lines[: sb_ix(894)])
    sbb = "".join(sb_css_lines[sb_ix(894) : sb_ix(1470)])
    sbc = "".join(sb_css_lines[sb_ix(1470) :])
    sb_head = sb_inner[:p0]
    sb_tail = sb_inner[p1 + len("</style>") :]

    sb_bodies = [
        (
            "07-styles-b-part1-to-tire-pattern.html",
            "<!-- Стили B 1/4 -->\n" + sb_head + sba + "</style>\n",
        ),
        ("08-styles-b-part2-imported-blocks.html", "<!-- Стили B 2/4 -->\n<style>\n" + sbb + "</style>\n"),
        (
            "09-styles-b-part3-visual-refresh-plus-reviews-script.html",
            "<!-- Стили B 3/4 + скрипт отзывов -->\n<style>\n" + sbc + "</style>\n" + sb_tail,
        ),
    ]
    outputs += [(n, t123_wrap(b)) for n, b in sb_bodies]

    # ----- 10 Main JS (без вкладок прайса — панели подгружаются блоками 17–22) -----
    outputs.append(
        (
            "10-main-javascript.html",
            "<!-- Основной JS страницы (вкладки #prices — делегирование в файле 22) -->\n"
            + strip_prices_tabs_from_main_js((BLOCKS / "rec2203839051.html").read_text(encoding="utf-8")),
        )
    )

    # ----- 11–13 rec2197558781: CSS×2 + скрипт -----
    u78 = (BLOCKS / "rec2197558781.html").read_text(encoding="utf-8").splitlines(True)
    u78_inner = "".join(u78[5:2843])
    uo = u78_inner.index("<style>") + len("<style>")
    uc = u78_inner.index("</style>", uo)
    u78_css = u78_inner[uo:uc].splitlines(True)
    u78_css_a = "".join(u78_css[: 1461 - 8])
    u78_css_b = "".join(u78_css[1461 - 8 :])
    u78_head = u78_inner[:uo]
    u78_tail = u78_inner[uc + len("</style>") :]

    outputs += [
        (
            "11-services-layer-css-part1.html",
            t123_wrap(
                "<!-- Слой услуг (rec878): CSS, часть 1 -->\n" + u78_head + u78_css_a + "</style>\n"
            ),
        ),
        (
            "12-services-layer-css-part2.html",
            t123_wrap("<!-- Слой услуг (rec878): CSS, часть 2 -->\n<style>\n" + u78_css_b + "</style>\n"),
        ),
        (
            "13-services-layer-scripts.html",
            t123_wrap(
                "<!-- Слой услуг (rec878): скрипты (пересекается с блоком 10 — при дублях отключите один) -->\n"
                + u78_tail
            ),
        ),
    ]

    # ----- 14–15 Zero 9101 (rec2197559101): локальные стили + секции -----
    # Каждый T123 в Тильде — отдельный виджет: внутри должна быть полная разметка. Раньше 14 обрывался
    # на закрытии .services-grid, а «хвост» </section> жил в начале 15 — браузеру невалидно, парсер ломает дерево.
    # 14 — по строку с закрытием первого .pride-tilda после #services; 15 — только портфель + полный </script>.
    # После расширения 15 (до полного </script>) все диапазоны ниже сдвинуты:
    # оболочка прайса 494–521, фрагменты 522+, vertical-media 2150–2206.
    u91 = BLOCKS / "rec2197559101.html"
    u91_lines = u91.read_text(encoding="utf-8").splitlines(True)
    pride_wrappers = [
        i for i, line in enumerate(u91_lines, start=1) if '<div class="pride-tilda">' in line
    ]
    portfolio_wrapper_start = pride_wrappers[1]
    portfolio_start = next(
        i
        for i, line in enumerate(u91_lines, start=1)
        if '<section class="portfolio section section--alt" id="portfolio">' in line
    )
    prices_start = next(
        i
        for i, line in enumerate(u91_lines, start=1)
        if '<section class="prices section" id="prices">' in line
    )
    prices_wrapper_start = max(
        i
        for i, line in enumerate(u91_lines, start=1)
        if i < prices_start and '<div class="pride-tilda">' in line
    )
    # 14 — весь services до начала portfolio; 15 — portfolio до начала prices.
    services_styles_and_section = slice_lines(u91, 6, portfolio_wrapper_start - 1)
    portfolio_block = slice_lines(u91, portfolio_wrapper_start, prices_wrapper_start - 1)

    outputs += [
        (
            "14-section-services.html",
            "<!-- nominify + <style> (в т.ч. правила прайса) + секция #services до закрытия обёртки -->\n"
            + t123_wrap(services_styles_and_section),
        ),
        (
            "15-section-portfolio-slider-script.html",
            "<!-- Портфель + полный inline-скрипт слайдера (до </script>) -->\n" + t123_wrap(portfolio_block),
        ),
    ]

    # ----- 16–22 Прайс: оболочка + 6 скрытых фрагментов (перенос в #prices .container) -----
    prices_header = PRICES_SHELL_HINT_CSS + slice_lines(u91, 494, 521) + prices_shell_after_tabs()
    outputs.append(
        (
            "16-prices-shell-tabs.html",
            "<!-- Прайс: заголовок, вкладки (таблицы — в 17–22). Один раз на странице: не держите старый целый блок с #prices рядом с этой связкой. -->\n"
            + t123_wrap(prices_header),
        )
    )
    prices_slices: list[tuple[str, tuple[int, int]]] = [
        ("17-prices-frag-panel-wash.html", (522, 813)),
        ("18-prices-frag-panel-body.html", (814, 1065)),
        ("19-prices-frag-panel-protect.html", (1066, 1245)),
        ("20-prices-frag-panel-polish.html", (1246, 1497)),
        ("21-prices-frag-panel-salon.html", (1498, 1767)),
        ("22-prices-frag-tail-footnote-tabs-js.html", (1768, 2149)),
    ]
    ids = ["pprice-f02", "pprice-f03", "pprice-f04", "pprice-f05", "pprice-f06", "pprice-f07"]
    for (fname, lr), frag_id in zip(prices_slices, ids):
        chunk = slice_lines(u91, lr[0], lr[1])
        body = "<!-- см. сборщик → merge во #prices -->\n" + t123_wrap(prices_merge_fragment(chunk, frag_id))
        if fname == "22-prices-frag-tail-footnote-tabs-js.html":
            body += "\n<!-- Делегирование кликов по вкладкам прайса (после появления всех .prices__panel) -->\n"
            body += PRICES_TABS_DELEGATION + "\n"
            body += "<!-- Убрать дубли section#prices, если на странице два прайса (старый блок + новая сборка) -->\n"
            body += PRICES_DEDUPE_EXTRA_SECTIONS + "\n"
        outputs.append((fname, body))

    vertical_block = slice_lines(u91, 2150, 2206)
    outputs.append(
        (
            "23-section-vertical-media.html",
            "<!-- Секция #vertical-media (Vimeo укорочены) -->\n"
            + t123_wrap(shorten_vimeo_iframes(vertical_block)),
        )
    )

    # ----- 24–25 этапы | отзывы+FAQ+контакты -----
    u35 = BLOCKS / "rec2197559351.html"
    u35_lines = u35.read_text(encoding="utf-8").splitlines(True)
    u35_pride_wrappers = [
        i for i, line in enumerate(u35_lines, start=1) if '<div class="pride-tilda">' in line
    ]
    # 24 — только первый pride-tilda со stages; 25 начинается со второго pride-tilda (reviews).
    stages_only = "".join(u35_lines[6 - 1 : u35_pride_wrappers[1] - 1])
    # Нечувствительно к смещениям строк: до строки перед <!-- nominify end -->.
    u35_end_exclusive = next(
        (i for i, line in enumerate(u35_lines, start=1) if "<!-- nominify end -->" in line),
        len(u35_lines),
    )
    tail_reviews = "".join(u35_lines[u35_pride_wrappers[1] - 1 : u35_end_exclusive - 1])
    outputs += [
        (
            "24-section-stages-only.html",
            "<!-- Этапы работы (#stages) -->\n" + t123_wrap(stages_only),
        ),
        (
            "25-section-reviews-faq-contact.html",
            "<!-- Отзывы, FAQ, контакты -->\n" + t123_wrap(tail_reviews),
        ),
    ]

    widgets = strip_accidental_footer(
        (BLOCKS / "rec2210693821.html").read_text(encoding="utf-8")
        + (BLOCKS / "rec2210709011.html").read_text(encoding="utf-8")
        + (BLOCKS / "rec2210713401.html").read_text(encoding="utf-8")
        + (BLOCKS / "rec2197720901.html").read_text(encoding="utf-8")
        + (BLOCKS / "rec2197721931.html").read_text(encoding="utf-8")
    )
    outputs.append(
        (
            "26-popups-scroll-yclients-top.html",
            "<!-- Файл вставки №26 «попапы/скролл/наверх». Записи Tilda при склейке: rec2210693821 rec2210709011 rec2210713401 rec2197720901 rec2197721931. Ранее Yclients был отдельным блоком rec2242113141 (blocks/rec2242113141.html) — из склейки убран, скрипт там отключён. -->\n"
            + widgets,
        )
    )
    outputs.append(("27-footer.html", "<!-- Подвал -->\n" + (BLOCKS / "rec2203780251.html").read_text(encoding="utf-8")))

    for old in [
        "11-services-portfolio-prices-media.html",
        "12-stages-reviews-faq-contact.html",
        "13-popups-scroll-yclients-top.html",
        "14-footer.html",
        "16-section-prices.html",
        "17-section-vertical-media.html",
        "18-section-stages-only.html",
        "19-section-reviews-faq-contact.html",
        "18-stages-reviews-faq-contact.html",
        "19-popups-scroll-yclients-top.html",
        "20-footer.html",
        "20-popups-scroll-yclients-top.html",
        "21-footer.html",
    ]:
        p = OUT / old
        if p.exists():
            p.unlink()

    for name, content in outputs:
        (OUT / name).write_text(content, encoding="utf-8")

    print(f"OK: {len(outputs)} файлов → {OUT}")


if __name__ == "__main__":
    main()
