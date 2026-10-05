import { createHash } from "node:crypto";

export function idempotencyKey(conversationId: string, tool: string, args: object): string {
    const canonical = JSON.stringify(args, Object.keys(args).sort());
    const digest = createHash("sha256").update(canonical).digest("hex").slice(0, 32);
    return `${conversationId}:${tool}:${digest}`;
}
