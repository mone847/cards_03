from js import document, window
import random
import asyncio

# ---- DOM ----
p_img = document.getElementById("p-card")
c_img = document.getElementById("c-card")
status = document.getElementById("status")

draw_btn = document.getElementById("draw-btn")
nav = document.getElementById("nav")
step_btn = document.getElementById("step-btn")
back_btn = document.getElementById("back-btn")

summary = document.getElementById("summary")
sum_img_p = document.getElementById("sum-img-p")
sum_img_c = document.getElementById("sum-img-c")
sum_title = document.getElementById("sum-title")
sum_body = document.getElementById("sum-body")

# ---- game state ----
_cards = None
deck = []                    # 1..52
rounds_total = 5
round_no = 0
busy = False

# 取り札（カードindexを保持）
taken_p = []
taken_c = []

# 終了後の表示ステップ
# 1:画像 2:文字化 3:並べ替え 4:式表示 5:答え合わせ
step = 1

# ---- helpers ----
async def ensure_cards():
    global _cards
    if _cards is not None:
        return _cards
    while not hasattr(window, "cards"):
        await asyncio.sleep(0)
    _cards = window.cards
    return _cards

def card_to_suit_rank(i: int):
    """
    c1..c52 の並び「クラブ→ダイヤ→ハート→スペード（各A..K）」
    """
    if i < 1 or i > 52:
        return ("?", 0)
    suit_index = (i - 1) // 13  # 0..3
    rank = (i - 1) % 13 + 1     # 1..13
    suits = ["♣", "♦", "♥", "♠"]  # マーク順
    return (suits[suit_index], rank)

def is_red(suit: str) -> bool:
    return suit in ["♦", "♥"]

def signed_value(i: int) -> int:
    suit, rank = card_to_suit_rank(i)
    return -rank if is_red(suit) else rank

def abs_value(i: int) -> int:
    suit, rank = card_to_suit_rank(i)
    return rank

def token(i: int, with_sign=False) -> str:
    suit, rank = card_to_suit_rank(i)
    color = "red" if is_red(suit) else "black"
    val = signed_value(i)
    if with_sign:
        s = f"{'＋' if val >= 0 else '－'}{abs(val)}"
        txt = f"({s})"
    else:
        txt = f"{suit}{rank}"
    return (color, txt)

def clear_node(node):
    while node.firstChild:
        node.removeChild(node.firstChild)

def img_tag(src):
    img = document.createElement("img")
    img.src = src
    return img

def span_token(color, text):
    sp = document.createElement("span")
    sp.className = "red" if color == "red" else "black"
    sp.innerText = text
    return sp

def compute_plus_minus(cards_list):
    plus = sum(v for v in (signed_value(i) for i in cards_list) if v > 0)
    minus = sum(v for v in (signed_value(i) for i in cards_list) if v < 0)  # 負の合計
    total = plus + minus
    return plus, minus, total

def update_status(extra=""):
    remaining = len(deck)
    status.innerText = (
        f"ラウンド: {round_no}/{rounds_total}\n"
        f"残りカード: {remaining}枚\n"
        f"{extra}"
    )

async def show_back():
    cards = await ensure_cards()
    back = cards.getUrl(0)
    p_img.src = back
    c_img.src = back
    p_img.classList.add("ready")
    c_img.classList.add("ready")

# ---- endgame rendering ----
def render_step():
    # step 1 は「画像一覧」を表示、2以降は sum_body に出す（画像は消す）
    clear_node(sum_title)
    clear_node(sum_body)

    if step == 1:
        # 画像を表示
        sum_title.innerText = ""
        sum_img_p.style.display = "flex"
        sum_img_c.style.display = "flex"
        sum_body.innerText = "②〜⑤は「文字化」ボタンで進みます。"
        step_btn.innerText = "文字化"
        back_btn.disabled = True
        return

    # 2以降は画像を隠す（条件②）
    sum_img_p.style.display = "none"
    sum_img_c.style.display = "none"
    back_btn.disabled = False

    if step == 2:
        sum_title.innerText = "② 文字キャラクタ表示"
        step_btn.innerText = "並べ替え"
        body = document.createElement("div")
        body.className = "tokens"
        body.appendChild(document.createTextNode("あなた： "))
        for i in taken_p:
            color, t = token(i, with_sign=False)
            body.appendChild(span_token(color, t))
        body.appendChild(document.createElement("br"))
        body.appendChild(document.createTextNode("コンピュータ： "))
        for i in taken_c:
            color, t = token(i, with_sign=False)
            body.appendChild(span_token(color, t))
        sum_body.appendChild(body)
        return

    if step == 3:
        sum_title.innerText = "③ 並べ替え（黒→赤）"
        step_btn.innerText = "式表示"

        def sort_key(i):
            # 黒先、赤後、同色内は絶対値小→大
            suit, rank = card_to_suit_rank(i)
            return (1 if is_red(suit) else 0, rank)

        body = document.createElement("div")
        body.className = "tokens"

        body.appendChild(document.createTextNode("あなた： "))
        for i in sorted(taken_p, key=sort_key):
            color, t = token(i, with_sign=False)
            body.appendChild(span_token(color, t))

        body.appendChild(document.createElement("br"))
        body.appendChild(document.createTextNode("コンピュータ： "))
        for i in sorted(taken_c, key=sort_key):
            color, t = token(i, with_sign=False)
            body.appendChild(span_token(color, t))

        sum_body.appendChild(body)
        return

    if step == 4:
        sum_title.innerText = "④ 式表示（(＋) / (－)・色付き）"
        step_btn.innerText = "答え合わせ"

        def render_expr(cards_list):
            container = document.createElement("div")
            container.className = "tokens"
            first = True
            for i in cards_list:
                color, t = token(i, with_sign=True)
                if not first:
                    container.appendChild(document.createTextNode("＋"))
                container.appendChild(span_token(color, t))
                first = False
            if len(cards_list) == 0:
                container.innerText = "（なし）"
            return container

        body = document.createElement("div")
        body.appendChild(document.createTextNode("あなた： "))
        body.appendChild(render_expr(taken_p))
        body.appendChild(document.createElement("br"))
        body.appendChild(document.createTextNode("コンピュータ： "))
        body.appendChild(render_expr(taken_c))

        sum_body.appendChild(body)
        return

    if step == 5:
        sum_title.innerText = "⑤ 答え合わせ（＋合計・－合計・合計点）"
        step_btn.innerText = "答え合わせ（完了）"
        step_btn.disabled = True

        p_plus, p_minus, p_total = compute_plus_minus(taken_p)
        c_plus, c_minus, c_total = compute_plus_minus(taken_c)

        if p_total > c_total:
            winner = "あなたの勝ち！"
        elif p_total < c_total:
            winner = "コンピュータの勝ち！"
        else:
            winner = "引き分け！"

        txt = (
            f"本人： ＋{p_plus}、 {p_minus}、 合計 {p_total}\n"
            f"コンピュータ： ＋{c_plus}、 {c_minus}、 合計 {c_total}\n"
            f"\n{winner}"
        )
        pre = document.createElement("pre")
        pre.innerText = txt
        sum_body.appendChild(pre)
        return

def show_summary_images():
    # ① 画像表示（小さく並べる）
    clear_node(sum_img_p)
    clear_node(sum_img_c)

    # URLを作って並べる
    cards = _cards
    for i in taken_p:
        sum_img_p.appendChild(img_tag(cards.getUrl(i)))
    for i in taken_c:
        sum_img_c.appendChild(img_tag(cards.getUrl(i)))

# ---- game flow ----
async def reset_async():
    global deck, round_no, taken_p, taken_c, step
    cards = await ensure_cards()

    await show_back()
    deck = list(range(1, 53))
    random.shuffle(deck)

    round_no = 0
    taken_p = []
    taken_c = []
    step = 1

    # UI reset
    draw_btn.disabled = False
    nav.style.display = "none"
    step_btn.disabled = False
    summary.style.display = "none"

    update_status("開始！「カードを引く（1回）」を押してください。")

async def end_game_async():
    # 終了画面へ
    summary.style.display = "block"
    nav.style.display = "block"
    draw_btn.disabled = True
    step_btn.disabled = False

    # ①の画像を作って表示
    show_summary_images()
    render_step()

async def draw_once_async():
    global busy, round_no, step
    if busy:
        return
    busy = True
    try:
        cards = await ensure_cards()

        if round_no >= rounds_total:
            update_status("規定回数が終わりました。")
            return

        if len(deck) < 2:
            update_status("カードが足りません。リセットしてください。")
            return

        # 1枚ずつ引く
        p = deck.pop()
        c = deck.pop()

        p_img.src = cards.getUrl(p)
        c_img.src = cards.getUrl(c)

        # 勝敗：絶対値の大きい方が2枚とも取る
        ap, ac = abs_value(p), abs_value(c)

        # 同値はルール未指定なので「各自1枚ずつ」にしています（必要なら変更可）
        if ap > ac:
            taken_p.extend([p, c])
            msg = "あなたが2枚獲得！"
        elif ap < ac:
            taken_c.extend([p, c])
            msg = "コンピュータが2枚獲得！"
        else:
            taken_p.append(p)
            taken_c.append(c)
            msg = "同じ絶対値：それぞれ1枚ずつ"

        round_no += 1

        # ラウンド中の状況表示（いったん暫定）
        p_plus, p_minus, p_total = compute_plus_minus(taken_p)
        c_plus, c_minus, c_total = compute_plus_minus(taken_c)

        extra = (
            f"{msg}\n"
            f"（途中経過）あなた 合計 {p_total} / コンピュータ 合計 {c_total}"
        )
        update_status(extra)

        if round_no >= rounds_total:
            update_status(extra + "\n\n規定回数終了。下のボタンで結果表示へ。")
            await end_game_async()

    finally:
        busy = False

# ---- button handlers (sync) ----
def reset_game(event=None):
    asyncio.create_task(reset_async())

def draw_once(event=None):
    asyncio.create_task(draw_once_async())

def next_step(event=None):
    global step
    if step < 5:
        step += 1
        render_step()

def prev_step(event=None):
    global step
    if step > 1:
        step -= 1
        # ⑤で無効化したのを戻す
        if step_btn.disabled:
            step_btn.disabled = False
        render_step()

# init
asyncio.create_task(reset_async())