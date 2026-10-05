import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

import type { CallerSessions } from "./callerSessions.js";
import { GatewayError, type GatewayApi } from "./gatewayClient.js";
import { idempotencyKey } from "./idempotency.js";

const policyNumber = z
    .string()
    .regex(/^[A-Z]{2}-\d{6}$/, "Policy numbers look like HH-100234")
    .describe("Policy number exactly as the caller read it, e.g. HH-100234");
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Use YYYY-MM-DD");
const claimType = z.enum(["water_damage", "theft", "fire", "glass", "liability"]);

const NOT_VERIFIED =
    "The caller is not verified for this policy yet. Ask for their date of birth and call verify_caller first.";

export interface ToolDependencies {
    gateway: GatewayApi;
    sessions: CallerSessions;
    conversationId: string;
}

function ok(data: unknown): CallToolResult {
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
}

function failure(message: string): CallToolResult {
    return { content: [{ type: "text", text: message }], isError: true };
}

async function guarded(action: () => Promise<CallToolResult>): Promise<CallToolResult> {
    try {
        return await action();
    } catch (error) {
        if (error instanceof GatewayError) {
            return failure(`${error.code}: ${error.message}`);
        }
        throw error;
    }
}

export function registerGatewayTools(server: McpServer, deps: ToolDependencies): void {
    const { gateway, sessions, conversationId } = deps;

    server.registerTool(
        "verify_caller",
        {
            title: "Verify caller",
            description:
                "Confirms the caller owns the policy using their date of birth. Must succeed before reading the policy or filing a claim.",
            inputSchema: { policy_number: policyNumber, date_of_birth: isoDate },
        },
        ({ policy_number, date_of_birth }) =>
            guarded(async () => {
                const caller = await gateway.verifyCaller(policy_number, date_of_birth);
                sessions.remember(policy_number, caller.session_token);
                return ok({ verified: true, display_name: caller.display_name });
            }),
    );

    server.registerTool(
        "get_policy",
        {
            title: "Get policy",
            description: "Returns product, coverage period, covered claim types and deductible.",
            inputSchema: { policy_number: policyNumber },
            annotations: { readOnlyHint: true },
        },
        ({ policy_number }) =>
            guarded(async () => {
                const session = sessions.forPolicy(policy_number);
                return session ? ok(await gateway.getPolicy(policy_number, session)) : failure(NOT_VERIFIED);
            }),
    );

    server.registerTool(
        "file_claim",
        {
            title: "File claim",
            description:
                "Files a new claim. Repeating the call with identical arguments returns the original claim instead of a duplicate.",
            inputSchema: {
                policy_number: policyNumber,
                claim_type: claimType,
                incident_date: isoDate,
                description: z.string().min(10).max(2000).describe("What happened, in the caller's words"),
            },
            annotations: { idempotentHint: true },
        },
        (args) =>
            guarded(async () => {
                const session = sessions.forPolicy(args.policy_number);
                if (!session) {
                    return failure(NOT_VERIFIED);
                }
                const claim = await gateway.fileClaim(
                    args,
                    session,
                    idempotencyKey(conversationId, "file_claim", args),
                );
                sessions.rememberClaim(claim.claim_id, claim.policy_number);
                return ok(claim);
            }),
    );

    server.registerTool(
        "get_claim_status",
        {
            title: "Get claim status",
            description: "Returns the current status of a claim filed by the verified caller.",
            inputSchema: { claim_id: z.string().min(3) },
            annotations: { readOnlyHint: true },
        },
        ({ claim_id }) =>
            guarded(async () => {
                const session = sessions.forClaim(claim_id);
                return session ? ok(await gateway.getClaim(claim_id, session)) : failure(NOT_VERIFIED);
            }),
    );

    server.registerTool(
        "escalate_to_human",
        {
            title: "Escalate to a human agent",
            description:
                "Hands the conversation to a human with a short summary. Use when the caller asks for a person or the request is outside the available tools.",
            inputSchema: {
                policy_number: policyNumber.optional(),
                reason: z.string().min(3).max(200),
                summary: z.string().min(10).max(4000),
            },
            annotations: { idempotentHint: true },
        },
        ({ policy_number, reason, summary }) =>
            guarded(async () => {
                const escalation = { reason, summary, ...(policy_number ? { policy_number } : {}) };
                return ok(
                    await gateway.escalate(
                        escalation,
                        idempotencyKey(conversationId, "escalate_to_human", escalation),
                    ),
                );
            }),
    );
}
