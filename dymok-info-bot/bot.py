#!/usr/bin/env python3
"""Private-chat FAQ bot. Python 3.9+, standard library only."""
import argparse
import json
import logging
import os
from pathlib import Path
import re
import signal
import socket
import threading
import unicodedata
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
LOG = logging.getLogger("info_bot")


class SetupError(ValueError):
    """A locally authored error safe to show without exposing runtime data."""


class ApiError(Exception):
    def __init__(self, code, retry_after=0):
        self.code = code
        self.retry_after = max(0, int(retry_after))
        # Never expose server descriptions, URLs, tokens or message contents.
        super().__init__("Помилка зв’язку з Telegram (код {}).".format(code))


class Telegram:
    def __init__(self, token):
        if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{20,}", token):
            raise SetupError("Перевірте TELEGRAM_BOT_TOKEN у файлі .env.")
        self._url = "https://api.telegram.org/bot" + token + "/"

    def call(self, method, **payload):
        request = urllib.request.Request(
            self._url + method,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            code, retry = error.code, 0
            try:
                body = json.loads(error.read())
                retry = body.get("parameters", {}).get("retry_after", 0)
            except (ValueError, TypeError, AttributeError):
                pass
            raise ApiError(code, retry) from None
        except (urllib.error.URLError, OSError, socket.timeout):
            raise ApiError(0) from None
        except (ValueError, UnicodeError):
            raise ApiError(0) from None
        if not isinstance(result, dict):
            raise ApiError(0)
        if not result.get("ok"):
            raise ApiError(result.get("error_code", 0),
                           result.get("parameters", {}).get("retry_after", 0))
        return result.get("result")


def load_env(path):
    """Read key=value without executing shell code or overwriting environment."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep and key.strip() == "TELEGRAM_BOT_TOKEN":
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


class Knowledge:
    def __init__(self, path=ROOT / "faq.json"):
        self.data = json.loads(path.read_text(encoding="utf-8"))
        if set(self.data["topics"]) != {"service", "returns", "privacy", "age"}:
            raise ValueError("Перевірте розділи faq.json.")
        for item in self.data["topics"].values():
            if not item["title"] or not item["keywords"] or not item["answer"]:
                raise ValueError("У довідці є порожній розділ.")
            if len(item["answer"]) > 3500:
                raise ValueError("Скоротіть відповідь у довідці до 3500 символів.")

    def menu(self, topics=None):
        keys = list(topics) if topics else list(self.data["topics"])
        buttons = [{"text": self.data["topics"][key]["title"],
                    "callback_data": "faq:" + key} for key in keys]
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        rows.append([{"text": "🏠 Головне меню", "callback_data": "faq:home"}])
        return {"inline_keyboard": rows}

    def answer(self, text):
        normalized = unicodedata.normalize("NFKC", text).casefold().strip()
        command = normalized.split(maxsplit=1)[0].split("@")[0] if normalized else ""
        commands = {"/returns": "returns", "/privacy": "privacy", "/age": "age",
                    "/service": "service"}
        if command in commands:
            return self.data["topics"][commands[command]]["answer"], self.menu()
        if command in {"/start", "/help", "/menu"} or normalized in {
            "меню", "привіт", "вітаю", "добрий день", "добрий вечір"
        }:
            return self.data["welcome"], self.menu()
        def matches_keyword(word):
            # Ukrainian stems match word starts; English terms and numbers are whole words.
            suffix = r"(?!\w)" if word.isascii() else ""
            return re.search(r"(?<!\w)" + re.escape(word) + suffix, normalized)

        matches = [key for key, item in self.data["topics"].items()
                   if any(matches_keyword(word) for word in item["keywords"])]
        if len(matches) == 1:
            return self.data["topics"][matches[0]]["answer"], self.menu()
        if len(matches) > 1:
            return "У запитанні є кілька тем. Яку відкрити?", self.menu(matches)
        return self.data["fallback"], self.menu()


class Bot:
    def __init__(self, api, knowledge):
        self.api = api
        self.knowledge = knowledge

    def handle(self, update):
        callback = update.get("callback_query")
        if callback:
            try:
                self.api.call("answerCallbackQuery", callback_query_id=callback["id"])
            except ApiError as error:
                if error.code != 400:  # An expired button should still give an answer.
                    raise
            message = callback.get("message", {})
            chat = message.get("chat", {})
            if chat.get("type") != "private":
                return
            topic = self.knowledge.data["topics"].get(
                callback.get("data", "").removeprefix("faq:"))
            text = topic["answer"] if topic else self.knowledge.data["welcome"]
            markup = self.knowledge.menu()
        else:
            message = update.get("message", {})
            chat = message.get("chat", {})
            if chat.get("type") != "private" or message.get("from", {}).get("is_bot"):
                return
            if "text" in message:
                text, markup = self.knowledge.answer(message["text"])
            else:
                text = ("Я працюю з текстовими запитаннями та кнопками. "
                        "Файли, контакти й геолокацію не зберігаю та не пересилаю. "
                        "Оберіть тему нижче.")
                markup = self.knowledge.menu()
        self.api.call("sendMessage", chat_id=chat["id"], text=text,
                      reply_markup=markup,
                      link_preview_options={"is_disabled": True})


class Cursor:
    def __init__(self, path):
        self.path = path
        self.offset = 0
        if path.exists():
            self.offset = int(path.read_text(encoding="ascii"))
            if self.offset < 0:
                raise SetupError("Некоректний файл стану. Перевірте state/offset.")

    def commit(self, update_id):
        self.offset = int(update_id) + 1
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(str(self.offset), encoding="ascii")
        temporary.replace(self.path)


def run(api, knowledge, state_dir, stop):
    # macOS/Linux: prevent two local pollers from using the same state.
    import fcntl
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state_dir / "bot.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SetupError("Бот уже запущений у цій папці.") from None
        api.call("getMe")
        if api.call("getWebhookInfo").get("url"):
            raise SetupError("У цього бота вже активне інше підключення (webhook). "
                             "Використайте окремого бота; поточне підключення не змінено.")
        cursor = Cursor(state_dir / "offset")
        bot = Bot(api, knowledge)
        LOG.info("Довідковий бот працює. Для зупинки натисніть Ctrl+C.")
        delay = 1
        while not stop.is_set():
            try:
                updates = api.call("getUpdates", offset=cursor.offset, timeout=30,
                                   allowed_updates=["message", "callback_query"])
                for update in updates:
                    if stop.is_set():
                        break
                    if update["update_id"] < cursor.offset:
                        continue
                    try:
                        bot.handle(update)
                    except ApiError as error:
                        if error.code not in {400, 403}:
                            raise
                        LOG.warning("Відповідь недоступна або чат заблокований; подію пропущено.")
                    cursor.commit(update["update_id"])
                delay = 1
            except ApiError as error:
                if error.code in {401, 404, 409}:
                    raise
                LOG.warning("Telegram тимчасово недоступний. З’єднання буде повторено.")
                # Event.wait lets Ctrl+C / SIGTERM interrupt any retry immediately.
                stop.wait(max(delay, error.retry_after))
                delay = min(delay * 2, 60)


def main():
    parser = argparse.ArgumentParser(description="Довідковий Telegram-бот")
    parser.add_argument("--check", action="store_true", help="Перевірити довідку без мережі")
    parser.add_argument("--demo", action="store_true", help="Локальний діалог без Telegram")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        knowledge = Knowledge()
        if args.check:
            print("Довідка коректна. Доступні 4 теми. З’єднання з Telegram не виконувалося.")
            return 0
        if args.demo:
            print(knowledge.data["welcome"])
            print("\nКоманди: /service, /returns, /privacy, /age. Вихід: /exit")
            while True:
                try:
                    text = input("\nВи: ")
                except EOFError:
                    break
                if text.strip() == "/exit":
                    break
                print("\nБот: " + knowledge.answer(text)[0])
            return 0
        load_env(ROOT / ".env")
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise SetupError("Додайте токен нового бота у .env за прикладом .env.example. "
                             "Для локальної перевірки: python3 bot.py --demo")
        stop = threading.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stop.set())
        run(Telegram(token), knowledge, ROOT / "state", stop)
        return 0
    except SetupError as error:
        LOG.error("%s", error)
        return 1
    except (ValueError, OSError, KeyError):
        # Deliberately avoid tracebacks: a frame could contain token or user data.
        LOG.error("Не вдалося запустити бот. Перевірте .env, faq.json і доступ до папки. "
                  "Також переконайтеся, що бот не запущений двічі та не має активного webhook.")
        return 1
    except ApiError as error:
        LOG.error("%s Перевірте токен, мережу та чи не працює інша копія бота.", error)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
