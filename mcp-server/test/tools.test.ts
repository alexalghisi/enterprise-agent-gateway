import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { createServer } from "../src/server.js";
import { FakeGateway } from "./fakeGateway.js";

const CLAIM = {
    policy_number: "HH-100234",
    claim_type: "water_damage",
    incident_date: "2026-01-20",
    description: "Ceiling leak from the flat upstairs",
};

describe("gateway MCP tools", () => {
    let gateway: FakeGateway;
    let client: Client;

    beforeEach(async () => {
        gateway = new FakeGateway();
        const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
        await createServer(gateway, "conv-1").connect(serverTransport);
        client = new Client({ name: "test-agent", version: "1.0.0" });
        await client.connect(clientTransport);
    });

    afterEach(async () => {
        await client.close();
    });

    async function call(name: string, args: Record<string, unknown>): Promise<CallToolResult> {
        return (await client.callTool({ name, arguments: args })) as CallToolResult;
    }

    function text(result: CallToolResult): string {
        const [first] = result.content;
        return first?.type === "text" ? first.text : "";
    }

    const verify = () => call("verify_caller", { policy_number: "HH-100234", date_of_birth: "1987-04-12" });

    it("advertises every tool with an input schema", async () => {
        const { tools } = await client.listTools();
        expect(tools.map((tool) => tool.name).sort()).toEqual([
            "escalate_to_human",
            "file_claim",
            "get_claim_status",
            "get_policy",
            "verify_caller",
        ]);
        expect(tools.every((tool) => tool.inputSchema.type === "object")).toBe(true);
    });

    it("never exposes the caller session token to the model", async () => {
        const result = await verify();
        expect(JSON.parse(text(result))).toEqual({ verified: true, display_name: "M**** S********" });
        expect(text(result)).not.toContain("session-");
    });

    it("asks the agent to verify before reading the policy", async () => {
        const result = await call("get_policy", { policy_number: "HH-100234" });
        expect(result.isError).toBe(true);
        expect(text(result)).toContain("call verify_caller first");
    });

    it("reads the policy with the stored session after verification", async () => {
        await verify();
        const result = await call("get_policy", { policy_number: "HH-100234" });
        expect(JSON.parse(text(result)).covered_claim_types).toContain("water_damage");
    });

    it("surfaces gateway errors as recoverable tool errors", async () => {
        const result = await call("verify_caller", { policy_number: "HH-100234", date_of_birth: "2000-01-01" });
        expect(result.isError).toBe(true);
        expect(text(result)).toBe("verification_failed: Policy number and date of birth do not match");
    });

    it("rejects malformed arguments before reaching the gateway", async () => {
        const result = await call("verify_caller", { policy_number: "100234", date_of_birth: "12.04.1987" });
        expect(result.isError).toBe(true);
    });

    it("derives the same idempotency key when the agent retries a claim", async () => {
        await verify();
        await call("file_claim", CLAIM);
        await call("file_claim", { ...CLAIM });
        await call("file_claim", { ...CLAIM, incident_date: "2026-01-21" });

        const [first, retry, different] = gateway.fileClaimKeys;
        expect(first).toBe(retry);
        expect(different).not.toBe(first);
        expect(first).toMatch(/^conv-1:file_claim:[0-9a-f]{32}$/);
    });

    it("looks up claim status with the session of the policy the claim belongs to", async () => {
        await verify();
        const claimId = JSON.parse(text(await call("file_claim", CLAIM))).claim_id;
        const status = await call("get_claim_status", { claim_id: claimId });
        expect(JSON.parse(text(status)).status).toBe("received");
    });

    it("escalates without requiring a verified caller", async () => {
        const result = await call("escalate_to_human", {
            reason: "caller wants a person",
            summary: "Caller could not remember their policy number",
        });
        expect(JSON.parse(text(result))).toEqual({ escalation_id: "esc_1" });
        expect(gateway.escalations[0]).not.toHaveProperty("policy_number");
    });
});
