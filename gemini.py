"""Gemini API の呼び出し。文章を少しずつ返し、失敗時は GenerationError を投げる。"""

import os
from pathlib import Path

import truststore

# Windows の証明書ストアで検証する（ウイルス対策ソフトがHTTPS通信を検査するPCでも接続できるように）
truststore.inject_into_ssl()

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from tools import TOOLS

DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.1-flash-lite"  # DEFAULT_MODEL が混雑などで使えないときに切り替える
TIMEOUT_MS = 60_000
ENV_PATH = Path(__file__).parent / ".env"
PLACEHOLDER_KEY = "your-api-key-here"


class GenerationError(Exception):
    """画面にそのまま表示できるメッセージを持つエラー。"""


def _build_contents(request):
    prompt = TOOLS[request["tool"]]["build"](request["fields"])
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    refine = request.get("refine")
    if refine:
        contents.append(types.Content(role="model", parts=[types.Part(text=refine["previous"])]))
        contents.append(types.Content(role="user", parts=[types.Part(
            text=f"上の出力を次の指示に従って書き直してください（出力ルールは同じ）:\n{refine['instruction']}"
        )]))
    return contents


def _can_try_next_model(err):
    """モデルの混雑や提供終了なら次のモデルを試す。キーの誤りなどは試しても直らない。"""
    if not isinstance(err, errors.APIError):
        return True
    return err.code in (404, 429) or (err.code or 0) >= 500


def _error_message(err, model):
    if not isinstance(err, errors.APIError):
        if "timed out" in str(err):
            return "AIから時間内に応答がありませんでした。混み合っている可能性があります。少し時間をおいてお試しください。"
        return f"AIサーバーに接続できないか、予期しないエラーが発生しました: {err}"
    code = err.code
    if code == 404:
        return f"モデル「{model}」が見つかりません。.env の GEMINI_MODEL を確認してください。"
    if code == 429:
        return "利用上限に達したか、混み合っています。少し時間をおいてもう一度お試しください。"
    if code in (401, 403) or "API key" in str(err):
        return "APIキーが正しくないか、権限がありません。.env の GEMINI_API_KEY を確認してください。"
    if code and code >= 500:
        return f"AIサーバーが混み合っているか、エラーが発生しました（{code}）。少し時間をおいてお試しください。"
    return f"リクエストエラー（{code}）: {err.message}"


def stream(request):
    """request = {"tool", "fields", "refine"(任意)} から生成した文章を順に返す。"""
    load_dotenv(ENV_PATH, override=True)  # .env を書き換えたら再起動なしで反映する
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key or api_key == PLACEHOLDER_KEY:
        raise GenerationError(
            "APIキーが設定されていません。.env ファイルの GEMINI_API_KEY に自分のキーを書いてください。"
        )
    configured = (os.environ.get("GEMINI_MODEL") or "").strip()
    models = [configured] if configured else [DEFAULT_MODEL, FALLBACK_MODEL]

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    contents = _build_contents(request)
    config = types.GenerateContentConfig(system_instruction=TOOLS[request["tool"]]["system"])

    for model in models:
        has_text = False
        finish_reason = None
        block_reason = None
        try:
            for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
                if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                    block_reason = chunk.prompt_feedback.block_reason
                if chunk.candidates and chunk.candidates[0].finish_reason:
                    finish_reason = chunk.candidates[0].finish_reason
                if chunk.text:
                    has_text = True
                    yield chunk.text
        except Exception as err:
            # 文章を表示し始める前なら、次のモデルで生成し直す
            if not has_text and model != models[-1] and _can_try_next_model(err):
                continue
            raise GenerationError(_error_message(err, model)) from err

        if finish_reason == types.FinishReason.MAX_TOKENS:
            raise GenerationError("出力が長すぎて途中で終わりました。")
        if block_reason or (finish_reason and finish_reason != types.FinishReason.STOP):
            raise GenerationError("この内容はAIが対応できませんでした。表現を変えてお試しください。")
        return
