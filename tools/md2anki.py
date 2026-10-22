#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
md2anki.py — 把 Markdown 笔记按约定格式一键转成 Anki 卡片包（.apkg）

用法：
    pip install genanki
    python md2anki.py 笔记.md --deck "02-RAG与检索" --out cards.apkg
    然后双击生成的 .apkg 导入 Anki（建议先把牌组名在 Anki 里建好）

笔记格式约定（两种卡片）：
1) 问答卡——Q: 与 A: 成对出现（A 可多行，到下一个 Q: 或文件结束）：
       Q: RRF 公式是什么？k 一般取多少？
       A: score(d)=Σ 1/(k+rank_i(d))，k 一般取 60。

2) 填空卡——任何包含 {{c1::挖空}} 的独立段落自动变成 Cloze 卡：
       RRF 中 k 通常取 {{c1::60}}，它把 {{c2::多个榜单}} 融合。
"""
import argparse
import hashlib
import re
import sys

try:
    import genanki
except ImportError:
    sys.exit("缺少 genanki，请先执行: pip install genanki")

BASIC_MODEL = genanki.Model(
    1607392319, "基本",
    fields=[{"name": "Front"}, {"name": "Back"}],
    templates=[{
        "name": "Card 1",
        "qfmt": "{{Front}}",
        "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
    }],
)

CLOZE_MODEL = genanki.Model(
    1559328896, "填空题",
    fields=[{"name": "Text"}, {"name": "Extra"}],
    templates=[{
        "name": "Cloze",
        "qfmt": "{{cloze:Text}}",
        "afmt": "{{cloze:Text}}<br>{{Extra}}",
    }],
    model_type=genanki.Model.CLOZE,
)

QA_RE = re.compile(
    r"^Q[::：]\s*(.+?)\s*$"      # Q: 问题（行）
    r"[ \t]*\n"
    r"^A[::：]\s*(.+?)"           # A: 答案（可多行，非贪婪到下一个 Q: 或文末）
    r"(?=^Q[::：]|\Z)",
    re.S | re.M,
)


def stable_id(text: str) -> int:
    """由文本生成稳定的 10 位数字 ID，保证同一笔记重复生成时牌组一致。"""
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:10], 16)


def cloze_paragraphs(text: str):
    """按空行分段，返回所有含 {{cN::...}} 的段落。"""
    return [p.strip() for p in re.split(r"\n\s*\n", text)
            if re.search(r"\{\{c\d+::", p)]


def main():
    ap = argparse.ArgumentParser(description="Markdown → Anki (.apkg)")
    ap.add_argument("mdfile", help="笔记 .md 文件路径")
    ap.add_argument("--deck", default="00-待整理", help="目标牌组名")
    ap.add_argument("--out", default="cards.apkg", help="输出文件名")
    args = ap.parse_args()

    text = open(args.mdfile, encoding="utf-8").read()

    deck = genanki.Deck(stable_id(args.deck), args.deck)
    n_qa = n_cloze = 0

    for q, a in QA_RE.findall(text):
        deck.add_note(genanki.Note(model=BASIC_MODEL, fields=[q.strip(), a.strip()]))
        n_qa += 1

    for para in cloze_paragraphs(text):
        # Cloze 模型要求字段名恰好为 Text/Extra
        deck.add_note(genanki.Note(model=CLOZE_MODEL, fields=[para, ""]))
        n_cloze += 1

    if n_qa + n_cloze == 0:
        sys.exit("没有识别到任何卡片：请检查 Q:/A: 格式或 {{c1::}} 写法")

    genanki.Package(deck).write_to_file(args.out)
    print(f"完成：问答卡 {n_qa} 张 + 填空卡 {n_cloze} 张 → {args.out}")
    print("双击 .apkg 导入 Anki；重复导入会产生重复卡片，请一次导入后删除 apkg")


if __name__ == "__main__":
    main()