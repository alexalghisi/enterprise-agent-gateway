import { describe, expect, it, vi } from "vitest";

import { GatewayError, HttpGatewayClient } from "../src/gatewayClient.js";

function jsonResponse(status: number, body: unknown): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

describe("HttpGatewayClient", () => {
    it("sends the API key, caller session and idempotency key", async () => {
        const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
            jsonResponse(201, { claim_id: "clm_1", status: "received" }),
        );
        const client = new HttpGatewayClient("http://gateway:8080", "key-1", fetchMock);

        await client.fileClaim(
            {
                policy_number: "HH-100234",
                claim_type: "fire",
                incident_date: "2026-02-01",
                description: "Kitchen fire",
            },
            "session-1",
            "idem-1",
        );

        const [url, init] = fetchMock.mock.calls[0] ?? [];
        expect(String(url)).toBe("http://gateway:8080/v1/tools/claims");
        expect(init?.method).toBe("POST");
        expect(init?.headers).toMatchObject({
            "X-Api-Key": "key-1",
            "X-Caller-Session": "session-1",
            "Idempotency-Key": "idem-1",
            "Content-Type": "application/json",
        });
        expect(JSON.parse(String(init?.body))).toMatchObject({ claim_type: "fire" });
    });

    it("encodes path parameters", async () => {
        const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(200, {}));
        await new HttpGatewayClient("http://gateway", "key", fetchMock).getClaim("clm/../x", "s");
        expect(String(fetchMock.mock.calls[0]?.[0])).toBe("http://gateway/v1/tools/claims/clm%2F..%2Fx");
    });

    it("maps structured gateway errors", async () => {
        const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
            jsonResponse(422, { error: { code: "not_covered", message: "glass is not covered" } }),
        );
        const error = await new HttpGatewayClient("http://gateway", "key", fetchMock)
            .getPolicy("HH-100234", "s")
            .catch((caught: unknown) => caught);

        expect(error).toBeInstanceOf(GatewayError);
        expect(error).toMatchObject({ status: 422, code: "not_covered", message: "glass is not covered" });
    });

    it("maps unexpected responses without a body", async () => {
        const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response("bad gateway", { status: 502 }));
        await expect(
            new HttpGatewayClient("http://gateway", "key", fetchMock).getPolicy("HH-100234", "s"),
        ).rejects.toMatchObject({ code: "unexpected_response", status: 502 });
    });
});
