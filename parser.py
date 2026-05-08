import re

# =====================
# 🔥 KEYWORDS (longer-first + group order matters)
# =====================
KEYWORDS = {
    "bro": ["ညီအစ်ကို", "ညီအကို", "ညီကို"],

    "pat_pu": ["ပတ်ပူးပို", "ပူးပို", "ပတ်ပူး", "ပတ်အကွက်20", "ထိပ်ပိတ်", "ထိပ်နောက်", "ထန", "ထပ"],
    "pat": ["ပတ်သီး", "အပါ", "ပတ်", "ပါ", "ch", "p"],

    "even_brake": ["စုံဘရိတ်", "စဘရိတ်", "စုံbk", "စုံBk", "မbk", "မBk", "မဘရိတ်"],
    "brake": ["ဘရိတ်", "bk", "Bk"],

    "top": ["ထိပ်စီး", "ထိပ်", "top", "Top", "t", "T", "ထ"],

    "power": ["ပါဝါ", "power", "pw", "ပဝ"],
    "nk": ["နက္ခတ်", "nk", "Nk", "နက", "နခ"],

    "ten": ["ဆယ်ပြည့်", "ဆယ်ပြည်", "ဆယ့်ပြည်"],

    # ပိတ် group (single-char "ပ","န" ကို boundary နဲ့ပဲဖမ်းမယ်)
    "pait": ["အပိတ်", "ပိတ်", "နောက်"],

    # ပူး fixed group (အပူး 500 လို digits မပါတဲ့အခါ)
    "puu_fixed": ["အပူးစုံ", "အပူးအစုံ", "အပူးအကုန်", "အပူး", "ပူး", "puu", "ပုး"],

    # စပူး/မပူး => 5 ကွက်
    "so_pu": ["စပူး", "စုံပူး", "မပူး"],

    # စစ/မမ/စမ... => 25 ကွက်
    "sam": ["စုံစုံ", "စုံမ", "စစ", "မမ", "စမ", "မစ", "စုူံစူံ", "စူံစုံ", "စုံစူံ"],

    # ခွေ / ခွေပူး
    "khwe_pu": ["အပူးပါခွေပူး", "အပူးပါခွေ", "အပူးအပြီးပါ", "ခွေပူး", "အခွေပူး", "ခပ", "ခွေပူး"],
    "khwe": ["အခွေ", "ခွေ", "ခ"],

    # ကပ်
    "kap": ["အကပ်", "ကပ်", "ကို"],

    # direct marker (ဒါမတွေ့ရင်လည်း default direct ပဲ)
    "direct": ["ဒဲ့", "=", "-", "*", "/", ".", ":"],
}

RULE_ORDER = [
    "bro",
    "pat_pu",
    "pat",
    "even_brake",
    "brake",
    "top",
    "power",
    "nk",
    "ten",
    "pait",
    "khwe_pu",
    "khwe",
    "kap",
    "so_pu",
    "sam",
    "puu_fixed",
    "direct",
]

SEPS_CLASS = r"[ \t,\-*/=.:]"


def _contains_token(text: str, token: str) -> bool:
    """single-char (e.g. 'ပ','န') ကိုတော့ separator boundary နဲ့ပဲ match လုပ်"""
    if not token:
        return False
    t = text.lower()
    k = token.lower()

    # ASCII tokens: simple contains
    if re.fullmatch(r"[a-z0-9]+", k):
        return k in t

    # single Burmese char => require boundary
    if len(k) == 1:
        return re.search(rf"(?:^|{SEPS_CLASS}){re.escape(k)}(?:$|{SEPS_CLASS})", t) is not None

    return k in t


def detect_rule(line: str) -> str:
    for rule in RULE_ORDER:
        for k in KEYWORDS.get(rule, []):
            if _contains_token(line, k):
                return rule
    return "direct"


def has_reverse_marker(line: str) -> bool:
    """
    Reverse marker (r/R/အာ) ကို သပ်သပ်ဖမ်း။
    IMPORTANT: "600R400" လို amount split က R ကို reverse marker မယူ (delimiter အနေနဲ့သာယူ)
    """
    # r/အာ standalone or with space: " r300", "အာ300"
    if re.search(r"(?i)(?:^|[^a-z0-9])(r|အာ)\s*\d*", line):
        return True

    # "12r500" style (2digit r amount) ကို reverse marker လို့ယူ
    if re.search(r"(?i)\b\d{1,2}\s*r\s*\d+\b", line):
        return True

    return False


def split_bets_and_amounts(line: str):
    """
    return:
      bets: list[str]  (amount numbers removed)
      amount_sum: int  (normal amount + (amountRamount ရှိရင်) R amount)
      rev_flag: bool   (reverse marker exists => ကွက် 2 ဆ)

    Support:
      - "... 600R400" / "...=500R250"  => amount_sum=600+400, rev_flag=False
      - "... r300" / "...64r50"        => amount_sum=300/50, rev_flag=True
    """
    raw = line
    raw_l = raw.lower()

    # 0) amount split at end: 600R400 / 150r100  (left>=100 => amount)
    base_amount = 0
    r_amount = 0

    m = re.search(r"(\d{3,})\s*[rR]\s*(\d+)\s*$", raw_l)
    if m:
        base_amount = int(m.group(1))
        r_amount = int(m.group(2))
        # remove trailing "...600R400"
        raw_l = raw_l[: m.start()].strip()
        # IMPORTANT: delimiter R ကို reverse marker မယူ
        rev_flag = has_reverse_marker(raw_l)
    else:
        rev_flag = has_reverse_marker(raw_l)

    # 1) trailing reverse-only amount: "... r300" OR "...64r50"
    r_only = 0

    # case A: " ... r300" or " ... အာ300"
    m2 = re.search(r"(?i)(?:^|[^a-z0-9])(r|အာ)\s*(\d+)\s*$", raw_l)
    if m2:
        r_only = int(m2.group(2))
        raw_l = raw_l[: m2.start()].strip()
        rev_flag = True

    else:
        # case B: "...64r50" (space မခြား)
        m3 = re.search(r"(?i)(\d{1,2})\s*r\s*(\d+)\s*$", raw_l)
        if m3 and base_amount == 0 and r_amount == 0:
            # group reverse amount လို့ယူ (bets ထဲမှာ 64 ပါသင့်)
            r_only = int(m3.group(2))
            # keep left number as bet: replace "64r50" -> "64"
            raw_l = raw_l[: m3.start()].strip() + " " + m3.group(1)
            raw_l = raw_l.strip()
            rev_flag = True

    # 2) remaining numbers
    nums = [m.group(0) for m in re.finditer(r"\d+", raw_l)]

    # 3) normal amount
    normal_amount = 0
    bets = nums

    if base_amount or r_amount:
        # already got amounts
        normal_amount = 0
    else:
        # heuristic: normal amount usually >= 3 digits (500,1000,5000...)
        idx_amount = None
        for i in range(len(nums) - 1, -1, -1):
            if len(nums[i]) >= 3:
                idx_amount = i
                break

        # if no >=3-digit and no r_only and len(nums)>=2 => last number is amount
        if idx_amount is None and r_only == 0 and len(nums) >= 2:
            idx_amount = len(nums) - 1

        if idx_amount is not None and nums:
            normal_amount = int(nums[idx_amount])
            bets = [n for j, n in enumerate(nums) if j != idx_amount]

    amount_sum = normal_amount + base_amount + r_amount + r_only
    return bets, amount_sum, rev_flag


def calculate(rule: str, bets: list[str], amount_sum: int, rev_flag: bool):
    # base slots
    if rule == "bro":
        base = 20

    elif rule == "pat":
        base = 19

    elif rule == "pat_pu":
        base = 20

    elif rule in ("top", "brake"):
        # each bet digit => 10 slots (3ထိပ် + 8ထိပ် => 20)
        base = (len(bets) * 10) if bets else 10

    elif rule in ("power", "nk", "pait", "ten"):
        base = 10

    elif rule == "puu_fixed":
        # "အပူး 500" => 10 slots
        base = 10

    elif rule == "so_pu":
        base = 5

    elif rule == "sam":
        base = 25

    elif rule == "khwe":
        digits = "".join(bets)
        n = len(digits)
        base = n * (n - 1)

    elif rule == "khwe_pu":
        digits = "".join(bets)
        n = len(digits)
        base = n * n

    elif rule == "kap":
        # a×b where a,b are digit lengths of first two bet numbers
        if len(bets) >= 2:
            base = len(bets[0]) * len(bets[1])
        else:
            base = 0

    else:  # direct
        base = len(bets)

    # if "ပူး" keyword but bets ပါနေပြီး digits>=3 ဆို khwe_pu သဘောတရားထား (123ပူး)
    if rule == "puu_fixed" and bets:
        digits = "".join(bets)
        if len(digits) >= 3:
            base = len(digits) * len(digits)  # N×N

    # Reverse => base 2 ဆ (ကွက် ၂ ဆ)
    eff_base = base * 2 if rev_flag else base

    total = eff_base * amount_sum
    return eff_base, total


def parse_message(text: str):
    """
    newline အလိုက် line တွေခွဲပြီး line တစ်ခုချင်း စည်းကမ်းအလိုက် total ထုတ်ပေး
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    results = []
    grand_total = 0

    for line in lines:
        # "Hazel:" လို prefix ဖယ်
        line2 = re.sub(r"^\s*[^:]{1,30}:\s*", "", line)

        rule = detect_rule(line2)
        bets, amount_sum, rev_flag = split_bets_and_amounts(line2)

        base, total = calculate(rule, bets, amount_sum, rev_flag)

        grand_total += total
        results.append(
            {
                "raw": line,
                "rule": rule,
                "base": int(base),
                "amount_sum": int(amount_sum),
                "total": int(total),
            }
        )

    return {"lines": results, "grand_total": int(grand_total)}
