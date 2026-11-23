# Версии промптов для эксперимента №4

| Режим | Версия | Файл инструкции | Результат повторного прогона |
| --- | --- | --- | --- |
| A · quote | azpu-extract-v2 | [quote-2.txt](quote-2.txt) | [CSV A](../../docs/experiments/lab4-quote.csv) |
| B · segment | azpu-segments-1 | [segments-1.txt](segments-1.txt) | [CSV B](../../docs/experiments/lab4-segment.csv) |
| C · short | azpu-segments-short-1 | [segments-1.txt](segments-1.txt) | [CSV C](../../docs/experiments/lab4-short.csv) |

В A модель генерирует цитату и ID. В B она выбирает ID, а код берёт цитату из исходного фрагмента. В C дополнительно уменьшается набор входных фрагментов. B и C используют один текст инструкции, но разные режимы подготовки входа.

Каждая строка CSV содержит версию промпта. [Сводка прогонов](../../docs/experiments/lab4-summary.json) связывает файл инструкции и выходной CSV по SHA-256. При изменении инструкции создайте новую версию, повторите эксперимент и обновите сводку. Команды и правило выбора описаны в [протоколе](../../docs/experiments/lab4.md).
