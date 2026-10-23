import { Client } from "@langchain/langgraph-sdk";

export function createClient(apiUrl: string, accessToken: string) {
  return new Client({
    apiUrl,
    defaultHeaders: { Authorization: `Bearer ${accessToken}` },
  });
}
