import {
    GatewayError,
    type Claim,
    type GatewayApi,
    type NewClaim,
    type NewEscalation,
    type PolicySummary,
    type VerifiedCaller,
} from "../src/gatewayClient.js";

export class FakeGateway implements GatewayApi {
    readonly fileClaimKeys: string[] = [];
    readonly escalations: NewEscalation[] = [];
    private readonly claims = new Map<string, Claim>();

    async verifyCaller(policyNumber: string, dateOfBirth: string): Promise<VerifiedCaller> {
        if (dateOfBirth !== "1987-04-12") {
            throw new GatewayError(401, "verification_failed", "Policy number and date of birth do not match");
        }
        return { session_token: `session-${policyNumber}`, display_name: "M**** S********" };
    }

    async getPolicy(policyNumber: string, session: string): Promise<PolicySummary> {
        this.assertSession(session, policyNumber);
        return {
            policy_number: policyNumber,
            product: "Home Contents Plus",
            holder: "M**** S********",
            covered_claim_types: ["fire", "theft", "water_damage"],
            valid_from: "2025-01-01",
            valid_until: "2027-12-31",
            deductible_eur: 150,
        };
    }

    async fileClaim(claim: NewClaim, session: string, idempotencyKey: string): Promise<Claim> {
        this.assertSession(session, claim.policy_number);
        this.fileClaimKeys.push(idempotencyKey);
        const filed: Claim = {
            claim_id: `clm_${this.claims.size + 1}`,
            policy_number: claim.policy_number,
            claim_type: claim.claim_type,
            incident_date: claim.incident_date,
            status: "received",
        };
        this.claims.set(filed.claim_id, filed);
        return filed;
    }

    async getClaim(claimId: string, session: string): Promise<Claim> {
        const claim = this.claims.get(claimId);
        if (!claim) {
            throw new GatewayError(404, "not_found", `Claim ${claimId} not found`);
        }
        this.assertSession(session, claim.policy_number);
        return claim;
    }

    async escalate(escalation: NewEscalation): Promise<{ escalation_id: string }> {
        this.escalations.push(escalation);
        return { escalation_id: `esc_${this.escalations.length}` };
    }

    private assertSession(session: string, policyNumber: string): void {
        if (session !== `session-${policyNumber}`) {
            throw new GatewayError(403, "forbidden", "Caller is not verified for this policy");
        }
    }
}
