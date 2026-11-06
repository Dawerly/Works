#!/bin/zsh
cd -- "${0:A:h}" || exit 1
python3 bot.py
result=$?
if (( result != 0 )); then
  read '?Натисніть Enter, щоб закрити вікно…'
fi
exit "$result"
