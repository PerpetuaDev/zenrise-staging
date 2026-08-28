/**
 * Zenrise — language switcher + site-wide translation.
 *
 * Mark anything translatable in your HTML with one of:
 *   data-i18n="key"             — replaces textContent
 *   data-i18n-html="key"        — replaces innerHTML (for strings with markup)
 *   data-i18n-placeholder="key" — replaces an input's placeholder
 *   data-i18n-title="key"       — replaces document.title (on the <title> element)
 *
 * Then add the matching key under each language in DICT below.
 *
 * Choice persists across pages via localStorage('zenrise-lang').
 */
(function () {
  var KEY = 'zenrise-lang';

  var DICT = {
    en: {
      // language switcher
      langLabel: 'english',
      english: 'English',
      japanese: '日本語',
      lang_menu_header: 'Language',

      // nav (shared)
      nav_home: 'home',
      nav_tours: 'our tours',
      // contact region-card names (referenced by contact.html)
      home_dest_kamakura_name: 'Kamakura',
      home_dest_enoshima_name: 'Enoshima',
      home_dest_yokohama_name: 'Yokohama',
      home_dest_fujisawa_name: 'Other Destinations',
      nav_about: 'about us',
      nav_news: 'news',
      nav_contact: 'contact',

      // tours page
      tours_title: 'Our Tours — Zenrise',
      tours_h1: 'Our<br/>tours.',
      tours_lede: 'Original tours through the Kamakura area — researched, walked, and written by us, then led at your pace.',
      tours_filter_label: 'Browse by area',
      tours_area_all: 'All areas',
      tours_area_kamakura: 'Kamakura',
      tours_area_enoshima: 'Enoshima',
      tours_area_yokohama: 'Yokohama',
      tours_filter_label_theme: 'Browse by experience',
      tours_theme_temples: 'Temples & Shrines',
      tours_theme_culture: 'Culture',
      tours_theme_arts: 'Arts & Craft',
      tours_theme_food: 'Food & Drink',
      tours_theme_walking: 'Walking',
      tours_theme_nature: 'Nature & Views',
      tours_theme_cycling: 'Cycling',
      tours_len_half: 'Half-day',
      tours_len_full: 'Full-day',
      tours_len_both: 'Full / Half-day',
      tours_cta_h: 'Looking for something<br/>of your own?',
      tours_cta_p: 'Multi-day itineraries and days built around a single interest — designed around you, not a route.',
      tours_cta_link: 'Plan a bespoke journey',

      // home — tours + news sections
      home_tours_title: 'Our tours',
      home_tours_more: 'All tours',
      home_tours_cta: 'View this tour',
      home_news_title: 'News & stories',
      home_news_more: 'All news',
      home_news_1_title: 'A day away from Tokyo',
      home_news_1_sub: 'A bus tour through Kamakura & Enoshima',
      home_news_2_title: 'Inside the sumo ring',
      home_news_2_sub: 'A show & experience in Shinjuku',
      home_news_3_title: 'Fuji to Hakone',
      home_news_3_sub: 'And the ride home by Shinkansen',

      // tour detail — shared
      tours_back: 'All tours',
      td_f_tour: 'Tour', td_f_area: 'Area', td_f_format: 'Format',
      td_f_length: 'Length', td_f_group: 'Group', td_f_from: 'From',
      td_included: 'Included',
      td_notinc: 'Not included',
      td_bring: 'What to bring',
      td_know: 'Good to know',
      td_book_heading: 'Book your spot',
      td_route: 'The route.',
      td_other: 'Other info.',
      td_other_terms: 'Cancellation, insurance and payment terms in full',
      td_cta_h: 'Walk it with us.',
      td_cta_p: 'Tell us your dates and we\u2019ll come back within two working days with the mornings we have open. Printed pamphlet included, English and Japanese.',
      td_cta_link: 'Book this tour',
      td_prep_label: 'In preparation',
      td_prep_p1: 'The pamphlet for this tour is still being written \u2014 we walk each route several times before we publish it.',
      td_prep_p2: 'Write to us in the meantime and we\u2019ll send the current itinerary by email, along with the dates we have open.',
      td_prep_cta: 'Write to us',

      // tour detail — No. 04

      // tour detail — in-preparation tours

      // footer (shared across pages)
      footer_tagline: 'Quiet, locally-led journeys through the <br class="brk"/>lesser-known corners of Japan.',
      footer_visit: 'Office',
      footer_contact: 'Contact',
      footer_follow: 'Follow',
      footer_newsletter: 'Newsletter',
      footer_address: 'me-labo4, Sophiale Minamifujisawa #101<br/>10-11 Minamifujisawa, Fujisawa<br/>Kanagawa, 251-0055, Japan',
      footer_copyright: '© 2026 Intercommunicate K. K.',
      footer_terms: 'Terms',
      footer_instagram: 'Instagram',
      footer_youtube: 'YouTube',
      footer_tiktok: 'TikTok',

      // terms page (legal notice, cancellation policy & tour insurance)
      terms_title: 'Booking Terms — Zenrise',
      terms_h1: 'Terms &amp;<br/>conditions.',
      terms_legal_label: 'Disclosure',
      terms_legal_h2: 'Legal Notice.',
      terms_legal_note: 'Disclosure under Japan’s Specified Commercial Transactions Act.',
      terms_legal_biz: 'Business Name',
      terms_legal_biz_v: 'Intercommunicate K.K. / Zenrise',
      terms_legal_rep: 'Representative',
      terms_legal_rep_v: 'Akari Usuda',
      terms_legal_mgr: 'Certified Domestic Travel Services Manager',
      terms_legal_mgr_v: 'Kentaro Usuda',
      terms_legal_addr: 'Address',
      terms_legal_addr_v: 'me-labo4, Sophiale Minamifujisawa #101<br/>10-11 Minamifujisawa, Fujisawa<br/>Kanagawa, 251-0055, Japan',
      terms_legal_email: 'Email',
      terms_legal_email_v: 'hello@zenrise.jp',
      terms_legal_phone: 'Phone Number',
      terms_legal_phone_v: 'Disclosed promptly upon request.',
      terms_legal_url: 'Website',
      terms_legal_url_v: 'https://zenrise.jp',
      terms_legal_pay: 'Payment Methods',
      terms_legal_pay_v: 'Credit card<br/>Bank transfer (transfer fees are borne by the customer)<br/>PayPal',
      terms_legal_paydl: 'Payment Deadline',
      terms_legal_paydl_v: 'Credit card / PayPal: processed immediately — the charge date follows your card issuer’s or PayPal’s terms.<br/><br/>Bank transfer: payment within 7 days of booking.<br/><br/>For bookings made 7 days or less before the tour date, bank transfer is not available — payment is by credit card or PayPal for instant confirmation.',
      terms_legal_delivery: 'Service Delivery',
      terms_legal_delivery_v: 'Provided on the scheduled date and time of the booked tour.',
      terms_cancel_label: 'Cancellation',
      terms_cancel_h2: 'Cancellation & Changes.',
      terms_cancel_intro: 'If you cancel your booking for personal reasons, the following cancellation fees apply, in accordance with the Standard Travel Agency Terms and Conditions.',
      terms_cancel_sub: 'Day trips & private tours',
      terms_cancel_li1: 'Up to 11 days before the tour — free of charge',
      terms_cancel_li2: '10 to 8 days before — up to 20% of the tour fee',
      terms_cancel_li3: '7 to 2 days before — up to 30% of the tour fee',
      terms_cancel_li4: 'The day before the tour — up to 40% of the tour fee',
      terms_cancel_li5: 'On the tour day, before departure — up to 50% of the tour fee',
      terms_cancel_li6: 'After departure, or no-show — 100% of the tour fee',
      terms_cancel_costs: 'Even for a same-day cancellation before departure, any individual costs already arranged on your behalf — same-day taxi cancellation fees, facility hire, pre-purchased tickets and similar out-of-pocket expenses — are charged in full, in addition to the cancellation fee above.',
      terms_cancel_refund: 'If a tour is cancelled by the organizer due to severe weather or other unforeseen circumstances, a full refund will be issued.',
      terms_ins_label: 'Insurance',
      terms_ins_h2: 'Tour Insurance.',
      terms_ins_intro: 'We are a member of the Japan Ecotourism Society. To keep our guests safe, specialized ecotour insurance — including domestic travel accident insurance and premises liability insurance — is included in your tour fee.',
      terms_ins_cov_h: 'Coverage limits',
      terms_ins_li1: 'Death or permanent disability — ¥5,000,000',
      terms_ins_li2: 'Hospitalization benefit — ¥5,000 per day',
      terms_ins_li3: 'Outpatient benefit — ¥3,000 per day',
      terms_ins_li4: 'Surgery benefit — 10× the daily benefit during hospitalization; 5× for other surgeries',
      terms_ins_li5: 'Liability insurance — up to ¥100,000,000 (no deductible)',
      terms_ins_excl_h: 'Liability & exclusions',
      terms_ins_excl_1: 'This insurance applies to day tours only, including international visitors. Overnight tours, and accidents or injuries that occur outside the tour itinerary — before the meeting time or after dismissal — are not covered.',
      terms_ins_excl_2: 'The insurance also does not cover the aggravation of pre-existing medical conditions, injuries caused by willful misconduct or gross negligence, or the loss, theft or damage of personal belongings such as smartphones and cameras. Intercommunicate K.K. / Zenrise accepts no liability for these items — we strongly recommend that overseas participants arrange their own travel insurance before departure.',
      terms_priv_label: 'Privacy',
      terms_priv_h2: 'Privacy Policy.',
      terms_priv_intro: 'Intercommunicate K.K. / Zenrise (“we”) handles personal information in accordance with Japan’s Act on the Protection of Personal Information and related guidelines, as set out below.',
      terms_priv_h3_collect: 'Information we collect',
      terms_priv_p_collect: 'When you send an enquiry or booking request we receive the details you provide — your name, email address, where you are travelling from, preferred dates, group size, and anything you choose to share with us such as dietary needs, mobility considerations or interests — together with our correspondence with you.',
      terms_priv_h3_use: 'Purposes of use',
      terms_priv_p_use: 'We use this information to reply to your enquiry, to plan and operate your booked tour, to process payment and insurance enrolment, to keep you safe during the tour, and to meet our legal obligations. We do not use it for advertising or marketing without your consent.',
      terms_priv_h3_share: 'Third-party provision & outsourcing',
      terms_priv_p_share: 'We do not provide personal information to third parties without your prior consent, except where required by law. Where needed to operate your tour, we share the minimum necessary details with the businesses involved — restaurants, activity providers, the insurer and the like — and supervise any entrusted handling appropriately.',
      terms_priv_h3_safe: 'Safety management',
      terms_priv_p_safe: 'We take appropriate measures to prevent the leakage, loss or damage of personal information, and keep it only for as long as the purposes above require.',
      terms_priv_h3_rights: 'Disclosure, correction & deletion',
      terms_priv_p_rights: 'You may request the disclosure, correction, suspension of use or deletion of your personal information at any time by writing to hello@zenrise.jp. After confirming your identity, we will respond promptly in accordance with the law.',
      terms_priv_h3_contact: 'Changes & contact',
      terms_priv_p_contact: 'This policy may be revised from time to time; any changes will be published on this page. Enquiries about personal information: Intercommunicate K.K. / Zenrise — hello@zenrise.jp.',

      // news index
      news_title: 'News — Zenrise',
      news_eyebrow: 'News',
      news_h1: 'News & stories',
      news_count: '03',
      news_read: 'Read article',

      // article pages (shared chrome; per-article copy is CMS-generated)
      art_back: 'All News',
      art_cta_ours: 'Our own tours',
      art_outro_cta: 'About our tours',

      // home page
      home_title: 'Zenrise — Quiet journeys through Japan',
      home_hero_slide_1_meta: 'Meigetsuin, Hydrangea Season',
      home_hero_slide_2_meta: 'Kamakura, Coastline',
      home_hero_slide_3_meta: 'Coastal Railway, Dusk',
      home_hero_slide_4_meta: 'Tsurugaoka Hachimangu, Kamakura',
      home_hero_slide_5_meta: 'Great Buddha, Kamakura',
      home_hero_tag: 'Feature — 02',
      home_hero_num: '01',
      home_hero_title: 'Discover the<br/>hidden Japan.',
      home_hero_copy: 'From iconic highlights to the secret spots the guidebooks leave behind — personalized tours through local eyes, crafted just for you.',
      home_hero_more_label: 'Read more',

      // home — expanded category panels. Item lists are client content; leads on the
      // five list tiles (2,3,4,5,7) are drafted copy. Tile 8 is lead-only.

      // about page
      about_title: 'About — Zenrise',
      about_h1: 'About<br/>Zenrise.',
      about_intro_1: 'We are a travel agency based in Kamakura, Fujisawa, and Yokohama. We design thoughtful, locally-led journeys through the lesser-known corners of the Kamakura area.',
      about_intro_2: 'Founded in 2024, we\'re on a journey to discover and share the hidden gems of Japan — the quiet, beautiful places that travellers usually miss.',
      about_hero_credit: 'Hase-dera Gate, Kamakura',
      // company profile
      about_cp_label: 'Company Profile',
      about_cp_h2: 'Company Profile.',
      about_cp_name: 'Company Name',
      about_cp_name_v: 'Intercommunicate K. K.',
      about_cp_founded: 'Founded',
      about_cp_founded_v: 'April 2024',
      about_cp_reps: 'Representatives',
      about_cp_reps_v: 'Akari Usuda',
      about_cp_address: 'Address',
      about_cp_address_v: 'me-labo4, Sophiale Minamifujisawa #101<br/>10-11 Minamifujisawa, Fujisawa<br/>Kanagawa, 251-0055, Japan',
      about_cp_business: 'Business',
      about_cp_business_v: 'Curation &amp; operation of original tours across the Kamakura, Fujisawa &amp; Yokohama areas.<br/>Curation &amp; operation of bespoke, private tours.',
      about_cp_contact: 'Contact',
      about_cp_contact_v: 'hello@zenrise.jp',
      about_cp_license: 'Travel Agency License',
      about_cp_license_v: 'Registered Travel Agent, Kanagawa Prefecture No. 1314',
      about_cp_bank: 'Certified Domestic Travel Services Manager',
      about_cp_bank_v: 'Kentaro Usuda',

      // contact page
      contact_title: 'Contact — Zenrise',
      // letterhead hero
      contact_hero_eyebrow: 'Contact',
      contact_hero_no: '04',
      contact_hero_credit: 'Mt. Fuji, Shonan Coast',
      contact_hero_email: 'Email',
      contact_hero_visit: 'Office',
      contact_hero_visit_v: 'me-labo4, Sophiale Minamifujisawa #101<br/>10-11 Minamifujisawa, Fujisawa<br/>Kanagawa, 251-0055, Japan',
      // display hero (alt)
      // booking intro
      contact_bi_title: 'Plan your trip.',

      // booking flow — sidebar
      booking_progress_title: 'Booking',
      booking_step1_lbl: 'Where',
      booking_step2_lbl: 'How long',
      booking_step3_lbl: 'When &amp; who',
      booking_step4_lbl: 'About you',
      booking_step5_lbl: 'Review &amp; send',
      booking_quick_h: 'Or talk to us directly',
      booking_quick_p: 'Sometimes a form is too much. Email or call — we usually pick up.',
      booking_quick_email_l: 'Email',
      booking_quick_tel_l: 'Tel',
      booking_btn_back: 'Back',
      booking_btn_continue: 'Continue',
      booking_btn_send: 'Send to Zenrise',
      booking_btn_sending: 'Sending…',
      booking_send_err: 'Something went wrong sending your request. Please try again in a moment, or email hello@zenrise.jp directly.',

      // booking step 1: region
      booking_s1_meta: 'Step 01 / 05',
      booking_s1_h: 'Where would you<br/>like to go?',
      booking_s1_lede: 'Pick one or more. We can string two towns together on a full-day route, or stay in one all morning.',
      booking_s1_kamakura_sub: 'Temples · Tea<span class="s3"> · Kilns</span>',
      booking_s1_enoshima_sub: 'Coast · Caves<span class="s3"> · Seafood</span>',
      booking_s1_fujisawa_sub: 'Tokyo<span class="s3"> · Mt. Fuji</span> · Hakone',
      booking_s1_yokohama_sub: 'Port · Chinatown<span class="s3"> · Lights</span>',
      booking_s1_count_suffix: 'selected',

      // booking step 2: length
      booking_s2_meta: 'Step 02 / 05',
      booking_s2_sub: 'Tour length',
      booking_s2_h: 'Half-day or full?',
      booking_s2_lede: 'Half-days run roughly 09:00–13:00. Full-days end with a late lunch or a harbourside visit around 17:00.',
      booking_s2_half: 'Half-day',
      booking_s2_full: 'Full-day',
      booking_s2_half_p: 'One town, one neighbourhood. A long morning of exploring, one workshop or tea stop, and a quiet lunch.',
      booking_s2_full_p: 'Two towns linked by local train. A morning exploring, lunch with the day\u2019s host, an afternoon stop.',
      booking_s2_half_t: '≈ 4 hrs',
      booking_s2_full_t: '≈ 8 hrs',
      booking_s2_half_price: '¥65,000 / group',
      booking_s2_full_price: '¥95,000 / group',
      booking_s2_opt1: 'Option 01',
      booking_s2_opt2: 'Option 02',
      booking_s2_notes_ttl: 'Terms',
      booking_s2_note_base: '※ Base prices, tax included, per group of 1–6 people. Bookings start from one group.',
      booking_s2_note_fees: '+ Additional fees apply for what the base price doesn’t cover: hotel pick-up & drop-off transport, taxi or private-hire arrangements, hotel & ryokan bookings, activities and experiences, admission to attractions, and food & drink.',

      // booking step 3: when + who
      booking_s3_meta: 'Step 03 / 05',
      booking_s3_sub: 'Dates &amp; party',
      booking_s3_h: 'When, and how<br/>many of you?',
      booking_s3_lede: 'A rough window is fine — we\u2019ll come back with two or three open dates near it.',
      booking_s3_dates: 'Dates',
      booking_s3_date_from: 'Earliest date',
      booking_s3_date_to: 'Latest date',
      booking_s3_party: 'Group size',
      booking_s3_party_unit: 'travelers',
      booking_s3_party_hint: 'Groups are 1 to 6 people at most. For 7 or more we can plan a custom tour for an additional surcharge — just mention it in your notes.',
      booking_s3_exp: 'Is this your first visit to Japan?',
      booking_s3_exp_first: 'First time',
      booking_s3_exp_few: 'Been a few times',
      booking_s3_exp_many: 'Many times',
      booking_s3_exp_local: 'I live in Japan',

      // booking step 4: about you
      booking_s4_meta: 'Step 04 / 05',
      booking_s4_sub: 'Just the basics',
      booking_s4_h: 'And a little<br/>about you.',
      booking_s4_lede: 'Just enough so we can reply — and so we know how to plan around dietary needs or mobility.',
      booking_s4_name: 'Your name',
      booking_s4_name_p: 'First & last',
      booking_s4_email: 'Email',
      booking_s4_email_p: 'name@example.com',
      booking_s4_from: 'Where you\u2019re traveling from',
      booking_s4_from_p: 'City, country',
      booking_s4_interests: 'What pulls you in',
      booking_s4_int_tea: 'Tea ceremony',
      booking_s4_int_ceramics: 'Ceramics',
      booking_s4_int_food: 'Food',
      booking_s4_int_history: 'History',
      booking_s4_int_photo: 'Photography',
      booking_s4_int_coast: 'Coastline',
      booking_s4_int_temples: 'Quiet temples',
      booking_s4_int_crafts: 'Crafts',
      booking_s4_int_zen: 'Zen meditation',
      booking_s4_int_nature: 'Nature',
      booking_s4_int_local: 'Local life',
      booking_s4_int_cafes: 'Cafés',
      booking_s4_int_gardens: 'Gardens',
      booking_s4_int_markets: 'Markets',
      booking_s4_int_calligraphy: 'Calligraphy',
      booking_s4_notes: 'Anything else we should know?',
      booking_s4_notes_p: 'Dietary needs, mobility, a specific date or experience you have in mind, who you\u2019re traveling with…',

      // booking step 5: review
      booking_s5_meta: 'Step 05 / 05',
      booking_s5_sub: 'Last look',
      booking_s5_h: 'Sound right?',
      booking_s5_lede: 'A quick look over what you\u2019ll send us. You can still go back and change anything — or we\u2019ll figure it out in the reply.',
      booking_s5_consent: 'I\u2019m happy for Zenrise to email me about the trip and any follow-up, and I\u2019ve read and understood the <a href="terms.html" target="_blank" style="text-decoration: underline">booking terms &amp; conditions</a>, including the cancellation and privacy policies.',
      booking_summary_town: 'Town(s)',
      booking_summary_length: 'Length',
      booking_summary_dates: 'Dates',
      booking_summary_party: 'Group size',
      booking_summary_exp: 'Japan',
      booking_summary_name: 'Name',
      booking_summary_email: 'Email',
      booking_summary_from: 'From',
      booking_summary_interests: 'Interests',
      booking_summary_notes: 'Notes',
      booking_summary_edit: 'edit',
      booking_summary_em: '—',
      booking_summary_traveler: 'traveler',
      booking_summary_travelers: 'travelers',
      booking_summary_dates_flex: 'Flexible — talk to us',

      // booking sent
      booking_sent_n: 'Sent, thank you',
      booking_sent_h: 'That\u2019s with us.',
      booking_sent_p1: 'Thank you for reaching out. We\u2019ll write back within two business days with two or three itinerary sketches that fit your dates.',
      booking_sent_p2: 'If you haven\u2019t heard from us by then, an email may have gone astray \u2014 please write to hello@zenrise.jp and quote your reference below.',
      booking_sent_ref: 'Your reference',
      booking_sent_back_home: 'Back to homepage  →',
      booking_sent_back_about: 'Read more about us  →'
    },

    ja: {
      // language switcher
      langLabel: '日本語',
      english: 'English',
      japanese: '日本語',
      lang_menu_header: '言語',

      // nav
      nav_home: 'ホーム',
      nav_tours: 'ツアー',
      // contact region-card names (referenced by contact.html)
      home_dest_kamakura_name: '鎌倉',
      home_dest_enoshima_name: '江ノ島',
      home_dest_yokohama_name: '横浜',
      home_dest_fujisawa_name: 'その他の目的地',
      nav_about: '私たちについて',
      nav_news: 'ニュース',
      nav_contact: 'お問い合わせ',

      // tours page
      tours_title: 'ツアー — Zenrise',
      tours_h1: '私たちの<br/>ツアー。',
      tours_lede: '鎌倉エリアを中心とした、Zenriseオリジナルのツアー。私たち自身が調べ、歩き、書き上げた行程を、あなたのペースでご案内します。',
      tours_filter_label: 'エリアから探す',
      tours_area_all: 'すべてのエリア',
      tours_area_kamakura: '鎌倉',
      tours_area_enoshima: '江ノ島',
      tours_area_yokohama: '横浜',
      tours_filter_label_theme: '体験から探す',
      tours_theme_temples: '寺社',
      tours_theme_culture: '文化',
      tours_theme_arts: 'アートと工芸',
      tours_theme_food: '食',
      tours_theme_walking: 'まち歩き',
      tours_theme_nature: '眺めと自然',
      tours_theme_cycling: 'サイクリング',
      tours_len_half: '半日',
      tours_len_full: '一日',
      tours_len_both: '一日／半日',
      tours_cta_h: 'あなただけの旅を<br/>お探しですか？',
      tours_cta_p: '数日にわたる旅程も、ひとつの興味を深める一日も。決まったルートではなく、あなたに合わせて設計します。',
      tours_cta_link: 'オーダーメイドの旅を相談する',

      // home — tours + news sections
      home_tours_title: '私たちのツアー',
      home_tours_more: 'ツアー一覧',
      home_tours_cta: 'このツアーを見る',
      home_news_title: 'ニュースと読みもの',
      home_news_more: 'ニュース一覧',
      home_news_1_title: '東京を離れて過ごす一日',
      home_news_1_sub: '鎌倉・江ノ島日帰りバスツアー',
      home_news_2_title: '土俵の中を知る午後',
      home_news_2_sub: '新宿の相撲ショー&体験',
      home_news_3_title: '富士から箱根へ',
      home_news_3_sub: '\u5e30\u308a\u9053\u306f\u65b0\u5e79\u7dda\u3067',

      // tour detail — shared
      tours_back: 'ツアー一覧',
      td_f_tour: 'ツアー', td_f_area: 'エリア', td_f_format: '形式',
      td_f_length: '所要', td_f_group: '人数', td_f_from: '料金',
      td_included: '含まれるもの',
      td_notinc: '含まれないもの',
      td_bring: 'お持ちいただくもの',
      td_know: 'ご予約前に',
      td_book_heading: 'ご予約はこちら',
      td_route: 'ルート。',
      td_other: 'その他の情報。',
      td_other_terms: 'キャンセル・保険・お支払いに関する規定の全文',
      td_cta_h: '一緒に歩きませんか。',
      td_cta_p: 'ご希望の日程をお知らせください。2営業日以内に、空きのある朝の日程をご案内します。英語・日本語の冊子付きです。',
      td_cta_link: 'このツアーを予約する',
      td_prep_label: '準備中',
      td_prep_p1: 'このツアーの冊子は、いま執筆を進めているところです。公開の前に、それぞれのルートを何度も歩いて確かめています。',
      td_prep_p2: 'それまでの間も、お気軽にお問い合わせください。現時点での行程と、空きのある日程をメールでお送りします。',
      td_prep_cta: 'お問い合わせ',

      // tour detail — No. 04

      // tour detail — in-preparation tours

      // footer
      footer_tagline: '日本の知られざる場所を巡る、<br/>静かな旅。',
      footer_visit: 'オフィス',
      footer_contact: '連絡先',
      footer_follow: 'フォロー',
      footer_newsletter: 'ニュースレター',
      footer_address: '〒251-0055<br/>神奈川県藤沢市南藤沢 10-11<br/>Sophiale Minamifujisawa #101 me-labo4',
      footer_copyright: '© 2026 株式会社インターコミュニケート',
      footer_terms: '利用規約',
      footer_instagram: 'Instagram',
      footer_youtube: 'YouTube',
      footer_tiktok: 'TikTok',

      // terms page (legal notice, cancellation policy & tour insurance)
      terms_title: 'ご予約規約 — Zenrise',
      terms_h1: 'ご予約に関する規約',
      terms_legal_label: '特定商取引法に基づく表記',
      terms_legal_h2: '特定商取引法に基づく表記',
      terms_legal_note: '特定商取引に関する法律に基づき、以下のとおり表記いたします。',
      terms_legal_biz: '販売事業者名',
      terms_legal_biz_v: '株式会社インターコミュニケート / Zenrise',
      terms_legal_rep: '運営統括責任者',
      terms_legal_rep_v: '臼田 亜香麗',
      terms_legal_mgr: '国内旅行業務取扱管理者',
      terms_legal_mgr_v: '臼田 健太郎',
      terms_legal_addr: '所在地',
      terms_legal_addr_v: '〒251-0055<br/>神奈川県藤沢市南藤沢10-11<br/>ソフィアーレ南藤沢101 me-labo4',
      terms_legal_email: 'メールアドレス',
      terms_legal_email_v: 'hello@zenrise.jp',
      terms_legal_phone: '電話番号',
      terms_legal_phone_v: 'この情報は、請求があり次第、速やかに開示されます。',
      terms_legal_url: '販売URL',
      terms_legal_url_v: 'https://zenrise.jp',
      terms_legal_pay: 'お支払い方法',
      terms_legal_pay_v: 'クレジットカード決済<br/>銀行振込（振込手数料はお客様負担）<br/>PayPal（ペイパル）',
      terms_legal_paydl: 'お支払い時期',
      terms_legal_paydl_v: 'クレジットカード・PayPal：即時決済（各カード会社・決済サービスの会員規約に基づく引き落とし日）<br/><br/>銀行振込：お申し込み後7日以内にお振込みください。<br/><br/>※ツアー実施日の7日前以降にお申し込みの場合は、即時決済が可能なクレジットカードまたはPayPal決済のみのご利用となります。',
      terms_legal_delivery: '商品の引き渡し時期（役務の提供時期）',
      terms_legal_delivery_v: '各ツアーの開催日（事前にお申し込みいただいた日時）',
      terms_cancel_label: 'キャンセルポリシー',
      terms_cancel_h2: 'キャンセル・変更について',
      terms_cancel_intro: 'お客様都合によるキャンセルの場合は、標準旅行業約款に基づき、以下のキャンセル料を申し受けます。',
      terms_cancel_sub: '日帰り旅行（プライベートツアー）',
      terms_cancel_li1: 'ツアー催行日の11日前まで — 無料',
      terms_cancel_li2: '10日前〜8日前 — 代金の20%以内',
      terms_cancel_li3: '7日前〜2日前 — 代金の30%以内',
      terms_cancel_li4: 'ツアー前日 — 代金の40%以内',
      terms_cancel_li5: 'ツアー当日（旅行開始前）— 代金の50%以内',
      terms_cancel_li6: '旅行開始後・無連絡不参加 — 代金の100%',
      terms_cancel_costs: '※ツアー開始前の当日キャンセルであっても、すでに手配が完了している個別費用（タクシーの当日キャンセル料、施設の貸切料、事前に購入済みのチケット代等の実費）が発生している場合は、上記のキャンセル料（50%）とは別に、その実費全額をお客様にご負担いただきます。',
      terms_cancel_refund: '※天候不良等による主催者側からの催行中止の場合は、全額返金いたします。',
      terms_ins_label: '加入保険について',
      terms_ins_h2: '旅行保険',
      terms_ins_intro: '弊社は「一般社団法人 日本エコツーリズム協会」に加入しており、万が一の事故に備えてエコツアー向け保険（国内旅行傷害保険・施設所有者賠償責任保険等）を完備しております。ツアー代金には以下の補償が含まれています。',
      terms_ins_cov_h: '補償内容',
      terms_ins_li1: '死亡・後遺障害 — 500万円',
      terms_ins_li2: '入院保険金日額 — 5,000円',
      terms_ins_li3: '通院保険金日額 — 3,000円',
      terms_ins_li4: '手術保険金 — 入院中＝入院日額の10倍／それ以外＝入院日額の5倍',
      terms_ins_li5: '賠償責任保険 — 最高1億円（免責金額0円）',
      terms_ins_excl_h: '会社免責および注意事項',
      terms_ins_excl_1: '※当保険は「日帰りツアー」に参加されるお客様（訪日外国人含む）のみが対象となります。宿泊を伴うツアー、またはツアー行程外（集合前・解散後）における事故やケガについては、本保険の補償範囲外となります。',
      terms_ins_excl_2: '※当保険はお客様の持病の悪化、故意または重大な過失によるケガ、携行品（スマホ・カメラ等）の紛失・盗難・破損は補償の対象外となります。これらについて弊社は一切の責任を負いかねますので、必要な方はご自身で事前に海外旅行保険等へのご加入をお願いいたします。',
      terms_priv_label: 'プライバシーポリシー',
      terms_priv_h2: 'プライバシーポリシー',
      terms_priv_intro: '株式会社インターコミュニケート / Zenrise（以下「当社」）は、個人情報の保護に関する法律および関連ガイドラインを遵守し、以下のとおり個人情報を取り扱います。',
      terms_priv_h3_collect: '取得する情報',
      terms_priv_p_collect: 'お問い合わせ・ご予約の際にご提供いただく情報 — お名前、メールアドレス、ご出発地、ご希望の日程、人数、食事制限や移動に関するご要望・ご興味などお客様が任意でお知らせくださる事項 — および当社とのやり取りの記録を取得します。',
      terms_priv_h3_use: '利用目的',
      terms_priv_p_use: '取得した情報は、お問い合わせへの回答、ご予約いただいたツアーの企画・催行、決済および保険加入の手続き、ツアー中の安全確保、法令上の義務の履行のために利用します。ご同意なく広告・宣伝目的で利用することはありません。',
      terms_priv_h3_share: '第三者提供・委託',
      terms_priv_p_share: '法令に基づく場合を除き、ご本人の同意なく個人情報を第三者に提供しません。ツアーの催行に必要な範囲で、催行に関わる事業者（飲食店、体験提供者、保険会社等）に必要最小限の情報を共有する場合があり、委託先に対しては適切な監督を行います。',
      terms_priv_h3_safe: '安全管理',
      terms_priv_p_safe: '個人情報の漏えい・滅失・毀損の防止のため適切な安全管理措置を講じ、上記の利用目的に必要な期間に限り保管します。',
      terms_priv_h3_rights: '開示・訂正・削除',
      terms_priv_p_rights: 'ご本人からの個人情報の開示・訂正・利用停止・削除のご請求には、ご本人確認のうえ、法令に従い速やかに対応します。hello@zenrise.jp までご連絡ください。',
      terms_priv_h3_contact: '改定・お問い合わせ',
      terms_priv_p_contact: '本ポリシーは必要に応じて改定することがあり、変更は本ページに掲載します。個人情報に関するお問い合わせ窓口：株式会社インターコミュニケート / Zenrise — hello@zenrise.jp',

      // news index
      news_title: 'ニュース — Zenrise',
      news_eyebrow: 'News',
      news_h1: 'ニュースと読みもの',
      news_count: '03',
      news_read: '記事を読む',

      // article pages (shared chrome; per-article copy is CMS-generated)
      art_back: 'ニュース一覧',
      art_cta_ours: '私たちのツアー',
      art_outro_cta: '弊社のツアーについて',

      // home page
      home_title: 'Zenrise — 日本の静かな旅',
      home_hero_slide_1_meta: '明月院、紫陽花の季節',
      home_hero_slide_2_meta: '鎌倉、海辺',
      home_hero_slide_3_meta: '海沿いの線路、夕暮れ',
      home_hero_slide_4_meta: '鶴岡八幡宮、鎌倉',
      home_hero_slide_5_meta: '鎌倉大仏',
      home_hero_tag: '特集 — 02',
      home_hero_num: '01',
      home_hero_title: '知られざる日本へ。',
      home_hero_copy: '人気の観光地から、ガイドブックには載っていない穴場まで。地元民の目線であなただけの特別な体験を。',
      home_hero_more_label: '続きを読む',

      // home — expanded category panels. Item lists are client content; leads on the
      // five list tiles (2,3,4,5,7) are drafted copy. Tile 8 is lead-only.

      // about page
      about_title: '私たちについて — Zenrise',
      about_h1: 'Zenrise<br/>について。',
      about_intro_1: '鎌倉・藤沢・横浜を拠点とする旅行会社です。鎌倉エリアを中心に、地元目線であなただけの特別な体験を企画しています。',
      about_intro_2: '2024年設立。私たちは今、日本の隠れた名所を発見し、分かち合う旅の途中です — 旅人がいつも見逃してしまう、静かで美しい場所を。',
      about_hero_credit: '長谷寺 山門、鎌倉',
      // company profile
      about_cp_label: '会社概要',
      about_cp_h2: '会社概要。',
      about_cp_name: '会社名',
      about_cp_name_v: '株式会社インターコミュニケート',
      about_cp_founded: '設立',
      about_cp_founded_v: '2024年4月',
      about_cp_reps: '代表者',
      about_cp_reps_v: '臼田　亜香麗',
      about_cp_address: '所在地',
      about_cp_address_v: '〒251-0055<br/>神奈川県藤沢市南藤沢 10-11<br/>Sophiale Minamifujisawa #101 me-labo4',
      about_cp_business: '事業内容',
      about_cp_business_v: '鎌倉・藤沢・横浜エリアにおける自社ツアーの企画・運営。<br/>オーダーメイドプライベートツアーの企画・運営。',
      about_cp_contact: '連絡先',
      about_cp_contact_v: 'hello@zenrise.jp',
      about_cp_license: '旅行業登録',
      about_cp_license_v: '神奈川県知事登録旅行業 地域-第1314号',
      about_cp_bank: '国内旅行業務取扱管理者',
      about_cp_bank_v: '臼田　健太郎',

      // contact page
      contact_title: 'お問い合わせ — Zenrise',
      contact_hero_eyebrow: 'お問い合わせ',
      contact_hero_no: '04',
      contact_hero_credit: '富士山、湘南海岸',
      contact_hero_email: 'メール',
      contact_hero_visit: 'オフィス',
      contact_hero_visit_v: '〒251-0055<br/>神奈川県藤沢市南藤沢 10-11<br/>Sophiale Minamifujisawa #101 me-labo4',
      contact_bi_title: '旅を計画する。',

      // booking flow — sidebar
      booking_progress_title: 'ご予約',
      booking_step1_lbl: '行き先',
      booking_step2_lbl: '所要時間',
      booking_step3_lbl: '日時と人数',
      booking_step4_lbl: 'お客様について',
      booking_step5_lbl: '確認 &amp; 送信',
      booking_quick_h: '直接ご連絡もどうぞ',
      booking_quick_p: 'フォームが煩わしいときは、メールかお電話を。だいたい出ます。',
      booking_quick_email_l: 'メール',
      booking_quick_tel_l: '電話',
      booking_btn_back: '戻る',
      booking_btn_continue: '次へ',
      booking_btn_send: 'Zenrise に送る',
      booking_btn_sending: '送信中…',
      booking_send_err: '送信中に問題が発生しました。しばらくしてからもう一度お試しいただくか、hello@zenrise.jp まで直接ご連絡ください。',

      // booking step 1
      booking_s1_meta: 'ステップ 01 / 05',
      booking_s1_h: 'どこを訪れて<br/>みたいですか？',
      booking_s1_lede: '一つでも、複数でも構いません。一日のルートで二つの町をつなぐことも、一つの町で朝のあいだ過ごすこともできます。',
      booking_s1_kamakura_sub: '寺 · 茶<span class="s3"> · 窯</span>',
      booking_s1_enoshima_sub: '海岸 · 洞窟<span class="s3"> · 海の幸</span>',
      booking_s1_fujisawa_sub: '東京<span class="s3"> · 富士山</span> · 箱根',
      booking_s1_yokohama_sub: '港 · 中華街<span class="s3"> · 夜景</span>',
      booking_s1_count_suffix: '選択中',

      // booking step 2
      booking_s2_meta: 'ステップ 02 / 05',
      booking_s2_sub: 'ツアーの長さ',
      booking_s2_h: '半日? 一日?',
      booking_s2_lede: '半日はおおむね 09:00〜13:00。一日は遅めの昼食または港への立ち寄りで、17:00 ごろに終わります。',
      booking_s2_half: '半日',
      booking_s2_full: '一日',
      booking_s2_half_p: '一つの町、一つの地区。ゆっくりとした朝のひととき、一つの工房または茶の時間、そして静かな昼食。',
      booking_s2_full_p: '二つの町を地元の電車でつなぎます。朝のひととき、その日の案内人との昼食、午後の立ち寄り先。',
      booking_s2_half_t: '約 4 時間',
      booking_s2_full_t: '約 8 時間',
      booking_s2_half_price: '¥65,000 ／ 1組',
      booking_s2_full_price: '¥95,000 ／ 1組',
      booking_s2_opt1: 'オプション 01',
      booking_s2_opt2: 'オプション 02',
      booking_s2_notes_ttl: '注意事項',
      booking_s2_note_base: '※基本料金（税込）・1組（1〜6名さま）あたり。ご予約は1組から承ります。',
      booking_s2_note_fees: '＋追加料金：基本料金に含まれないもの — ホテル送迎の交通費、タクシー・ハイヤーの手配、ホテル・旅館のご宿泊予約、アクティビティ・体験の料金、観光施設の入場料、飲食費（レストラン・カフェ等）。',

      // booking step 3
      booking_s3_meta: 'ステップ 03 / 05',
      booking_s3_sub: '日時と人数',
      booking_s3_h: 'いつ、何人で<br/>来られますか?',
      booking_s3_lede: 'おおよその期間で構いません — その近辺で空いている候補日を二、三日、ご提案します。',
      booking_s3_dates: '日程',
      booking_s3_date_from: '最も早い日',
      booking_s3_date_to: '最も遅い日',
      booking_s3_party: '人数',
      booking_s3_party_unit: '名',
      booking_s3_party_hint: '1組は最大6名さままでです。7名さま以上は、追加料金にてカスタムツアーをご相談いただけます — 備考欄にお書き添えください。',
      booking_s3_exp: '日本は初めてですか?',
      booking_s3_exp_first: '初めて',
      booking_s3_exp_few: '数回ある',
      booking_s3_exp_many: '何度もある',
      booking_s3_exp_local: '日本に住んでいる',

      // booking step 4
      booking_s4_meta: 'ステップ 04 / 05',
      booking_s4_sub: '基本情報',
      booking_s4_h: 'お客様のことを<br/>少し教えてください。',
      booking_s4_lede: 'お返事を差し上げるために、また食事制限や移動についてご相談するために必要なことだけ。',
      booking_s4_name: 'お名前',
      booking_s4_name_p: '姓 名',
      booking_s4_email: 'メール',
      booking_s4_email_p: 'name@example.com',
      booking_s4_from: 'どちらから来られますか',
      booking_s4_from_p: '都市、国',
      booking_s4_interests: '惹かれるものは',
      booking_s4_int_tea: '茶の湯',
      booking_s4_int_ceramics: '陶芸',
      booking_s4_int_food: '食',
      booking_s4_int_history: '歴史',
      booking_s4_int_photo: '写真',
      booking_s4_int_coast: '海沿い',
      booking_s4_int_temples: '静かな寺',
      booking_s4_int_crafts: '手仕事',
      booking_s4_int_zen: '坐禅',
      booking_s4_int_nature: '自然',
      booking_s4_int_local: '地元の暮らし',
      booking_s4_int_cafes: 'カフェ',
      booking_s4_int_gardens: '庭園',
      booking_s4_int_markets: '朝市',
      booking_s4_int_calligraphy: '書道',
      booking_s4_notes: 'その他、お知らせいただくことは?',
      booking_s4_notes_p: '食事制限、移動のご都合、特にご希望の日付や体験、ご同行者など…',

      // booking step 5
      booking_s5_meta: 'ステップ 05 / 05',
      booking_s5_sub: '最終確認',
      booking_s5_h: 'こちらでよろしいですか?',
      booking_s5_lede: '送信する内容を最後にご確認ください。戻って変更することもできますし、お返事の中で調整することもできます。',
      booking_s5_consent: 'Zenrise から旅行とその後のやり取りに関するメールを受け取ることに同意し、キャンセルポリシー・プライバシーポリシーを含む<a href="terms.html" target="_blank" style="text-decoration: underline">ご予約規約</a>を読み、理解しました。',
      booking_summary_town: '町',
      booking_summary_length: '長さ',
      booking_summary_dates: '日付',
      booking_summary_party: '人数',
      booking_summary_exp: '日本での経験',
      booking_summary_name: 'お名前',
      booking_summary_email: 'メール',
      booking_summary_from: '出発地',
      booking_summary_interests: 'ご興味',
      booking_summary_notes: '備考',
      booking_summary_edit: '編集',
      booking_summary_em: '—',
      booking_summary_traveler: '名',
      booking_summary_travelers: '名',
      booking_summary_dates_flex: 'お任せ — ご相談ください',

      // booking sent
      booking_sent_n: '送信完了、ありがとうございます',
      booking_sent_h: '承りました。',
      booking_sent_p1: 'お問い合わせいただきありがとうございます。二営業日以内に、ご希望の日付に合う二、三の行程案をお送りします。',
      booking_sent_p2: '万が一ご連絡がない場合は、メールが届いていない可能性がございます。お手数ですが、下記の受付番号を添えて hello@zenrise.jp までご連絡ください。',
      booking_sent_ref: '受付番号',
      booking_sent_back_home: 'ホームへ戻る  →',
      booking_sent_back_about: '私たちについてもっと読む  →'
    }
  };

  // CMS-generated pages (news) define their copy inline as window.ZENRISE_CMS_DICT
  // before this script loads; fold it into the shared dictionaries.
  if (window.ZENRISE_CMS_DICT) {
    ['en', 'ja'].forEach(function (l) {
      var extra = window.ZENRISE_CMS_DICT[l];
      if (extra) for (var k in extra) DICT[l][k] = extra[k];
    });
  }

  // expose for use by page scripts (e.g. dynamically rendered text)
  window.ZenriseI18n = {
    get: function () { return getLang(); },
    t: function (key) {
      var d = DICT[getLang()] || DICT.en;
      return d[key] != null ? d[key] : (DICT.en[key] != null ? DICT.en[key] : key);
    },
    onChange: function (cb) { listeners.push(cb); }
  };

  var listeners = [];

  function getLang() {
    try { return localStorage.getItem(KEY) || 'en'; } catch (e) { return 'en'; }
  }
  function setLang(l) {
    try { localStorage.setItem(KEY, l); } catch (e) {}
    apply(l);
    listeners.forEach(function (cb) { try { cb(l); } catch (e) {} });
  }

  function apply(lang) {
    var d = DICT[lang] || DICT.en;
    var fb = DICT.en;

    // textContent
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      var v = d[key] != null ? d[key] : fb[key];
      if (v != null) el.textContent = v;
    });
    // innerHTML
    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-html');
      var v = d[key] != null ? d[key] : fb[key];
      if (v != null) el.innerHTML = v;
    });
    // placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-placeholder');
      var v = d[key] != null ? d[key] : fb[key];
      if (v != null) el.setAttribute('placeholder', v);
    });
    // title
    var t = document.querySelector('title[data-i18n-title]');
    if (t) {
      var key = t.getAttribute('data-i18n-title');
      var v = d[key] != null ? d[key] : fb[key];
      if (v != null) document.title = v;
    }

    document.documentElement.setAttribute('lang', lang === 'ja' ? 'ja' : 'en');

    var trig = document.querySelector('[data-lang-trigger] .lbl');
    if (trig) trig.textContent = d.langLabel;
    document.querySelectorAll('[data-lang-option]').forEach(function (o) {
      o.classList.toggle('on', o.getAttribute('data-lang-option') === lang);
    });
  }

  function injectStyles() {
    if (document.getElementById('zenrise-lang-style')) return;
    var s = document.createElement('style');
    s.id = 'zenrise-lang-style';
    s.textContent = [
      // wrapper + trigger
      '.lang-switcher { position: relative; justify-self: end; }',
      '.lang-trigger { background: none; border: none; padding: 0; font: inherit; font-size: 22px; color: inherit; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; letter-spacing: 0.01em; }',
      '.lang-trigger:hover { opacity: 0.7; }',
      '.lang-trigger .arrow { font-weight: 300; font-size: 20px; line-height: 1; position: relative; top: 0; transition: top 220ms cubic-bezier(.2,.6,.2,1), transform 220ms cubic-bezier(.2,.6,.2,1); color: #294138; display: inline-block; }',
      '.lang-switcher.open .lang-trigger .arrow { transform: rotate(180deg); }',
      // menu panel — cream, sharp corners, hairline border
      '.lang-menu { position: absolute; right: 0; top: calc(100% + 14px); background: #F7F4EA; border: 1px solid rgba(41,65,56,0.14); min-width: 190px; padding: 0; box-shadow: 0 24px 48px -8px rgba(41,65,56,0.18), 0 2px 6px rgba(41,65,56,0.04); opacity: 0; transform: translateY(-6px); pointer-events: none; transition: opacity 220ms cubic-bezier(.2,.6,.2,1), transform 220ms cubic-bezier(.2,.6,.2,1); z-index: 1000; border-radius: 0; }',
      '.lang-switcher.open .lang-menu { opacity: 1; transform: none; pointer-events: auto; }',
      // each language option — plain row
      '.lang-menu button { display: flex; align-items: center; justify-content: space-between; width: 100%; text-align: left; background: none; border: none; padding: 16px 22px; cursor: pointer; border-bottom: 1px solid rgba(41,65,56,0.06); transition: background 160ms ease; border-radius: 0; }',
      '.lang-menu button:last-child { border-bottom: none; }',
      '.lang-menu button:hover { background: rgba(41,65,56,0.04); }',
      '.lang-menu .name { font-family: "optima-nova-lt-pro", "toppan-bunkyu-mincho-pr6n", "Optima", serif; font-size: 22px; color: #294138; letter-spacing: -0.005em; line-height: 1; }',
      '.lang-menu button.on::after { content: ""; width: 6px; height: 6px; background: #294138; }',
      // ── mobile hamburger nav (shared, phone AND tablet widths) ──
      // 899, not 599: the nav's own content needs about 832px (brand + five
      // links + the language switcher), so between 600 and 860 the switcher was
      // pushed off the right edge -- 832px of content in a 768px viewport, which
      // also gave the page a horizontal scroll. Measured: overflows at 640 and
      // 768, fits from 860. 899 leaves margin. iPad landscape (1024+) keeps the
      // full nav. The .nav height/padding already drop to 72/20px at 1023, so
      // the burger's fixed offsets line up across this whole range.
      '.nav-burger, .mobile-nav { display: none; }',
      '@media (max-width: 899px) {',
      '  .nav { position: relative; }',
      '  .navlinks { display: none !important; }',
      '  .lang-switcher { display: none !important; }',
      // the three lines are an SVG background, not CSS boxes: layout snaps
      // each box edge to device pixels independently (so under fractional
      // zoom/DPR one bar can rasterize thicker than its siblings), while SVG
      // strokes get identical smooth anti-aliasing at any scale
      '  .nav-burger { display: block; position: absolute; right: 20px; top: 24px; width: 26px; height: 17px; border: none; padding: 0; cursor: pointer; z-index: 5; background: url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'26\' height=\'17\'%3E%3Cpath d=\'M0 .5h26M0 8.5h26M0 16.5h26\' stroke=\'%23294138\'/%3E%3C/svg%3E") center / 26px 17px no-repeat; }',
      '  .nav-burger::before { content: ""; position: absolute; inset: -16px; }',
      '  .nav-burger span { display: none; }',
      '  .mobile-nav { display: flex; flex-direction: column; position: fixed; inset: 0; z-index: 1200; background: #F7F4EA; padding: 56px 28px 40px; opacity: 0; pointer-events: none; transition: opacity 240ms ease; }',
      '  html.menu-open { overflow: hidden; }',
      '  html.menu-open .mobile-nav { opacity: 1; pointer-events: auto; }',
      // close button — two 1px hairlines, same weight as the burger, and
      // pinned so its glyph sits exactly where the burger sits in the nav
      // (26px glyph right-aligned to 20px, centred in the 64px bar) — no
      // jump between the two on open/close
      '  .mobile-nav-close { position: absolute; top: 14px; right: 15px; width: 36px; height: 36px; background: none; border: none; cursor: pointer; padding: 0; }',
      '  .mobile-nav-close span { position: absolute; left: 5px; top: 50%; width: 26px; height: 1px; background: #294138; }',
      '  .mobile-nav-close span:first-child { transform: rotate(45deg); }',
      '  .mobile-nav-close span:last-child { transform: rotate(-45deg); }',
      '  .mobile-nav-links { display: flex; flex-direction: column; gap: 6px; margin-top: 10vh; }',
      '  .mobile-nav-links a { font-family: "optima-nova-lt-pro","Optima",serif; font-size: 40px; line-height: 1.25; color: #294138; text-decoration: none; }',
      '  .mobile-nav-links a.active { opacity: 0.4; }',
      // opening choreography — links rise & fade in with a stagger, the
      // language block follows; closing snaps back with the menu fade
      '  .mobile-nav-links a { opacity: 0; transform: translateY(14px); transition: opacity 500ms ease, transform 500ms ease; }',
      '  html.menu-open .mobile-nav-links a { opacity: 1; transform: none; }',
      '  html.menu-open .mobile-nav-links a.active { opacity: 0.4; }',
      '  html.menu-open .mobile-nav-links a:nth-child(1) { transition-delay: 120ms; }',
      '  html.menu-open .mobile-nav-links a:nth-child(2) { transition-delay: 200ms; }',
      '  html.menu-open .mobile-nav-links a:nth-child(3) { transition-delay: 280ms; }',
      '  html.menu-open .mobile-nav-links a:nth-child(4) { transition-delay: 360ms; }',
      '  html.menu-open .mobile-nav-links a:nth-child(5) { transition-delay: 440ms; }',
      '  .mobile-nav-lang { opacity: 0; transition: opacity 500ms ease; }',
      '  html.menu-open .mobile-nav-lang { opacity: 1; transition-delay: 460ms; }',
      '  .mobile-nav-lang { margin-top: auto; border-top: 1px solid rgba(41,65,56,0.14); padding-top: 22px; }',
      '  .mobile-nav-lang .mnl-h { display: block; font-family: "gill-sans-nova", "Gill Sans", "Gill Sans MT", sans-serif; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(41,65,56,0.55); margin-bottom: 14px; }',
      '  .mobile-nav-lang button { display: inline-flex; align-items: baseline; gap: 10px; background: none; border: none; padding: 6px 0; margin-right: 32px; cursor: pointer; }',
      '  .mobile-nav-lang button .code { font-family: "gill-sans-nova", "Gill Sans", "Gill Sans MT", sans-serif; text-transform: uppercase; font-size: 12px; letter-spacing: 0.08em; color: rgba(41,65,56,0.5); }',
      '  .mobile-nav-lang button .name { font-family: "optima-nova-lt-pro","Optima",serif; font-size: 22px; color: #294138; }',
      '  .mobile-nav-lang button.on .name { text-decoration: underline; text-underline-offset: 4px; }',
      '}',
      // CTA underline offset, Japanese correction.
      //
      // Every CTA underline sits 0.18em below its text -- the ratio taken from
      // the home page's "All tours" link. That ratio is right for Latin type,
      // but Japanese glyphs sit higher in the line box, so the same offset
      // reads as a noticeably wider gap: measured at 3x DPR on the home tile
      // CTA, English came out at 6.0px and Japanese at 10.0px from the same
      // padding. Lifting the rule by 0.22em brings Japanese back to the same
      // optical gap. Expressed relatively so it holds at every CTA size, and
      // injected here because this is the language layer and it applies to
      // every page including the generated ones.
      'html[lang="ja"] .more-link > span:first-child::after,',
      'html[lang="ja"] .hero-card .more > span:first-child::after,',
      'html[lang="ja"] .dest .panel .go .u::after,',
      'html[lang="ja"] .bespoke .cta > span:first-child::after,',
      'html[lang="ja"] .book-cta .cta > span:first-child::after,',
      'html[lang="ja"] .f-body .more > span:first-child::after,',
      'html[lang="ja"] .cta-panel .cta .u::after,',
      'html[lang="ja"] .art-head .meta .back .lbl::after,',
      'html[lang="ja"] .art-foot .back .lbl::after,',
      'html[lang="ja"] .back .b-label::after,',
      'html[lang="ja"] .pg-num::after,',
      'html[lang="ja"] .foot-col .soc > span:first-child::after {',
      '  bottom: 0.28em;',
      '}'
    ].join('\n');
    document.head.appendChild(s);
  }

  // Entrance animations — shared by every subpage. A page opts in by putting
  // data-entrance="<reveal selector>" on its .stage; index.html keeps its own
  // hero-specific system and has no attribute. Runs at parse (lang.js sits at
  // end of body) so the hide rules land before fonts settle and the stage
  // (kept visibility:hidden while html.wf-loading) is ever painted.
  function initEntrance() {
    var stage = document.querySelector('.stage[data-entrance]');
    if (!stage || document.getElementById('zenrise-entrance-style')) return;
    // Full entrance only on the session's first view of a page, and never
    // under prefers-reduced-motion. Repeat views (reloads, quick back-and-
    // forth) return before any hide rule is injected, so the page renders
    // settled instead of blanking and re-animating content the visitor has
    // already seen.
    var seenKey = 'zenrise-entrance:' + location.pathname;
    try {
      if (sessionStorage.getItem(seenKey) === '1') return;
    } catch (e) {}
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    try { sessionStorage.setItem(seenKey, '1'); } catch (e) {}
    var s = document.createElement('style');
    s.id = 'zenrise-entrance-style';
    s.textContent = [
      '@keyframes page-fade {',
      '  from { opacity: 0; transform: translateY(10px); }',
      '  to   { opacity: 1; transform: none; }',
      '}',
      '.intro-a, .intro-b { opacity: 0; }',
      '.stage.page-in .intro-a { animation: page-fade 0.9s ease forwards; }',
      '.stage.page-in .intro-b { animation: page-fade 0.9s ease 0.35s forwards; }',
      '.reveal { opacity: 0; transform: translateY(12px); transition: opacity 700ms ease, transform 700ms ease; }',
      '.reveal.in { opacity: 1; transform: none; }'
    ].join('\n');
    document.head.appendChild(s);

    // Intro beats fire once fonts are active (wf-loading removed), then
    // sections reveal on scroll; reveal setup waits for fonts so above-fold
    // sections animate on load too (the stage is hidden until then).
    function start() {
      requestAnimationFrame(function () { stage.classList.add('page-in'); });
      var els = document.querySelectorAll(stage.getAttribute('data-entrance'));
      els.forEach(function (el) { el.classList.add('reveal'); });
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) {
            if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
          });
        }, { threshold: 0.08 });
        els.forEach(function (el) { io.observe(el); });
      } else {
        els.forEach(function (el) { el.classList.add('in'); });
      }
    }
    if (!document.documentElement.classList.contains('wf-loading')) {
      start();
    } else {
      var obs = new MutationObserver(function () {
        if (!document.documentElement.classList.contains('wf-loading')) {
          obs.disconnect();
          start();
        }
      });
      obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    }
  }

  function init() {
    injectStyles();

    var orig = document.querySelector('a.lang');
    if (orig) {
      var wrapper = document.createElement('div');
      wrapper.className = 'lang-switcher';
      wrapper.innerHTML =
        '<button class="lang-trigger" type="button" data-lang-trigger aria-haspopup="listbox" aria-expanded="false">' +
          '<span class="lbl">english</span><span class="arrow">↓</span>' +
        '</button>' +
        '<div class="lang-menu" role="listbox">' +
          '<button type="button" data-lang-option="en">' +
            '<span class="name">English</span>' +
          '</button>' +
          '<button type="button" data-lang-option="ja">' +
            '<span class="name">日本語</span>' +
          '</button>' +
        '</div>';
      orig.parentNode.replaceChild(wrapper, orig);

      var trigger = wrapper.querySelector('[data-lang-trigger]');
      trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = wrapper.classList.toggle('open');
        trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      wrapper.querySelectorAll('[data-lang-option]').forEach(function (opt) {
        opt.addEventListener('click', function (e) {
          e.stopPropagation();
          setLang(opt.getAttribute('data-lang-option'));
          wrapper.classList.remove('open');
          trigger.setAttribute('aria-expanded', 'false');
        });
      });
      document.addEventListener('click', function () {
        wrapper.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
          wrapper.classList.remove('open');
          trigger.setAttribute('aria-expanded', 'false');
        }
      });
    }

    // ── Mobile hamburger nav (shared across pages) ──
    var navEl = document.querySelector('.nav');
    var navLinksEl = navEl && navEl.querySelector('.navlinks');
    if (navEl && navLinksEl) {
      var burger = document.createElement('button');
      burger.className = 'nav-burger';
      burger.type = 'button';
      burger.setAttribute('aria-label', 'Open menu');
      burger.setAttribute('aria-expanded', 'false');
      burger.innerHTML = '<span></span><span></span><span></span>';
      navEl.appendChild(burger);

      var menu = document.createElement('div');
      menu.className = 'mobile-nav';
      menu.innerHTML =
        '<button class="mobile-nav-close" type="button" aria-label="Close"><span></span><span></span></button>' +
        '<nav class="mobile-nav-links">' + navLinksEl.innerHTML + '</nav>' +
        '<div class="mobile-nav-lang">' +
          '<span class="mnl-h" data-i18n="lang_menu_header">Language</span>' +
          '<button type="button" data-lang-option="en"><span class="code">EN</span><span class="name">English</span></button>' +
          '<button type="button" data-lang-option="ja"><span class="code">JP</span><span class="name">日本語</span></button>' +
        '</div>';
      document.body.appendChild(menu);

      function closeMenu() {
        document.documentElement.classList.remove('menu-open');
        burger.setAttribute('aria-expanded', 'false');
      }
      burger.addEventListener('click', function () {
        document.documentElement.classList.add('menu-open');
        burger.setAttribute('aria-expanded', 'true');
      });
      menu.querySelector('.mobile-nav-close').addEventListener('click', closeMenu);
      menu.querySelectorAll('.mobile-nav-links a').forEach(function (a) {
        a.addEventListener('click', closeMenu);
      });
      menu.querySelectorAll('[data-lang-option]').forEach(function (opt) {
        opt.addEventListener('click', function () {
          setLang(opt.getAttribute('data-lang-option'));
          closeMenu();
        });
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeMenu();
      });
    }

    // Nav links pointing at the current page dead-click (scroll to top)
    // instead of reloading — a same-page reload would replay the entrance
    // system's initial hidden state on content already on screen.
    function samePage(a) {
      var href = a.getAttribute('href');
      if (!href || href.charAt(0) === '#') return false;
      var u;
      try { u = new URL(href, location.href); } catch (e) { return false; }
      if (u.origin !== location.origin || u.hash) return false;
      var norm = function (p) { return p.replace(/\/index\.html$/, '/'); };
      return norm(u.pathname) === norm(location.pathname);
    }
    document.querySelectorAll('.navlinks a, .mobile-nav-links a').forEach(function (a) {
      if (!samePage(a)) return;
      a.addEventListener('click', function (e) {
        e.preventDefault();
        var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
      });
    });

    apply(getLang());
  }

  initEntrance();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
