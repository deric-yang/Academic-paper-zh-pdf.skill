#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

function parseArgs(argv) {
    const values = new Map();
    for (let index = 0; index < argv.length; index += 2) {
        const key = argv[index];
        const value = argv[index + 1];
        if (!key?.startsWith("--") || value === undefined) {
            throw new Error(`Invalid argument near: ${key ?? "<end>"}`);
        }
        values.set(key.slice(2), value);
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
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ].filter(Boolean);
    const match = candidates.find((candidate) => existsSync(candidate));
    if (!match) {
        throw new Error("Chromium/Google Chrome was not found. Set CHROME_PATH to its executable.");
    }
    return match;
}

const args = parseArgs(process.argv.slice(2));
const input = required(args, "input");
const output = required(args, "output");
const html = args.get("html") ? resolve(args.get("html")) : output.replace(/\.pdf$/i, ".html");
const css = args.get("css") ? resolve(args.get("css")) : resolve(dirname(import.meta.filename), "../assets/paper.css");
const title = args.get("title") ?? "学术论文中文译本";
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
    "--toc",
    "--toc-depth=2",
    "--number-sections",
    `--css=${css}`,
    `--metadata=title:${title}`,
    `--resource-path=${dirname(input)}`,
    `--output=${html}`,
];

if (bibliography) {
    pandocArgs.push("--citeproc", `--bibliography=${bibliography}`);
}

execFileSync("pandoc", pandocArgs, { cwd: dirname(input), stdio: "inherit" });

const chrome = findChrome();
execFileSync(
    chrome,
    [
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        `--print-to-pdf=${output}`,
        `file://${html}`,
    ],
    { stdio: "inherit" },
);

if (!existsSync(output)) {
    throw new Error(`PDF was not created: ${output}`);
}

console.log(JSON.stringify({ html, input, output }, null, 2));
