#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const BOOLEAN_FLAGS = new Set(["help", "number-sections"]);

const USAGE = `Usage: node scripts/build_pdf.mjs --input <paper.zh-CN.md> --output <paper.zh-CN.pdf> [options]

Options:
  --html <file>           HTML output path (default: the --output path with .html)
  --css <file>            Print stylesheet (default: assets/paper.css)
  --title <text>          Document title (default: 学术论文中文译本)
  --bibliography <file>   BibTeX file for pandoc citeproc
  --number-sections       Let Pandoc number headings (off by default to preserve source numbering)
  --lang <code>           Document language metadata (default: zh-Hans)
  --help                  Show this help message`;

function parseArgs(argv) {
    const values = new Map();
    for (let index = 0; index < argv.length; index += 1) {
        const argument = argv[index];
        if (!argument.startsWith("--") || argument === "--") {
            throw new Error(`Invalid argument: ${argument}`);
        }
        const separator = argument.indexOf("=");
        let key;
        let value;
        if (separator !== -1) {
            key = argument.slice(2, separator);
            value = argument.slice(separator + 1);
        } else {
            key = argument.slice(2);
            if (BOOLEAN_FLAGS.has(key)) {
                value = "true";
            } else {
                value = argv[index + 1];
                if (value === undefined || value.startsWith("--")) {
                    throw new Error(`Missing value for --${key}`);
                }
                index += 1;
            }
        }
        if (!key) {
            throw new Error(`Invalid argument: ${argument}`);
        }
        if (values.has(key)) {
            throw new Error(`Duplicate argument: --${key}`);
        }
        values.set(key, value);
    }
    return values;
}

function required(args, name) {
    const value = args.get(name);
    if (!value) {
        throw new Error(`Missing required argument: --${name}`);
    }
    return resolve(value);
}

function findChrome() {
    const candidates = [
        process.env.CHROME_PATH,
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ].filter(Boolean);
    const match = candidates.find((candidate) => existsSync(candidate));
    if (!match) {
        throw new Error("Chromium/Google Chrome was not found. Set CHROME_PATH to its executable.");
    }
    return match;
}

function decodeHtmlAttribute(value) {
    return value
        .replaceAll("&amp;", "&")
        .replaceAll("&quot;", "\"")
        .replaceAll("&#39;", "'")
        .replaceAll("&lt;", "<")
        .replaceAll("&gt;", ">");
}

function assertImagesEmbedded(htmlPath) {
    const html = readFileSync(htmlPath, "utf8");
    const missing = [];
    for (const match of html.matchAll(/<img\b[^>]*\bsrc="([^"]*)"/g)) {
        const source = decodeHtmlAttribute(match[1]);
        if (/^(?:data:|https?:|file:|blob:)/i.test(source)) {
            continue;
        }
        if (!existsSync(resolve(dirname(htmlPath), source))) {
            missing.push(source);
        }
    }
    if (missing.length > 0) {
        throw new Error(
            `Image resources were not embedded and do not exist relative to the HTML: ${missing.join(", ")}`,
        );
    }
}

const args = parseArgs(process.argv.slice(2));

if (args.has("help")) {
    console.log(USAGE);
    process.exit(0);
}

const input = required(args, "input");
const output = required(args, "output");
if (!/\.pdf$/i.test(output)) {
    throw new Error("--output must end with .pdf so the HTML fallback path is unambiguous");
}
if (/\.(?:tex|latex)$/i.test(input)) {
    throw new Error(
        "LaTeX input is not supported directly; convert it to Markdown first, for example: " +
            "pandoc -f latex -t markdown paper.tex -o paper.zh-CN.md",
    );
}
const html = args.get("html") ? resolve(args.get("html")) : output.replace(/\.pdf$/i, ".html");
if (html === output) {
    throw new Error("--html must differ from --output");
}
const css = args.get("css")
    ? resolve(args.get("css"))
    : resolve(dirname(fileURLToPath(import.meta.url)), "../assets/paper.css");
const title = args.get("title") ?? "学术论文中文译本";
const lang = args.get("lang") ?? "zh-Hans";
const bibliography = args.get("bibliography") ? resolve(args.get("bibliography")) : null;

for (const file of [input, css, bibliography].filter(Boolean)) {
    if (!existsSync(file)) {
        throw new Error(`Input does not exist: ${file}`);
    }
}

mkdirSync(dirname(output), { recursive: true });
mkdirSync(dirname(html), { recursive: true });

const pandocArgs = [
    input,
    "--standalone",
    "--from=markdown+raw_html+tex_math_dollars",
    "--to=html5",
    "--mathml",
    "--embed-resources",
    "--toc",
    "--toc-depth=2",
    `--css=${css}`,
    `--metadata=title:${title}`,
    `--metadata=lang:${lang}`,
    `--resource-path=${dirname(input)}`,
    `--output=${html}`,
];

if (args.has("number-sections")) {
    pandocArgs.push("--number-sections");
}
if (bibliography) {
    pandocArgs.push("--citeproc", `--bibliography=${bibliography}`);
}

execFileSync("pandoc", pandocArgs, { cwd: dirname(input), stdio: "inherit" });
assertImagesEmbedded(html);

const chrome = findChrome();
execFileSync(
    chrome,
    [
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        `--print-to-pdf=${output}`,
        pathToFileURL(html).href,
    ],
    { stdio: "inherit" },
);

if (!existsSync(output)) {
    throw new Error(`PDF was not created: ${output}`);
}

console.log(
    JSON.stringify(
        {
            embeddedResources: true,
            html,
            input,
            lang,
            numberedSections: args.has("number-sections"),
            output,
            title,
        },
        null,
        2,
    ),
);
