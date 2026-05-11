import base64
import requests
import re
import sys
import os
import time
import threading
import shutil
import textwrap
import hashlib
import select

# ─── ANSI Color Codes ─────────────────────────────────────────────────────────
RED    = '\033[91m'
GREEN  = '\033[92m'
YELLOW = '\033[93m'
WHITE  = '\033[97m'
CYAN   = '\033[96m'
RESET  = '\033[0m'

# Strips ANSI escape sequences for width-safe text measurement
_ANSI_ESC = re.compile(r'\033\[[0-9;]*m')

# ─── Global Word-Wrap Print ───────────────────────────────────────────────────
def smart_print(text, color='', indent=0):
    """
    Print text wrapped to the current terminal width, breaking at spaces only.
    - color : an ANSI color constant to apply to every wrapped line (optional)
    - indent: number of leading spaces on every line
    ANSI codes in `text` are stripped before wrapping so they never split words.
    """
    cols  = max(20, shutil.get_terminal_size((58, 20)).columns)
    pad   = ' ' * indent
    reset = RESET if color else ''
    plain = _ANSI_ESC.sub('', text)   # strip codes → measure correctly

    for para in plain.split('\n'):
        stripped = para.strip()
        if not stripped:
            print()
            continue
        lines = textwrap.wrap(
            stripped,
            width             = max(1, cols - indent),
            break_long_words  = False,   # never split a word mid-character
            break_on_hyphens  = False,   # keep hyphenated words intact
        )
        for line in (lines or ['']):
            print(f"{color}{pad}{line}{reset}")

# ─── Reverse-Base64 Masked API Keys (DO NOT MODIFY) ───────────────────────────
_VT_MASKED  = "YzU5MGE0NjY1ODRkMTNlNmZiZjllOGIxNzdiMzlhYzlmNTg3ZmE0Yzk1Y2Q3MThjZjYwZjRlMjdlM2ZkN2Q1Nw=="
_URL_MASKED = "NmQ1NTMyZjIwZDIyLTZhZmItOTY0Ny0xM2NlLWMzNWZjOTEw"

# ─── File Scan Size Limit ─────────────────────────────────────────────────────
FILE_SIZE_LIMIT = 50 * 1024 * 1024   # 50 MB

def _decode_key(masked):
    try:
        decoded = base64.b64decode(masked).decode('utf-8')
        return decoded[::-1]
    except Exception:
        return None

def get_vt_key():
    return _decode_key(_VT_MASKED)

def get_url_key():
    return _decode_key(_URL_MASKED)

# ─── URL Sanitizer ────────────────────────────────────────────────────────────
def sanitize_url(url):
    url = url.strip()
    if not url:
        return None
    if not re.match(r'^https?://', url):
        url = 'https://' + url
    regex = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if re.match(regex, url):
        return url
    return None

# ─── ASCII Art Lines (raw, no color) ─────────────────────────────────────────
ASCII_LINES = [
    r"  ______ ___ ____  _____        ",
    r" |  ___|_ _| __ \| ____|       ",
    r" | |_   | ||   / |  _|         ",
    r" |  _|  | || |\ \| |___        ",
    r" |_|   |___|_| \_\_____|       ",
    r"  ____  _   _ ___ ___ _    ____ ",
    r" / ___|| | | |_ _| __| |  |  _ \ ",
    r" \___ \| |_| || || _|| |__| | | |",
    r"  ___) |  _  || || |___  _| |_| |",
    r" |____/|_| |_|___|_____|_||____/ ",
]

WIDTH = 58

# ─── Animated Banner (infinite shimmer until Enter is pressed) ────────────────
def banner():
    credit  = "[-] Tool Created by Bayazid Habib [-]"
    version = "Version : 0.1"
    prompt  = "[ Press Enter to run the tool ]"

    stop_flag   = {'stop': False}
    frame_cycle = [YELLOW, RED, YELLOW, RED, YELLOW, RED]

    def _animate():
        idx = 0
        while not stop_flag['stop']:
            base_color = frame_cycle[idx % len(frame_cycle)]
            os.system('clear')
            print()
            for i, line in enumerate(ASCII_LINES):
                color = YELLOW if i % 2 == 0 else RED
                if base_color == RED:
                    color = RED if i % 2 == 0 else YELLOW
                print(color + line.center(WIDTH) + RESET)
            print()
            print(GREEN + credit.center(WIDTH) + RESET)
            print(WHITE + version.center(WIDTH) + RESET)
            print()
            print(CYAN + prompt.center(WIDTH) + RESET)
            time.sleep(0.2)
            idx += 1

    anim_thread = threading.Thread(target=_animate, daemon=True)
    anim_thread.start()

    input()                    # Blocks until user presses Enter
    stop_flag['stop'] = True
    anim_thread.join(timeout=0.5)

    # Final settled frame — full YELLOW, no flicker
    os.system('clear')
    print()
    for line in ASCII_LINES:
        print(YELLOW + line.center(WIDTH) + RESET)
    print()
    print(GREEN + credit.center(WIDTH) + RESET)
    print(WHITE + version.center(WIDTH) + RESET)
    print()
    time.sleep(0.4)

# ─── Static Banner (used by menu & modules) ───────────────────────────────────
BANNER = f"""
{YELLOW}  ______ ___ ____  _____        
 |  ___|_ _| __ \| ____|       
 | |_   | ||   / |  _|         
 |  _|  | || |\ \| |___        
 |_|   |___|_| \_\_____|       
  ____  _   _ ___ ___ _    ____ 
 / ___|| | | |_ _| __| |  |  _ \\
 \___ \| |_| || || _|| |__| | | |
  ___) |  _  || || |___  _| |_| |
 |____/|_| |_|___|_____|_||____/ {RESET}
                    {RED}Version : 0.1{RESET}
"""

# ─── Menu ─────────────────────────────────────────────────────────────────────
def show_menu():
    os.system('clear')
    print(BANNER)
    print(f"{GREEN}[-] Tool Created by Bayazid Habib [-]{RESET}\n")
    print(f"{GREEN}[::] Select A Scan Module [::]  {RESET}\n")
    print(f"  {RED}[01]{RESET}  {GREEN}Scan URL{RESET}")
    print(f"  {RED}[02]{RESET}  {GREEN}Scan File{RESET}")
    print(f"  {RED}[03]{RESET}  {GREEN}Scan IP Address{RESET}")
    print()
    print(f"  {RED}[99]{RESET}  {GREEN}Exit{RESET}")
    print()
    choice = input(f"{GREEN}[-] Select an option : {RESET}")
    return choice.strip()

# ─── Helper: VirusTotal verdict display ───────────────────────────────────────
def _display_vt_stats(stats, label="Analysis"):
    malicious   = stats.get('malicious', 0)
    suspicious  = stats.get('suspicious', 0)
    harmless    = stats.get('harmless', 0)
    undetected  = stats.get('undetected', 0)
    total       = malicious + suspicious + harmless + undetected

    print(f"\n{CYAN}  ── VirusTotal {label} ──{RESET}")
    print(f"  {GREEN}[+] Harmless   : {harmless}{RESET}")
    print(f"  {YELLOW}[~] Suspicious : {suspicious}{RESET}")
    print(f"  {WHITE}[-] Undetected : {undetected}{RESET}")
    print(f"  {RED}[x] Malicious  : {malicious}{RESET}")

    if malicious == 0 and suspicious == 0:
        print(f"\n{GREEN}[v] Verdict: No significant threats detected ({total} engines checked).{RESET}")
    elif malicious <= 3:
        print(f"\n{YELLOW}[~] Verdict: Low-level flags found. Proceed with caution.{RESET}")
    else:
        print(f"\n{RED}[!] Verdict: Threat detected by {malicious} engine(s). Avoid this target.{RESET}")

# ─── Helper: Detailed per-engine file report (File Scan only) ────────────────
def _display_vt_file_report(attrs, analysis_id, scan_type='file', start_n=1):
    stats      = attrs.get('stats', {})
    results    = attrs.get('results', {})
    malicious  = stats.get('malicious', 0)
    suspicious = stats.get('suspicious', 0)
    harmless   = stats.get('harmless', 0)
    undetected = stats.get('undetected', 0)
    total      = malicious + suspicious + harmless + undetected
    detections = malicious + suspicious

    scan_link  = f"https://www.virustotal.com/gui/{scan_type}-analysis/{analysis_id}"
    SEP        = f"{CYAN}  {'─' * 44}{RESET}"

    # ── Summary header ─────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    det_color = RED if detections > 0 else GREEN
    det_label = f"[!]" if detections > 0 else "[v]"
    print(f"  {det_color}{det_label} Total Detections : {detections} / {total}{RESET}")
    print(f"  {GREEN}[+] Scan Link        : {scan_link}{RESET}")
    print(SEP)

    # ── Bucket engines by category ─────────────────────────────────────────────
    flagged_mal  = {}
    flagged_sus  = {}
    clean        = {}

    for engine, data in results.items():
        cat = data.get('category', '')
        if cat in ('malicious', 'phishing'):
            flagged_mal[engine] = data
        elif cat == 'suspicious':
            flagged_sus[engine] = data
        else:
            clean[engine] = data

    # ── Print flagged: malicious / phishing ────────────────────────────────────
    n = start_n
    if flagged_mal:
        print(f"\n{RED}  ── Malicious / Phishing ──{RESET}")
        for engine in sorted(flagged_mal):
            result = flagged_mal[engine].get('result') or 'Malicious'
            print(f"  {RED}[!] {n}. {engine:<24} -----> {result}{RESET}")
            n += 1

    # ── Print flagged: suspicious ──────────────────────────────────────────────
    if flagged_sus:
        print(f"\n{YELLOW}  ── Suspicious ──{RESET}")
        for engine in sorted(flagged_sus):
            result = flagged_sus[engine].get('result') or 'Suspicious'
            print(f"  {YELLOW}[~] {n}. {engine:<24} -----> {result}{RESET}")
            n += 1

    # ── Print clean engines ────────────────────────────────────────────────────
    if clean:
        print(f"\n{GREEN}  ── Clean / Undetected ──{RESET}")
        for engine in sorted(clean):
            result = clean[engine].get('result') or clean[engine].get('category', 'Clean').capitalize()
            print(f"  {WHITE}[-] {n}. {engine:<24} -----> {result}{RESET}")
            n += 1

    # ── Overall verdict ────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    if detections == 0:
        print(f"  {GREEN}[v] Verdict: Clean. No threats detected ({total} engines).{RESET}")
    elif malicious <= 3:
        print(f"  {YELLOW}[~] Verdict: Low-level flags. Proceed with caution.{RESET}")
    else:
        print(f"  {RED}[!] Verdict: Threat detected by {malicious} engine(s). Avoid this file.{RESET}")
    print(SEP)

# ─── Helper: Full URLscan.io report display ───────────────────────────────────
def _display_urlscan_full_report(data, uuid, start_n=1):
    """Prints all URLscan.io fields in sequential numbered list. Returns final n."""
    SEP  = f"{CYAN}  {'─' * 44}{RESET}"
    n    = start_n

    page     = data.get('page', {})
    stats    = data.get('stats', {})
    verdicts = data.get('verdicts', {}).get('overall', {})
    lists    = data.get('lists', {})
    meta     = data.get('meta', {})
    asn_list = meta.get('processors', {}).get('asn', {}).get('data', [])
    asn      = asn_list[0] if asn_list else {}

    # ── Page Info ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  {CYAN}── Page Information ──{RESET}")
    print(SEP)
    fields_page = [
        ("Page Title",    page.get('title',    'N/A')),
        ("Effective URL", page.get('url',       'N/A')),
        ("IP Address",    page.get('ip',        'N/A')),
        ("Country",       page.get('country',   'N/A')),
        ("City",          page.get('city',      'N/A')),
        ("Server",        page.get('server',    'N/A')),
        ("MIME Type",     page.get('mimeType',  'N/A')),
        ("Status Code",   str(page.get('statusCode', 'N/A'))),
    ]
    for label, value in fields_page:
        print(f"  {WHITE}{n}. {label:<18} : {value}{RESET}")
        n += 1

    # ── ASN / ISP ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  {CYAN}── Network / ASN ──{RESET}")
    print(SEP)
    fields_asn = [
        ("ASN",          asn.get('asn',         'N/A')),
        ("ISP / Org",    asn.get('name',         'N/A')),
        ("ASN Country",  asn.get('country',      'N/A')),
        ("Route",        asn.get('route',        'N/A')),
        ("Description",  asn.get('description',  'N/A')),
    ]
    for label, value in fields_asn:
        print(f"  {WHITE}{n}. {label:<18} : {value}{RESET}")
        n += 1

    # ── SSL / TLS ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  {CYAN}── SSL / TLS Certificate ──{RESET}")
    print(SEP)
    fields_ssl = [
        ("TLS Issuer",     page.get('tlsIssuer',    'N/A')),
        ("Valid From",     page.get('tlsValidFrom',  'N/A')),
        ("Valid For Days", str(page.get('tlsValidDays', 'N/A'))),
        ("TLS Age Days",   str(page.get('tlsAgeDays',   'N/A'))),
    ]
    for label, value in fields_ssl:
        print(f"  {WHITE}{n}. {label:<18} : {value}{RESET}")
        n += 1

    # ── Scan Statistics ───────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  {CYAN}── Scan Statistics ──{RESET}")
    print(SEP)
    fields_stats = [
        ("Total Requests",  str(stats.get('requests',     'N/A'))),
        ("Unique Domains",  str(stats.get('uniqDomains',  'N/A'))),
        ("Unique IPs",      str(stats.get('uniqIPs',      'N/A'))),
        ("Data (bytes)",    str(stats.get('dataLength',   'N/A'))),
        ("Malicious Reqs",  str(stats.get('malicious',    0))),
    ]
    for label, value in fields_stats:
        print(f"  {WHITE}{n}. {label:<18} : {value}{RESET}")
        n += 1

    # ── Domains Contacted ─────────────────────────────────────────────────────
    domains = lists.get('domains', [])
    if domains:
        print(f"\n{SEP}")
        print(f"  {CYAN}── Domains Contacted ({len(domains)}) ──{RESET}")
        print(SEP)
        for d in domains[:15]:   # cap at 15 for Termux readability
            print(f"  {WHITE}{n}. {d}{RESET}")
            n += 1
        if len(domains) > 15:
            print(f"  {CYAN}    ... and {len(domains) - 15} more (see full report){RESET}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    is_mal  = verdicts.get('malicious', False)
    score   = verdicts.get('score', 0)
    tags    = ', '.join(verdicts.get('tags', [])) or 'None'
    v_color = RED if is_mal else GREEN
    v_label = 'Malicious' if is_mal else 'Clean'

    print(f"\n{SEP}")
    print(f"  {CYAN}── Verdict ──{RESET}")
    print(SEP)
    print(f"  {v_color}{n}. Verdict   : {v_label} (Score: {score}){RESET}"); n += 1
    print(f"  {WHITE}{n}. Tags      : {tags}{RESET}");                        n += 1
    print(f"  {GREEN}{n}. Full Link : https://urlscan.io/result/{uuid}/{RESET}"); n += 1

    print(f"\n{SEP}")
    return n  # return final counter for VT continuation

# ─── Helper: URLscan.io Diagnostic Error Report ───────────────────────────────
def _display_urlscan_error_report(error):
    SEP   = f"{CYAN}  {'─' * 44}{RESET}"
    code  = error.get('code', 'Unknown')
    msg   = error.get('message', 'No additional details.')

    print(f"\n{SEP}")
    print(f"  {RED}── URLscan.io Diagnostic Report ──{RESET}")
    print(SEP)
    print(f"\n  {RED}Technical Error : HTTP {code} (Bad Request){RESET}")
    smart_print(f"API Message : {msg}", color=YELLOW, indent=2)

    print(f"\n{SEP}")
    print(f"  {CYAN}── Possible Reasons ──{RESET}")
    print(SEP)

    reasons = [
        (
            "1. Bot Detection & Security Headers",
            "High-security domains like Facebook deploy strict Content-Security-Policy "
            "and X-Frame-Options headers to block automated headless browsers. When "
            "URLscan.io's Chromium instance attempts to load the page, the server "
            "detects the missing human interaction signals (mouse events, cookies, "
            "JS challenges) and responds with a 400 or challenge block before the "
            "page even renders, causing the scan submission to be rejected."
        ),
        (
            "2. Mandatory User Authentication (Login Wall)",
            "Many pages on Facebook, Instagram, and similar platforms require an "
            "active authenticated session before serving any meaningful content. "
            "URLscan.io operates without credentials, so the target URL redirects "
            "to a login page or returns an error payload. The API then flags the "
            "submission as invalid because the effective destination URL is not the "
            "same as the submitted one, triggering a 400 Bad Request response."
        ),
        (
            "3. IP Reputation & Rate Limiting",
            "Scanning engines like URLscan.io operate from known data-center IP "
            "ranges (AWS, Google Cloud, Cloudflare). Facebook and CDN-backed targets "
            "maintain real-time blocklists of these IP ranges and apply aggressive "
            "rate limiting. A request originating from a flagged ASN may receive a "
            "400 response or silent drop before reaching the application layer, "
            "making it impossible for the scan engine to retrieve page content."
        ),
        (
            "4. Dynamic JavaScript Execution Failure",
            "Modern single-page applications like Facebook rely on complex JS "
            "bundles, dynamic redirects, and AJAX-based authentication flows that "
            "free-tier scanning engines cannot fully execute. If the initial JS "
            "challenge or redirect chain does not complete within the engine's "
            "timeout window, the scan is aborted and a 400 is returned, as the "
            "engine cannot confirm the final resolved URL or page state."
        ),
    ]

    for title, body in reasons:
        print(f"\n  {YELLOW}[~] {title}{RESET}")
        smart_print(body, color=WHITE, indent=2)

    print(f"\n{SEP}")
    smart_print("Recommendation: Use VirusTotal report for this target.", color=GREEN, indent=2)
    print(SEP)

# ─── Interactive Report Sub-Menu (URL Scan only) ──────────────────────────────
def _show_report_menu(urlscan_data, urlscan_uuid, urlscan_ok,
                      vt_result, vt_analysis_id, vt_submitted,
                      urlscan_error=None):
    SEP = f"{CYAN}  {'─' * 44}{RESET}"

    while True:
        os.system('clear')
        print(BANNER)
        print(f"{GREEN}[::] SCAN COMPLETE — SELECT REPORT [::]  {RESET}\n")

        # ── [01] label changes if URLscan errored ──────────────────────────────
        if urlscan_error:
            label_01 = (f"{GREEN}URLscan.io Report  "
                        f"{RED}(See error details){RESET}")
        else:
            label_01 = f"{GREEN}URLscan.io Full Report{RESET}"

        print(f"  {RED}[01]{RESET}  {label_01}")
        print(f"  {RED}[02]{RESET}  {GREEN}VirusTotal Full Report{RESET}")
        print(f"  {RED}[03]{RESET}  {GREEN}Both Reports (Sequential){RESET}")
        print()
        print(f"  {RED}[00]{RESET}  {GREEN}Back to Scan Menu{RESET}")
        print()
        choice = input(f"{GREEN}[-] Select report : {RESET}").strip()

        if choice == '00':
            return

        os.system('clear')
        print(BANNER)

        if choice == '01':
            # ── URLscan.io — success report or diagnostic ──────────────────────
            if urlscan_error:
                _display_urlscan_error_report(urlscan_error)
            elif urlscan_ok and urlscan_data:
                _display_urlscan_full_report(urlscan_data, urlscan_uuid, start_n=1)
            else:
                print(f"\n{RED}[!] URLscan report failed to load.{RESET}")

        elif choice == '02':
            # ── VirusTotal only ────────────────────────────────────────────────
            if vt_result['attrs']:
                _display_vt_file_report(
                    vt_result['attrs'], vt_analysis_id,
                    scan_type='url', start_n=1
                )
            elif vt_submitted:
                print(f"\n{YELLOW}[~] VirusTotal: Analysis timed out.{RESET}")
            else:
                print(f"\n{YELLOW}[~] VirusTotal: Was not submitted.{RESET}")

        elif choice == '03':
            # ── Both sequential ────────────────────────────────────────────────
            n = 1
            if urlscan_ok and urlscan_data:
                n = _display_urlscan_full_report(urlscan_data, urlscan_uuid, start_n=n)
            else:
                print(f"\n{RED}[!] URLscan report failed to load.{RESET}")

            if vt_result['attrs']:
                print(f"\n{SEP}")
                print(f"  {CYAN}── VirusTotal Report (continuing #{n}) ──{RESET}")
                print(SEP)
                _display_vt_file_report(
                    vt_result['attrs'], vt_analysis_id,
                    scan_type='url', start_n=n
                )
            elif vt_submitted:
                print(f"\n{YELLOW}[~] VirusTotal: Analysis timed out.{RESET}")
            else:
                print(f"\n{YELLOW}[~] VirusTotal: Was not submitted.{RESET}")

        else:
            print(f"\n{YELLOW}[!] Invalid choice. Select 01, 02, 03, or 00.{RESET}")

        input(f"\n{YELLOW}[*] Press Enter to return to Report Menu...{RESET}")

# ─── Module 01 : URL Scanner (URLscan.io + VirusTotal) ────────────────────────
def scan_url():
    os.system('clear')
    print(BANNER)
    print(f"{GREEN}[::] URL SCAN MODULE [::]  {RESET}\n")

    raw_input = input(f"{GREEN}[?] Enter Target URL: {RESET}")
    target_url = sanitize_url(raw_input)

    if not target_url:
        print(f"\n{RED}[!] Error: Invalid URL format.{RESET}")
        input(f"\n{YELLOW}[*] Press Enter to return to menu...{RESET}")
        return

    # ── Submit both APIs ───────────────────────────────────────────────────────
    print(f"\n{YELLOW}[*] Submitting to URLscan.io and VirusTotal simultaneously...{RESET}")

    urlscan_uuid      = None
    urlscan_submitted = False
    urlscan_error     = None   # captures HTTP error for diagnostic report
    vt_analysis_id    = None
    vt_submitted      = False

    # URLscan.io submission
    try:
        url_resp = requests.post(
            'https://urlscan.io/api/v1/scan/',
            headers={'API-Key': get_url_key(), 'Content-Type': 'application/json'},
            json={"url": target_url, "visibility": "unlisted"},
            timeout=15
        )
        if url_resp.status_code == 200:
            urlscan_uuid      = url_resp.json().get('uuid')
            urlscan_submitted = True
            print(f"{GREEN}[+] URLscan.io : Submitted (UUID: {urlscan_uuid}){RESET}")
        elif url_resp.status_code == 401:
            urlscan_error = {'code': 401, 'message': 'Unauthorized — API key rejected.'}
            print(f"{RED}[!] URLscan.io : Unauthorized.{RESET}")
        else:
            # Capture code and API message for diagnostic display
            try:
                api_msg = url_resp.json().get('message', url_resp.text[:120])
            except Exception:
                api_msg = url_resp.text[:120]
            urlscan_error = {'code': url_resp.status_code, 'message': api_msg}
            print(f"{YELLOW}[!] URLscan.io: HTTP {url_resp.status_code} "
                  f"(Error details in report section){RESET}")
    except Exception as e:
        urlscan_error = {'code': 'N/A', 'message': str(e)}
        print(f"{RED}[!] URLscan.io : Submission error — {e}{RESET}")

    # VirusTotal submission
    try:
        vt_headers = {'x-apikey': get_vt_key()}
        vt_resp = requests.post(
            'https://www.virustotal.com/api/v3/urls',
            headers=vt_headers,
            data={'url': target_url},
            timeout=15
        )
        if vt_resp.status_code == 200:
            vt_analysis_id = vt_resp.json().get('data', {}).get('id', '')
            vt_submitted   = True
            print(f"{GREEN}[+] VirusTotal : Submitted. Polling in background...{RESET}")
        elif vt_resp.status_code == 401:
            print(f"{RED}[!] VirusTotal : Unauthorized.{RESET}")
        else:
            print(f"{RED}[!] VirusTotal : HTTP {vt_resp.status_code}{RESET}")
    except Exception as e:
        print(f"{RED}[!] VirusTotal : Submission error — {e}{RESET}")

    # ── VT polling in background thread ───────────────────────────────────────
    vt_result = {'attrs': None, 'done': False}

    def _poll_vt():
        if not vt_submitted:
            vt_result['done'] = True
            return
        while True:
            time.sleep(2)
            try:
                r = requests.get(
                    f'https://www.virustotal.com/api/v3/analyses/{vt_analysis_id}',
                    headers={'x-apikey': get_vt_key()},
                    timeout=15
                )
                if r.status_code == 200:
                    a      = r.json().get('data', {}).get('attributes', {})
                    status = a.get('status', '')
                    total  = sum(a.get('stats', {}).values())
                    if status == 'completed' and total > 0:
                        vt_result['attrs'] = a
                        break
            except Exception:
                break
        vt_result['done'] = True

    vt_thread = threading.Thread(target=_poll_vt, daemon=True)
    vt_thread.start()

    # ── URLscan.io polling in main thread (10s intervals) ─────────────────────
    urlscan_data = None
    urlscan_ok   = False

    if urlscan_submitted and urlscan_uuid:
        print(f"\n{YELLOW}[*] Waiting for URLscan.io to finish analysis...{RESET}")

        while True:
            time.sleep(2)
            vt_status_msg = (
                "VirusTotal report is ready but holding for synchronization."
                if vt_result['done'] and vt_result['attrs']
                else "VirusTotal is still scanning."
            )
            try:
                result_resp = requests.get(
                    f'https://urlscan.io/api/v1/result/{urlscan_uuid}/',
                    timeout=15
                )
                if result_resp.status_code == 200:
                    urlscan_data = result_resp.json()
                    urlscan_ok   = True
                    print(f"{GREEN}[+] URLscan.io : Analysis complete.{RESET}")
                    break
                elif result_resp.status_code == 404:
                    smart_print(
                        f"[*] URLscan is still analyzing... {vt_status_msg} (Waiting for results)",
                        color=YELLOW
                    )
                else:
                    print(f"{RED}[!] URLscan.io poll: HTTP {result_resp.status_code}{RESET}")
                    break
            except Exception as e:
                print(f"{RED}[!] URLscan.io poll error: {e}{RESET}")
                break

    # Wait for VT thread to finish before displaying anything
    vt_thread.join(timeout=120)

    # ── Clear polling clutter, then hand off to report sub-menu ───────────────
    os.system('clear')
    print(BANNER)
    _show_report_menu(
        urlscan_data, urlscan_uuid, urlscan_ok,
        vt_result, vt_analysis_id, vt_submitted,
        urlscan_error=urlscan_error
    )

# ─── Module 02 : File Scanner (VirusTotal) ────────────────────────────────────
def scan_file():
    os.system('clear')
    print(BANNER)
    print(f"{GREEN}[::] FILE SCAN MODULE [::]  {RESET}\n")
    print(f"{CYAN}[*] Working directory : {WHITE}{os.getcwd()}{RESET}\n")
    print(f"{GREEN}  upload{RESET}  {WHITE}→ Open file picker (saves as temp_file){RESET}")
    print(f"{GREEN}  scan  {RESET}  {WHITE}→ Submit temp_file to VirusTotal{RESET}")
    print(f"{GREEN}  back  {RESET}  {WHITE}→ Return to main menu{RESET}\n")

    TEMP_FILE = 'temp_file'

    while True:
        cmd = input(f"{GREEN}fire-shield> {RESET}").strip().lower()

        if not cmd:
            continue

        # ── back ───────────────────────────────────────────────────────────────
        if cmd == 'back':
            return

        # ── upload ─────────────────────────────────────────────────────────────
        elif cmd == 'upload':
            filepath_check = os.path.join(os.getcwd(), TEMP_FILE)

            # Cleanup: remove stale temp_file before new pick to avoid wrong scan
            if os.path.isfile(filepath_check):
                try:
                    os.remove(filepath_check)
                except Exception:
                    pass

            print(f"{YELLOW}[*] Opening file picker... Select your file.{RESET}")
            os.system('termux-storage-get temp_file')

            # Race condition fix: give Termux 0.5s to finish writing the file
            time.sleep(0.5)

            # Verify file existence — this is the only truth
            if os.path.isfile(filepath_check):
                print(f"{GREEN}[+] File uploaded successfully and ready to scan.{RESET}")
                print(f"{CYAN}[*] Type 'scan' to submit it to VirusTotal.{RESET}")
            else:
                print(f"{RED}[-] File not uploaded, please try again.{RESET}")

        # ── scan ───────────────────────────────────────────────────────────────
        elif cmd == 'scan':
            filepath = os.path.join(os.getcwd(), TEMP_FILE)
            if not os.path.isfile(filepath):
                print(f"{RED}[!] Error: File not found in current directory.{RESET}")
                print(f"{CYAN}[*] Use 'upload' to pick a file first.{RESET}")
                continue
            break  # File exists — proceed to VT upload below

        # ── unknown command ────────────────────────────────────────────────────
        else:
            print(f"{YELLOW}[!] Unknown command. Valid commands: upload | scan | back{RESET}")

    filepath = os.path.join(os.getcwd(), TEMP_FILE)
    if not os.path.isfile(filepath):
        print(f"\n{RED}[!] Error: File not found in current directory.{RESET}")
        input(f"\n{YELLOW}[*] Press Enter to return to menu...{RESET}")
        return

    # ── File Size Detection ────────────────────────────────────────────────────
    print(f"\n{GREEN}[*] Checking file size...{RESET}")
    file_size = os.path.getsize(filepath)

    try:
        if file_size <= FILE_SIZE_LIMIT:

            # ══════════════════════════════════════════════════════════════════
            # PATH A : Direct Upload (≤ 50 MB)
            # ══════════════════════════════════════════════════════════════════
            print(f"{GREEN}[+] File size is in limit. Sending to API...{RESET}")
            print(f"\n{YELLOW}[*] Uploading 'temp_file' to VirusTotal...{RESET}")

            vt_headers = {'x-apikey': get_vt_key()}
            with open(filepath, 'rb') as f:
                upload_resp = requests.post(
                    'https://www.virustotal.com/api/v3/files',
                    headers=vt_headers,
                    files={'file': (TEMP_FILE, f)},
                    timeout=60
                )

            if upload_resp.status_code == 200:
                analysis_id = upload_resp.json().get('data', {}).get('id', '')
                print(f"{YELLOW}[*] File uploaded. Waiting for VirusTotal engines...{RESET}")

                final_attrs = None
                while True:
                    time.sleep(2)
                    try:
                        poll_resp = requests.get(
                            f'https://www.virustotal.com/api/v3/analyses/{analysis_id}',
                            headers=vt_headers,
                            timeout=15
                        )
                        if poll_resp.status_code == 200:
                            poll_attrs = poll_resp.json().get('data', {}).get('attributes', {})
                            if poll_attrs.get('status', '') == 'completed':
                                final_attrs = poll_attrs
                                break
                            else:
                                print(f"{YELLOW}[*] Analysis in progress... "
                                      f"Retrying in 2s (Waiting for results){RESET}")
                        else:
                            print(f"{RED}[!] Poll error: HTTP {poll_resp.status_code}{RESET}")
                            break
                    except requests.exceptions.ConnectionError:
                        print(f"{RED}[!] Network error during polling.{RESET}")
                        break

                if final_attrs:
                    os.system('clear')
                    print(BANNER)
                    print(f"{GREEN}[::] FILE SCAN RESULTS [::]  {RESET}\n")
                    print(f"{CYAN}[*] Target : temp_file{RESET}")
                    _display_vt_file_report(final_attrs, analysis_id)
                else:
                    print(f"{RED}[!] Analysis could not be retrieved. Check network and try again.{RESET}")

            elif upload_resp.status_code == 401:
                print(f"{RED}[!] Unauthorized.{RESET}")
            else:
                print(f"{RED}[!] Upload failed: HTTP {upload_resp.status_code}{RESET}")

        else:

            # ══════════════════════════════════════════════════════════════════
            # PATH B : Large File — SHA-256 Hash Lookup (> 50 MB)
            # ══════════════════════════════════════════════════════════════════
            size_mb = file_size / (1024 * 1024)
            print(f"{RED}[!] File Size is too large ({size_mb:.1f} MB). "
                  f"File cannot be directly sent to API.{RESET}")

            # Real-time countdown on a single line
            for i in range(5, 0, -1):
                print(f"\r{YELLOW}[*] Proceeding in [{i}] sec...{RESET}",
                      end='', flush=True)
                time.sleep(1)
            print()   # move to next line after countdown

            print(f"\n{GREEN}[+] Automatically proceeding to next action...{RESET}")
            time.sleep(3)

            # Local hashing engine
            print(f"\n{YELLOW}[*] Initializing Local Engine: "
                  f"Analyzing Binary Structure...{RESET}")
            time.sleep(1)
            print(f"{YELLOW}[*] Generating Unique File Signature (SHA-256)...{RESET}")

            sha256     = hashlib.sha256()
            CHUNK_SIZE = 65536   # 64 KB — safe for large files in Termux
            try:
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        sha256.update(chunk)
                file_hash = sha256.hexdigest()
            except Exception as e:
                print(f"{RED}[!] Error reading file: {e}{RESET}")
                input(f"\n{YELLOW}[*] Press Enter to return to menu...{RESET}")
                return

            print(f"{YELLOW}[*] Finalizing Integrity Check...{RESET}")
            time.sleep(0.5)
            print(f"{GREEN}[v] File Hash Generated Successfully{RESET}")
            print(f"{CYAN}    SHA-256 : {file_hash}{RESET}")

            time.sleep(3)
            print(f"\n{YELLOW}[*] Automatically Sending to API for "
                  f"Cloud Intelligence Scan...{RESET}")

            # VT hash lookup — /files/{sha256}
            try:
                vt_headers = {'x-apikey': get_vt_key()}
                hash_resp  = requests.get(
                    f'https://www.virustotal.com/api/v3/files/{file_hash}',
                    headers=vt_headers,
                    timeout=15
                )
                if hash_resp.status_code == 200:
                    vt_data = hash_resp.json().get('data', {}).get('attributes', {})
                    # Remap VT file report keys to match _display_vt_file_report
                    mapped_attrs = {
                        'stats':   vt_data.get('last_analysis_stats',   {}),
                        'results': vt_data.get('last_analysis_results', {}),
                        'status':  'completed',
                    }
                    os.system('clear')
                    print(BANNER)
                    print(f"{GREEN}[::] FILE SCAN RESULTS (Hash Lookup) [::]  {RESET}\n")
                    print(f"{CYAN}[*] Target  : temp_file "
                          f"({size_mb:.1f} MB — hash-based scan){RESET}")
                    print(f"{CYAN}[*] SHA-256 : {file_hash}{RESET}")
                    _display_vt_file_report(mapped_attrs, file_hash, scan_type='file')

                elif hash_resp.status_code == 404:
                    print(f"\n{YELLOW}[~] Hash not found in database. "
                          f"This file is unique or new.{RESET}")

                    # ── Threading-based 10s countdown ─────────────────────────
                    # Input thread reads stdin, main thread drives the clock.
                    answer_box  = {'val': None}
                    input_done  = threading.Event()

                    def _read_input():
                        try:
                            line = sys.stdin.readline()
                            answer_box['val'] = line.strip().lower()
                        except Exception:
                            pass
                        finally:
                            input_done.set()

                    PROMPT = (f"{YELLOW}[?] Upload full file for "
                              f"real-time scan? (y/n)")

                    # Show first tick before starting the thread
                    print(f"\r{PROMPT} [10s] : {RESET}",
                          end='', flush=True)

                    input_thread = threading.Thread(
                        target=_read_input, daemon=True
                    )
                    input_thread.start()

                    # Count: 9 → 0 (9 more ticks = 10s total)
                    for remaining in range(9, -1, -1):
                        if input_done.wait(timeout=1):
                            break          # user pressed Enter
                        if remaining > 0:
                            print(f"\r{PROMPT} [{remaining:02d}s] : {RESET}",
                                  end='', flush=True)

                    print()   # newline after countdown/input

                    answer = answer_box['val']

                    # ── Case B : User declined ────────────────────────────────
                    if answer == 'n':
                        print(f"{RED}[-] Operation cancelled. "
                              f"Returning to main menu.{RESET}")

                    # ── Case A (y) or Case C (timeout) ───────────────────────
                    else:
                        if answer == 'y':
                            print(f"{GREEN}[+] Thanks for confirmation. "
                                  f"File directly sending to API...{RESET}")
                        else:
                            print(f"{GREEN}[+] Automatically directly "
                                  f"sending file to API...{RESET}")

                        print(f"\n{YELLOW}[*] Uploading 'temp_file' "
                              f"to VirusTotal...{RESET}")

                        # ── Progress-tracked upload ───────────────────────────
                        up_result  = {'resp': None, 'err': None}
                        up_done    = threading.Event()
                        up_progress = {
                            'sent':  0,
                            'total': file_size,
                        }

                        class ProgressFileWrapper:
                            """
                            Wraps a file object and intercepts every read()
                            call to track bytes sent in real time.
                            """
                            def __init__(self, fobj, progress):
                                self._fobj     = fobj
                                self._progress = progress

                            def read(self, size=-1):
                                chunk = self._fobj.read(size)
                                self._progress['sent'] += len(chunk)
                                return chunk

                            # requests inspects these attributes
                            def __len__(self):
                                return self._progress['total']

                            @property
                            def len(self):
                                return (self._progress['total']
                                        - self._progress['sent'])

                        def _do_upload():
                            try:
                                vt_up = {'x-apikey': get_vt_key()}

                                # Step 1: get large-file upload URL
                                url_req = requests.get(
                                    'https://www.virustotal.com'
                                    '/api/v3/files/upload_url',
                                    headers=vt_up,
                                    timeout=15
                                )
                                if url_req.status_code == 200:
                                    upload_url = url_req.json().get('data')
                                else:
                                    up_result['err'] = (
                                        f"Could not get upload URL: "
                                        f"HTTP {url_req.status_code}"
                                    )
                                    return

                                # Step 2: upload with progress wrapper
                                with open(filepath, 'rb') as raw_f:
                                    wrapped = ProgressFileWrapper(
                                        raw_f, up_progress
                                    )
                                    up_result['resp'] = requests.post(
                                        upload_url,
                                        headers=vt_up,
                                        files={'file': ('temp_file', wrapped)},
                                        timeout=600
                                    )
                            except Exception as e:
                                up_result['err'] = e
                            finally:
                                up_done.set()

                        up_thread = threading.Thread(
                            target=_do_upload, daemon=True
                        )
                        up_thread.start()

                        # ── Real-time progress bar + ETA ──────────────────────
                        BAR_W      = 20       # width of the filled bar
                        start_ts   = time.time()
                        last_sent  = 0
                        last_ts    = start_ts

                        print()   # blank line before bar

                        while not up_done.wait(timeout=0.5):
                            sent  = up_progress['sent']
                            total = up_progress['total']
                            now   = time.time()

                            # Overall speed (bytes/s) — smoothed over last tick
                            delta_bytes = sent - last_sent
                            delta_time  = max(now - last_ts, 0.001)
                            speed       = delta_bytes / delta_time   # B/s
                            last_sent   = sent
                            last_ts     = now

                            # Progress fraction
                            pct      = sent / total if total > 0 else 0
                            filled   = int(BAR_W * pct)
                            bar      = ('█' * filled
                                        + '░' * (BAR_W - filled))

                            # Human-readable sizes
                            sent_mb  = sent  / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            speed_mb = speed / (1024 * 1024)

                            # ETA
                            remaining = total - sent
                            if speed > 0:
                                eta_s = int(remaining / speed)
                                eta   = (f"{eta_s // 60:02d}m"
                                         f"{eta_s % 60:02d}s")
                            else:
                                eta = '--:--'

                            print(
                                f"\r{YELLOW}[{bar}] "
                                f"{pct*100:5.1f}%  "
                                f"{sent_mb:.1f}/{total_mb:.1f} MB  "
                                f"{speed_mb:.2f} MB/s  "
                                f"ETA {eta}{RESET}",
                                end='', flush=True
                            )

                        # Final 100% bar after upload completes
                        bar      = '█' * BAR_W
                        total_mb = file_size / (1024 * 1024)
                        elapsed  = max(time.time() - start_ts, 0.001)
                        avg_spd  = (file_size / elapsed) / (1024 * 1024)
                        print(
                            f"\r{GREEN}[{bar}] "
                            f"100.0%  "
                            f"{total_mb:.1f}/{total_mb:.1f} MB  "
                            f"{avg_spd:.2f} MB/s  "
                            f"Done          {RESET}"
                        )

                        if up_result['err']:
                            print(f"{RED}[!] Upload error: "
                                  f"{up_result['err']}{RESET}")
                        elif up_result['resp'] is None:
                            print(f"{RED}[!] Upload failed: "
                                  f"No response.{RESET}")
                        elif up_result['resp'].status_code == 200:
                            analysis_id = (up_result['resp'].json()
                                           .get('data', {})
                                           .get('id', ''))
                            print(f"{YELLOW}[*] File uploaded. Waiting "
                                  f"for VirusTotal engines...{RESET}")

                            final_attrs = None
                            while True:
                                time.sleep(2)
                                try:
                                    poll = requests.get(
                                        f'https://www.virustotal.com'
                                        f'/api/v3/analyses/{analysis_id}',
                                        headers={'x-apikey': get_vt_key()},
                                        timeout=15
                                    )
                                    if poll.status_code == 200:
                                        pa = (poll.json()
                                              .get('data', {})
                                              .get('attributes', {}))
                                        if pa.get('status') == 'completed':
                                            final_attrs = pa
                                            break
                                        print(f"{YELLOW}[*] Analysis in "
                                              f"progress... Retrying in 2s "
                                              f"(Waiting for results){RESET}")
                                    else:
                                        print(f"{RED}[!] Poll error: "
                                              f"HTTP {poll.status_code}"
                                              f"{RESET}")
                                        break
                                except requests.exceptions.ConnectionError:
                                    print(f"{RED}[!] Network error "
                                          f"during polling.{RESET}")
                                    break

                            if final_attrs:
                                os.system('clear')
                                print(BANNER)
                                print(f"{GREEN}[::] FILE SCAN RESULTS "
                                      f"[::]  {RESET}\n")
                                print(f"{CYAN}[*] Target  : temp_file "
                                      f"({size_mb:.1f} MB — "
                                      f"full upload){RESET}")
                                print(f"{CYAN}[*] SHA-256 : "
                                      f"{file_hash}{RESET}")
                                _display_vt_file_report(
                                    final_attrs, analysis_id
                                )
                            else:
                                print(f"{RED}[!] Analysis could not "
                                      f"be retrieved.{RESET}")

                        elif up_result['resp'].status_code == 401:
                            print(f"{RED}[!] Unauthorized.{RESET}")
                        else:
                            print(f"{RED}[!] Upload failed: HTTP "
                                  f"{up_result['resp'].status_code}"
                                  f"{RESET}")
                elif hash_resp.status_code == 401:
                    print(f"{RED}[!] Unauthorized — check API key.{RESET}")
                else:
                    print(f"{RED}[!] VT API Error: HTTP {hash_resp.status_code}{RESET}")

            except requests.exceptions.ConnectionError:
                print(f"{RED}[!] Network error during hash lookup.{RESET}")
            except Exception as e:
                print(f"{RED}[!] Error: {e}{RESET}")

    except requests.exceptions.ConnectionError:
        print(f"{RED}[!] Network error during upload.{RESET}")
    except Exception as e:
        print(f"{RED}[!] Error: {e}{RESET}")
    finally:
        # ── Cleanup: delete temp_file regardless of path or outcome ───────────
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
                print(f"\n{CYAN}[*] temp_file deleted from local storage.{RESET}")
            except Exception:
                print(f"\n{YELLOW}[~] Could not delete temp_file. Remove it manually.{RESET}")

    input(f"\n{YELLOW}[*] Press Enter to return to menu...{RESET}")
def scan_ip():
    os.system('clear')
    print(BANNER)
    print(f"{GREEN}[::] IP SCAN MODULE [::]  {RESET}\n")

    ip = input(f"{GREEN}[?] Enter Target IP Address: {RESET}").strip()
    if not ip:
        print(f"\n{RED}[!] No IP entered.{RESET}")
        input(f"\n{YELLOW}[*] Press Enter to return to menu...{RESET}")
        return

    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        print(f"\n{RED}[!] Invalid IP format. Use IPv4 (e.g. 8.8.8.8){RESET}")
        input(f"\n{YELLOW}[*] Press Enter to return to menu...{RESET}")
        return

    print(f"\n{YELLOW}[*] Querying VirusTotal for IP: {ip}{RESET}")
    try:
        vt_headers = {'x-apikey': get_vt_key()}
        resp = requests.get(
            f'https://www.virustotal.com/api/v3/ip_addresses/{ip}',
            headers=vt_headers,
            timeout=15
        )
        if resp.status_code == 200:
            attrs      = resp.json().get('data', {}).get('attributes', {})
            stats      = attrs.get('last_analysis_stats', {})
            country    = attrs.get('country', 'Unknown')
            owner      = attrs.get('as_owner', 'Unknown')
            reputation = attrs.get('reputation', 0)

            print(f"\n{CYAN}  ── IP Intelligence ──{RESET}")
            print(f"  {WHITE}[i] Country    : {country}{RESET}")
            print(f"  {WHITE}[i] Owner/ASN  : {owner}{RESET}")
            print(f"  {WHITE}[i] Reputation : {reputation}{RESET}")
            _display_vt_stats(stats, label="IP Report")
        elif resp.status_code == 404:
            print(f"{YELLOW}[~] IP not found in VirusTotal database.{RESET}")
        elif resp.status_code == 401:
            print(f"{RED}[!] Unauthorized.{RESET}")
        else:
            print(f"{RED}[!] HTTP {resp.status_code}{RESET}")
    except requests.exceptions.ConnectionError:
        print(f"{RED}[!] Network error.{RESET}")
    except Exception as e:
        print(f"{RED}[!] Error: {e}{RESET}")

    input(f"\n{YELLOW}[*] Press Enter to return to menu...{RESET}")

# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    banner()

    while True:
        try:
            choice = show_menu()

            if choice == '01':
                scan_url()
            elif choice == '02':
                scan_file()
            elif choice == '03':
                scan_ip()
            elif choice == '99':
                os.system('clear')
                print(f"\n{RED}[!] Exiting FIRE-SHIELD. Stay Safe.{RESET}\n")
                sys.exit()

        except KeyboardInterrupt:
            os.system('clear')
            print(f"\n{RED}[!] Session interrupted. Exiting...{RESET}\n")
            sys.exit()

if __name__ == "__main__":
    main()
