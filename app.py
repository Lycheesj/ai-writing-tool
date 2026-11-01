"""個人用 AIライティングツール（Streamlit + Gemini API）。"""

import streamlit as st

import gemini
from tools import REFINE_CHIPS, TOOLS

st.set_page_config(page_title="AIライティング", page_icon="✍️", layout="wide")
# 結果欄（コピーボタン付きのコード表示）を読みやすい通常フォントで表示する
st.markdown('<style>[data-testid="stCode"] code {font-family: inherit;}</style>', unsafe_allow_html=True)

state = st.session_state
state.setdefault("inputs", {})          # ツールごとの入力値
state.setdefault("request", None)       # これから生成するリクエスト
state.setdefault("running", None)       # 生成中のリクエスト
state.setdefault("partial", "")         # 生成途中の文章
state.setdefault("output", "")
state.setdefault("error", "")
state.setdefault("last_request", None)  # 「別の案」「手直し」用


def finish_generation(text, error=""):
    request = state.running
    state.running = None
    state.partial = ""
    state.output = text
    state.error = error if text else (error or "結果が空でした。もう一度お試しください。")
    if text:
        state.last_request = {"tool": request["tool"], "fields": request["fields"]}


# 生成中に画面を操作すると、Streamlit は実行中の処理を止めて最初からやり直す。
# 「停止」も含め、そこまでに届いた文章を結果として残す（同じ生成を再実行しない）。
if state.running is not None:
    finish_generation(state.partial, "" if state.partial else "停止しました。")


def start(request):
    state.request = request


def refine(instruction):
    instruction = instruction.strip()
    if instruction and state.last_request and state.output:
        start({**state.last_request, "refine": {"previous": state.output, "instruction": instruction}})


def render_field(field, values, widget_key):
    label = field["label"] + (f"（{field['hint']}）" if field.get("hint") else "")
    current = values.get(field["id"])
    if field["type"] == "choice":
        options = field["options"]
        index = options.index(current) if current in options else options.index(field["default"])
        return st.radio(label, options, index=index, horizontal=True, key=widget_key)
    if field["type"] == "textarea":
        return st.text_area(label, value=current or "", height=field["rows"] * 28 + 16,
                            placeholder=field["placeholder"], key=widget_key)
    return st.text_input(label, value=current or "", placeholder=field["placeholder"], key=widget_key)


# ===== サイドバー =====
with st.sidebar:
    st.title("✍️ AIライティング")
    tool_id = st.radio(
        "ツール", list(TOOLS), key="tool_id", label_visibility="collapsed",
        format_func=lambda id: f"{TOOLS[id]['icon']} {TOOLS[id]['name']}",
    )

tool = TOOLS[tool_id]
st.header(f"{tool['icon']} {tool['name']}")
st.caption(tool["desc"])
left, right = st.columns(2, gap="large")

# ===== 入力 =====
with left:
    with st.form(f"form_{tool_id}", border=True):
        saved = state.inputs.get(tool_id, {})
        fields = {f["id"]: render_field(f, saved, f"{tool_id}_{f['id']}") for f in tool["fields"]}
        submitted = st.form_submit_button("作成する", type="primary")
        st.caption("文章の入力中は Ctrl + Enter でも実行できます")
    if submitted:
        state.inputs[tool_id] = fields
        missing = next((f for f in tool["fields"] if f.get("required") and not fields[f["id"]].strip()), None)
        if missing:
            st.warning(f"「{missing['label']}」を入力してください")
        else:
            start({"tool": tool_id, "fields": fields})

# ===== 結果 =====
with right:
    st.subheader("結果")
    request, state.request = state.request, None
    if request:
        state.running = request
        state.partial = ""
        st.button("停止")  # 押すと再実行され、冒頭の処理が途中までの文章を残す
        box = st.empty()
        box.info("考え中…")
        error = ""
        try:
            for piece in gemini.stream(request):
                state.partial += piece
                box.code(state.partial, language=None, wrap_lines=True)
        except gemini.GenerationError as err:
            error = str(err)
        finish_generation(state.partial, error)
        st.rerun()

    if state.error:
        if state.output:
            st.warning(state.error)
        else:
            st.error(state.error)
    if state.output:
        st.code(state.output, language=None, wrap_lines=True)
        st.caption("右上のアイコンでコピーできます")
        st.button("別の案", on_click=start, args=(state.last_request,))
        st.write("**手直し**")
        chips = st.columns(3)
        for i, chip in enumerate(REFINE_CHIPS):
            chips[i % 3].button(chip, key=f"chip_{i}", on_click=refine, args=(chip,), width="stretch")
        with st.form("refine_form", clear_on_submit=True, border=False):
            st.text_input("手直しの指示", key="refine_input", placeholder="例: 2段落目をもっと具体的に")
            st.form_submit_button("手直しする", on_click=lambda: refine(state.refine_input))
    elif not state.error:
        st.info("左に入力して「作成する」を押すと、ここに結果が表示されます。")
