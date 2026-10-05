export class CallerSessions {
    private readonly tokens = new Map<string, string>();
    private readonly claimPolicies = new Map<string, string>();

    remember(policyNumber: string, token: string): void {
        this.tokens.set(policyNumber, token);
    }

    rememberClaim(claimId: string, policyNumber: string): void {
        this.claimPolicies.set(claimId, policyNumber);
    }

    forPolicy(policyNumber: string): string | undefined {
        return this.tokens.get(policyNumber);
    }

    forClaim(claimId: string): string | undefined {
        const policyNumber = this.claimPolicies.get(claimId);
        return policyNumber === undefined ? this.onlySession() : this.tokens.get(policyNumber);
    }

    private onlySession(): string | undefined {
        return this.tokens.size === 1 ? this.tokens.values().next().value : undefined;
    }
}
