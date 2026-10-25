"""Settings thank-you popup + IHS/Reservation Relief pitch box (static checks)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["promo_pop_title", "promo_pop_p1", "promo_pop_p2", "promo_pop_p3", "promo_dont", "promo_close", "promo_web"]


def test_popup_markup_and_assets():
    html = (ROOT / "static/index.html").read_text(encoding="utf-8")
    assert 'id="promo-modal"' in html and 'role="dialog"' in html
    assert 'id="promo-dont-show"' in html
    assert html.count('id="ihsSisterPromo"') == 1
    assert "https://www.reservationrelief.com/" in html and "https://intelligenthospitalitysystems.com/" in html
    assert "/static/js/promo.js" in html
    for f in ("static/img/reservation-relief-logo.png", "static/img/ihs-logo.png", "static/js/promo.js"):
        assert (ROOT / f).is_file(), f
    # pitch box is the last thing in the Settings view
    setup = html[html.index('id="view-setup"'):]
    setup = setup[:setup.index("</section>")]
    assert setup.rstrip().endswith("</div>") and setup.rindex("ihsSisterPromo") > setup.rindex("setup-form")


def test_promo_strings_en_es():
    for lang in ("en", "es"):
        d = json.loads((ROOT / f"locales/{lang}.json").read_text(encoding="utf-8"))
        for k in KEYS:
            assert d.get(k), (lang, k)
        assert "$300" in d["promo_pop_p2"]
