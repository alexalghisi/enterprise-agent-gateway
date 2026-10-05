export type ClaimType = "water_damage" | "theft" | "fire" | "glass" | "liability";

export interface VerifiedCaller {
    session_token: string;
    display_name: string;
}

export interface PolicySummary {
    policy_number: string;
    product: string;
    holder: string;
    covered_claim_types: ClaimType[];
    valid_from: string;
    valid_until: string;
    deductible_eur: number;
}

export interface Claim {
    claim_id: string;
    policy_number: string;
    claim_type: ClaimType;
    incident_date: string;
    status: "received" | "in_review" | "approved" | "rejected";
}

export interface NewClaim {
    policy_number: string;
    claim_type: ClaimType;
    incident_date: string;
    description: string;
}

export interface NewEscalation {
    policy_number?: string;
    reason: string;
    summary: string;
}

export interface GatewayApi {
    verifyCaller(policyNumber: string, dateOfBirth: string): Promise<VerifiedCaller>;
    getPolicy(policyNumber: string, session: string): Promise<PolicySummary>;
    fileClaim(claim: NewClaim, session: string, idempotencyKey: string): Promise<Claim>;
    getClaim(claimId: string, session: string): Promise<Claim>;
    escalate(escalation: NewEscalation, idempotencyKey: string): Promise<{ escalation_id: string }>;
}

export class GatewayError extends Error {
    constructor(
        readonly status: number,
        readonly code: string,
        message: string,
    ) {
        super(message);
        this.name = "GatewayError";
    }
}

type Fetch = typeof fetch;

interface RequestOptions {
    method?: "GET" | "POST";
    body?: unknown;
    headers?: Record<string, string>;
}

export class HttpGatewayClient implements GatewayApi {
    constructor(
        private readonly baseUrl: string,
        private readonly apiKey: string,
        private readonly fetchImpl: Fetch = fetch,
        private readonly timeoutMs = 8_000,
    ) {}

    verifyCaller(policyNumber: string, dateOfBirth: string): Promise<VerifiedCaller> {
        return this.request("/v1/tools/verify-caller", {
            method: "POST",
            body: { policy_number: policyNumber, date_of_birth: dateOfBirth },
        });
    }

    getPolicy(policyNumber: string, session: string): Promise<PolicySummary> {
        return this.request(`/v1/tools/policies/${encodeURIComponent(policyNumber)}`, {
            headers: { "X-Caller-Session": session },
        });
    }

    fileClaim(claim: NewClaim, session: string, idempotencyKey: string): Promise<Claim> {
        return this.request("/v1/tools/claims", {
            method: "POST",
            body: claim,
            headers: { "X-Caller-Session": session, "Idempotency-Key": idempotencyKey },
        });
    }

    getClaim(claimId: string, session: string): Promise<Claim> {
        return this.request(`/v1/tools/claims/${encodeURIComponent(claimId)}`, {
            headers: { "X-Caller-Session": session },
        });
    }

    escalate(escalation: NewEscalation, idempotencyKey: string): Promise<{ escalation_id: string }> {
        return this.request("/v1/tools/escalations", {
            method: "POST",
            body: escalation,
            headers: { "Idempotency-Key": idempotencyKey },
        });
    }

    private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
        const headers: Record<string, string> = { "X-Api-Key": this.apiKey, ...options.headers };
        const init: RequestInit = {
            method: options.method ?? "GET",
            headers,
            signal: AbortSignal.timeout(this.timeoutMs),
        };
        if (options.body !== undefined) {
            headers["Content-Type"] = "application/json";
            init.body = JSON.stringify(options.body);
        }
        const response = await this.fetchImpl(new URL(path, this.baseUrl), init);
        const payload: unknown = await response.json().catch(() => undefined);
        if (!response.ok) {
            throw toGatewayError(response.status, payload);
        }
        return payload as T;
    }
}

function toGatewayError(status: number, payload: unknown): GatewayError {
    const error = (payload as { error?: { code?: string; message?: string } } | undefined)?.error;
    if (error?.code && error.message) {
        return new GatewayError(status, error.code, error.message);
    }
    return new GatewayError(status, "unexpected_response", `Gateway responded with HTTP ${status}`);
}
