import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

type Json = Record<string, unknown>;

interface Step {
    tool: string;
    args: Json;
    expect?: Json;
    expectError?: string;
    expectAbsent?: string;
}

interface Scenario {
    name: string;
    steps: Step[];
}

interface Outcome {
    passed: boolean;
    detail: string;
    elapsedMs: number;
}

const serverEntry = fileURLToPath(new URL("../dist/index.js", import.meta.url));
const scenariosFile = new URL("./scenarios.json", import.meta.url);

function resolve(value: unknown, results: Json[]): unknown {
    if (typeof value === "string") {
        const match = /^\$\{(\d+)\.(\w+)\}$/.exec(value);
        return match ? results[Number(match[1])]?.[match[2] as string] : value;
    }
    if (value && typeof value === "object") {
        return Object.fromEntries(Object.entries(value).map(([key, inner]) => [key, resolve(inner, results)]));
    }
    return value;
}

function check(step: Step, text: string, isError: boolean, results: Json[]): string | undefined {
    if (step.expectError !== undefined) {
        return isError && text.includes(step.expectError) ? undefined : `expected error "${step.expectError}", got ${text}`;
    }
    if (isError) {
        return `unexpected error: ${text}`;
    }
    if (step.expectAbsent !== undefined && text.includes(step.expectAbsent)) {
        return `response leaked "${step.expectAbsent}"`;
    }
    const data = JSON.parse(text) as Json;
    results.push(data);
    const expected = resolve(step.expect ?? {}, results.slice(0, -1)) as Json;
    for (const [key, value] of Object.entries(expected)) {
        if (value === "*" ? data[key] === undefined : data[key] !== value) {
            return `${step.tool}.${key}: expected ${JSON.stringify(value)}, got ${JSON.stringify(data[key])}`;
        }
    }
    return undefined;
}

async function runScenario(scenario: Scenario): Promise<Outcome> {
    const started = performance.now();
    const client = new Client({ name: "scenario-evals", version: "1.0.0" });
    await client.connect(
        new StdioClientTransport({
            command: process.execPath,
            args: [serverEntry],
            env: { ...process.env } as Record<string, string>,
            stderr: "inherit",
        }),
    );
    try {
        const results: Json[] = [];
        for (const step of scenario.steps) {
            const result = await client.callTool({ name: step.tool, arguments: resolve(step.args, results) as Json });
            const content = result.content as { type: string; text?: string }[];
            const text = content.find((part) => part.type === "text")?.text ?? "";
            const failure = check(step, text, result.isError === true, results);
            if (failure) {
                return { passed: false, detail: failure, elapsedMs: performance.now() - started };
            }
            if (step.expectError !== undefined) {
                results.push({});
            }
        }
        const calls = scenario.steps.length;
        return {
            passed: true,
            detail: `${calls} tool call${calls === 1 ? "" : "s"}`,
            elapsedMs: performance.now() - started,
        };
    } finally {
        await client.close();
    }
}

const scenarios = JSON.parse(await readFile(scenariosFile, "utf8")) as Scenario[];
let failed = 0;
console.log(`Running ${scenarios.length} scenarios against ${process.env.GATEWAY_URL}\n`);
for (const scenario of scenarios) {
    const outcome = await runScenario(scenario);
    failed += outcome.passed ? 0 : 1;
    const mark = outcome.passed ? "\u001b[32m✔\u001b[0m" : "\u001b[31m✘\u001b[0m";
    console.log(`${mark} ${scenario.name.padEnd(52)} ${outcome.elapsedMs.toFixed(0).padStart(5)} ms  ${outcome.detail}`);
}
console.log(`\n${scenarios.length - failed}/${scenarios.length} scenarios passed`);
process.exitCode = failed === 0 ? 0 : 1;
