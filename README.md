# Academic Paper → Chinese PDF Skill

一个面向 Codex 的可复用学术论文本地化工作流：将英文或其他外文学术论文翻译为经过术语校正、保留公式、引文、原图、图题与表格，并完成全页视觉验收的中文 Markdown、HTML 和 PDF。

它适合“完整翻译论文并交付图文 PDF”，不用于只需要摘要、问答或单段翻译的场景。

## 能力范围

- 优先锁定会议终稿、论文官网或 arXiv 源码，记录来源、版本和 SHA-256；
- 在 LaTeX/Markdown 源码、PDF 版面翻译和 OCR 重建之间选择合适路线；
- 用术语表和章节上下文分段调用大模型，保护公式、变量、citation key 和关键数字；
- 复用论文原图，生成可审阅 Markdown、HTML 与完整中文 PDF；
- 使用 Poppler 渲染全部页面，检查页数、乱码、近空白页，并生成 contact sheet；
- 显式记录非官方翻译声明，以及论文、图片、附件和数据集的许可边界。

## 安装

### 从 GitHub 安装

可以直接让 Codex 安装这个仓库：

```text
请从 https://github.com/deric-yang/Academic-paper-zh-pdf.skill 安装 academic-paper-zh-pdf skill。
```

也可以手动克隆到 Codex skills 目录：

```bash
git clone https://github.com/deric-yang/Academic-paper-zh-pdf.skill.git \
  ~/.codex/skills/academic-paper-zh-pdf
```

### 使用打包文件

[下载可安装的 `academic-paper-zh-pdf.skill`](./dist/academic-paper-zh-pdf.skill)，解压到 Codex skills 目录：

```bash
unzip academic-paper-zh-pdf.skill -d ~/.codex/skills/
```

该包只包含运行时需要的 `SKILL.md`、参考规范、构建脚本和打印样式。

当前包 SHA-256：

```text
723a9aff94d4a11f7e96649715a6312ce7cbb72ba6893c5ffb09b56dcf107865
```

## 依赖

- 可调用的大模型；
- Pandoc ≥ 2.19（构建脚本使用 `--embed-resources`）；
- Chromium 或 Google Chrome；
- Poppler：`pdfinfo`、`pdftotext`、`pdftoppm`；
- Python 3 与 Pillow；
- Node.js ≥ 18；
- CJK 字体（如 Noto Serif/Sans CJK SC），否则 PDF 会缺字。

当论文提供 LaTeX、Markdown 或 arXiv 源码时，应优先采用源文件重排；只有 PDF 时可使用 BabelDOC、PDFMathTranslate 或 OCR 结果作为初稿，但仍需执行术语校正和全页 QA。

## 典型输出

```text
paper-translation/
├── source/
│   ├── original.pdf
│   └── assets/
├── translation/
│   ├── paper.zh-CN.md
│   ├── glossary.zh-CN.md
│   └── source-manifest.json
├── output/
│   ├── paper.zh-CN.html
│   └── paper.zh-CN.pdf
└── qa/
    ├── pdf-audit.json
    └── contact-sheet.png
```

完整工作流、触发边界和交付要求见 [`SKILL.md`](./SKILL.md)，翻译质量规范见 [`references/translation-quality.md`](./references/translation-quality.md)。

## 构建与验收

```bash
node scripts/build_pdf.mjs \
  --input /absolute/path/paper.zh-CN.md \
  --output /absolute/path/paper.zh-CN.pdf \
  --html /absolute/path/paper.zh-CN.html \
  --css assets/paper.css \
  --title "论文中文译本"

python scripts/verify_pdf.py \
  --pdf /absolute/path/paper.zh-CN.pdf \
  --output-dir /absolute/path/qa
```

构建脚本会把 `assets/paper.css` 与原图嵌入 HTML，因此 HTML 可单文件交付；默认保留 Markdown 中的章节编号，原稿没有编号时才加 `--number-sections`。缺失图片会让构建直接失败，而不是生成破图 PDF。

`verify_pdf.py` 在页数不一致或文本出现替换字符时以非零状态退出；`--strict` 还会把近空白页视为阻断，`pdf-audit.json` 的 `blocking_issues`/`warnings` 可直接消费。PDF 只有在全部页面成功渲染、自动检查无阻断错误，并且 contact sheet 已完成人工查看后才算交付完成。

## 打包

```bash
python3 scripts/build_skill.py          # 重新生成 dist/academic-paper-zh-pdf.skill，并打印 SHA-256
python3 scripts/build_skill.py --check  # 校验已提交的包与源码一致
```

打包使用固定时间戳和不压缩存储（ZIP_STORED），同一份源码生成相同哈希；修改 `SKILL.md`、脚本或样式后必须重新打包并更新上面的 SHA-256。

## 仓库结构

```text
.
├── SKILL.md
├── assets/paper.css
├── references/translation-quality.md
├── scripts/
│   ├── build_pdf.mjs
│   ├── build_skill.py
│   └── verify_pdf.py
├── tests/test_verify_pdf.py
├── .github/workflows/ci.yml
└── dist/academic-paper-zh-pdf.skill
```

## 许可边界

本仓库中的工作流不会改变被翻译论文、插图、补充材料或数据集原有的版权与许可。发布译文前应单独核对权威原文和每类附件的授权条件，并显著标注“非官方中文翻译”。
