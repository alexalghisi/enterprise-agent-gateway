import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { CallerSessions } from "./callerSessions.js";
import type { GatewayApi } from "./gatewayClient.js";
import { registerGatewayTools } from "./tools.js";

export function createServer(gateway: GatewayApi, conversationId: string): McpServer {
    const server = new McpServer({ name: "enterprise-agent-gateway", version: "0.1.0" });
    registerGatewayTools(server, { gateway, sessions: new CallerSessions(), conversationId });
    return server;
}
