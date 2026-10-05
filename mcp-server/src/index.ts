#!/usr/bin/env node
import { randomUUID } from "node:crypto";

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { HttpGatewayClient } from "./gatewayClient.js";
import { createServer } from "./server.js";

function requiredEnv(name: string): string {
    const value = process.env[name];
    if (!value) {
        throw new Error(`Missing required environment variable ${name}`);
    }
    return value;
}

const gateway = new HttpGatewayClient(requiredEnv("GATEWAY_URL"), requiredEnv("GATEWAY_API_KEY"));
const server = createServer(gateway, process.env.CONVERSATION_ID ?? randomUUID());

await server.connect(new StdioServerTransport());
