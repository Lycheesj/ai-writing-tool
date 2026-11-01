"""各ツールの画面項目とプロンプトの定義。

ツールを追加したいときは、TOOLS に1項目足すだけで画面にも反映されます。
"""

COMMON = """あなたは日本語の文章に強い、プロのライティングアシスタントです。
ルール:
- 出力するのは「完成した成果物そのもの」だけ。「以下が〜です」などの前置き・後書き・解説は書かない。
- Markdown記法（#、**、表など）は使わず、そのままメールやチャットに貼り付けられるプレーンテキストで書く。
- 入力に書かれていない事実（日時・金額・固有名詞など）は創作しない。必要な箇所は【　】で穴埋め欄にする。"""

REFINE_CHIPS = ["もっと短く", "もっと丁寧に", "もっとカジュアルに", "具体的に", "箇条書きに", "別の言い回しで"]


def _v(value, fallback="指定なし"):
    return str(value).strip() if value and str(value).strip() else fallback


def _optional(heading, value):
    return f"\n## {heading}\n{value}\n" if value and value.strip() else ""


def _textarea(id, label, rows, required=False, hint="", placeholder=""):
    return {"id": id, "label": label, "type": "textarea", "rows": rows,
            "required": required, "hint": hint, "placeholder": placeholder}


def _text(id, label, hint="", placeholder=""):
    return {"id": id, "label": label, "type": "text", "hint": hint, "placeholder": placeholder}


def _choice(id, label, options, default=None):
    return {"id": id, "label": label, "type": "choice", "options": options,
            "default": default or options[0]}


TOOLS = {
    "email": {
        "icon": "✉️", "name": "メール返信",
        "desc": "受け取ったメールを貼り付けるだけで返信文を作ります。",
        "fields": [
            _textarea("source", "受け取ったメール", 8, required=True, placeholder="返信したいメールをそのまま貼り付け"),
            _textarea("points", "返信で伝えたいこと", 3, hint="任意・箇条書きでOK", placeholder="例: 日程はOK / 資料は金曜までに送る"),
            _choice("relation", "相手", ["社外・取引先", "上司・目上", "同僚", "友人・知人"]),
            _choice("tone", "トーン", ["丁寧", "標準", "カジュアル"], "標準"),
            _choice("length", "長さ", ["短め", "標準", "しっかり"], "標準"),
        ],
        "system": f"""{COMMON}
あなたの役割: 受け取ったメールへの返信文を作成する。
- 1行目に「件名: Re: 〜」を書き、1行空けて本文を書く（元メールに件名がなければ内容から付ける）。
- 宛名、挨拶、本文、結び、署名欄（【署名】）の構成にする。
- 相手の質問・依頼にはすべて漏れなく答える。答えられない点は確認する一文を入れる。""",
        "build": lambda f: f"""## 受信したメール
{_v(f.get("source"), "（なし）")}

## 返信で伝えたいこと（要点・メモ）
{_v(f.get("points"), "特になし。内容に合わせて自然に返信する")}

## 条件
- 相手との関係: {_v(f.get("relation"))}
- トーン: {_v(f.get("tone"))}
- 長さ: {_v(f.get("length"))}""",
    },
    "summary": {
        "icon": "📝", "name": "要約",
        "desc": "長い文章のポイントを短くまとめます。",
        "fields": [
            _textarea("source", "要約したい文章", 12, required=True, placeholder="記事、議事録、メールなど"),
            _choice("style", "形式", ["1行で", "3行要約", "箇条書き", "200字程度", "詳しめ（見出し付き）"], "3行要約"),
            _text("focus", "重視する観点", hint="任意", placeholder="例: 決定事項とToDo"),
        ],
        "system": f"""{COMMON}
あなたの役割: 文章を要約する。
- 原文の主張・結論・数字を正確に残し、意見や推測は加えない。
- 箇条書きは「・」を使う。""",
        "build": lambda f: f"""次の文章を要約してください。

## 形式
{_v(f.get("style"), "3行要約")}
{_optional("特に重視する観点", f.get("focus"))}
## 原文
{_v(f.get("source"), "（なし）")}""",
    },
    "proofread": {
        "icon": "✅", "name": "校正・推敲",
        "desc": "誤字脱字や分かりにくい表現を直し、修正点も示します。",
        "fields": [
            _textarea("source", "チェックしたい文章", 12, required=True),
            _choice("level", "レベル", ["誤字脱字・文法だけ", "読みやすさも改善", "大きく推敲してOK"], "読みやすさも改善"),
        ],
        "system": f"""{COMMON}
あなたの役割: 文章の校正・推敲。
出力は次の2部構成にする（見出しはこの通り）:
【修正後の文章】
（修正した全文）

【主な修正点】
・修正前 → 修正後（理由）を短く。修正がなければ「修正点はありません」。
- 書き手の意図・文体はできるだけ保つ。""",
        "build": lambda f: f"""次の文章を校正してください。

## 校正のレベル
{_v(f.get("level"), "読みやすさも改善")}

## 文章
{_v(f.get("source"), "（なし）")}""",
    },
    "rewrite": {
        "icon": "🔄", "name": "言い換え",
        "desc": "意味はそのままに、トーンや長さを変えます。",
        "fields": [
            _textarea("source", "元の文章", 8, required=True),
            _choice("style", "書き換え方", ["より丁寧に（敬語）", "やわらかく", "カジュアルに", "簡潔に", "分かりやすく（専門用語なし）", "説得力を上げる"]),
            _text("extra", "追加の指示", hint="任意", placeholder="例: 断りの印象をやわらげたい"),
        ],
        "system": f"""{COMMON}
あなたの役割: 文章の内容・意味を変えずに、指定された文体・トーンに書き換える。""",
        "build": lambda f: f"""次の文章を書き換えてください。

## 書き換え方
{_v(f.get("style"), "より丁寧に")}
{_optional("追加の指示", f.get("extra"))}
## 元の文章
{_v(f.get("source"), "（なし）")}""",
    },
    "translate": {
        "icon": "🌐", "name": "翻訳",
        "desc": "自然な表現で翻訳します。",
        "fields": [
            _textarea("source", "原文", 10, required=True),
            _choice("target", "翻訳先", ["英語", "日本語", "中国語（簡体）", "韓国語"]),
            _choice("tone", "文体", ["原文に合わせる", "ビジネス", "カジュアル"]),
        ],
        "system": f"""{COMMON}
あなたの役割: 翻訳者。直訳ではなく、翻訳先の言語のネイティブが自然に書く文章にする。
- 原文の改行・段落構成は保つ。""",
        "build": lambda f: f"""次の文章を「{_v(f.get("target"), "英語")}」に翻訳してください。
文体: {_v(f.get("tone"), "原文に合わせる")}

## 原文
{_v(f.get("source"), "（なし）")}""",
    },
    "draft": {
        "icon": "💡", "name": "文章作成",
        "desc": "メモや箇条書きから文章を書き起こします。",
        "fields": [
            _textarea("source", "メモ・伝えたいこと", 8, required=True, placeholder="箇条書きのメモでOK"),
            _choice("kind", "文章の種類", ["ビジネスメール（新規）", "お知らせ・案内文", "ブログ記事", "SNS投稿", "日報・報告", "謝罪文", "お礼状"]),
            _choice("length", "長さ", ["短め", "おまかせ", "長め"], "おまかせ"),
        ],
        "system": f"""{COMMON}
あなたの役割: メモや箇条書きから、目的に合った文章を書き起こす。
- 読み手にとって分かりやすい構成にする。""",
        "build": lambda f: f"""次のメモをもとに文章を作成してください。

## 文章の種類
{_v(f.get("kind"), "ビジネス文書")}

## 長さ
{_v(f.get("length"), "おまかせ")}

## メモ・伝えたいこと
{_v(f.get("source"), "（なし）")}""",
    },
    "title": {
        "icon": "🏷️", "name": "タイトル案",
        "desc": "タイトル・件名・キャッチコピーの候補を出します。",
        "fields": [
            _textarea("source", "内容", 8, required=True, placeholder="記事の本文や概要"),
            _choice("kind", "種類", ["記事タイトル", "メール件名", "キャッチコピー", "資料のタイトル"]),
            _choice("tone", "雰囲気", ["おまかせ", "まじめ", "キャッチー", "親しみやすい"]),
            _choice("count", "案の数", ["3", "5", "10"], "5"),
        ],
        "system": f"""{COMMON}
あなたの役割: コピーライター。
- 案は番号付きで出し、各案の後ろに（ねらい: 〜）を一言添える。""",
        "build": lambda f: f"""次の内容に合う「{_v(f.get("kind"), "タイトル")}」を{_v(f.get("count"), "5")}案出してください。
雰囲気: {_v(f.get("tone"), "おまかせ")}

## 内容
{_v(f.get("source"), "（なし）")}""",
    },
}
